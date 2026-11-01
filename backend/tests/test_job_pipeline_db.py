"""Pipeline steps against a real, migrated Postgres (opt-in: CI has no database).

    TEST_DATABASE_URL=postgresql://... pytest tests/test_job_pipeline_db.py
"""
from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="needs TEST_DATABASE_URL")


class _DictRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.data[key] = value


@pytest.fixture
def session() -> Iterator[Any]:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    db = sessionmaker(bind=engine)()
    db.execute(text("DELETE FROM extracted_keywords"))
    db.execute(text("DELETE FROM job_matching_scores"))
    db.execute(text("DELETE FROM raw_job_postings WHERE DATE(scraped_at) = CURRENT_DATE"))
    db.execute(text("DELETE FROM job_market_metrics WHERE metric_date = CURRENT_DATE"))
    db.commit()
    yield db
    db.close()
    engine.dispose()


def _posting(db: Any, *, source: str = "remotive", title: str, company: str, location: str = "Stockholm",
             salary: tuple[int, int] | None = (50000, 60000), description: str | None = None,
             raw_data: dict[str, Any] | None = None) -> None:
    from app.models.job import RawJobPosting

    db.add(RawJobPosting(
        source=source, job_id_external=uuid.uuid4().hex, title=title, company=company, location=location,
        description=description or f"We are hiring a {title}. Python, Docker and AWS experience wanted. " * 2,
        url=f"https://example.com/{uuid.uuid4().hex}", raw_data=raw_data or {},
        salary_min=salary[0] if salary else None, salary_max=salary[1] if salary else None,
    ))


@pytest.mark.asyncio
async def test_pipeline_steps_end_to_end(session: Any) -> None:
    from sqlalchemy import text

    from app.core.dependencies import get_db, get_redis_client
    from app.main import app
    from app.services import job_pipeline as steps

    db = session
    for i in range(6):
        _posting(db, title=f"Senior Backend Engineer {i}", company=f"Company {i}")
    _posting(db, title="Senior Backend Engineer 0", company="Company 0")  # same ad again
    _posting(db, source="platsbanken", title="Systemutvecklare", company="Kommunen", salary=None,
             raw_data={"must_have_skills": ["Java"], "nice_to_have_skills": ["Scrum"]})
    _posting(db, title="Office plant", company="Plants AB", salary=None, description="x" * 60)
    db.commit()

    assert steps.mark_duplicates(db) == 1
    assert steps.tag_skills(db) == 8
    skills = dict(db.execute(text(
        "SELECT title, extracted_skills FROM raw_job_postings "
        "WHERE DATE(scraped_at) = CURRENT_DATE AND NOT is_duplicate"
    )).all())
    assert skills["Systemutvecklare"] == ["Java", "Scrum"]
    assert set(skills["Senior Backend Engineer 3"]) == {"python", "docker", "aws"}

    assert steps.extract_keywords(db) == 8  # every non-duplicate, counted once
    assert steps.extract_keywords(db) == 1  # only the one with nothing extractable comes back
    assert db.execute(text("SELECT count(DISTINCT raw_job_posting_id) FROM extracted_keywords")).scalar() == 7

    assert steps.compute_daily_metrics(db) == 8
    metrics = db.execute(text(
        "SELECT total_jobs_scraped, top_skills FROM job_market_metrics WHERE metric_date = CURRENT_DATE"
    )).one()
    assert metrics.total_jobs_scraped == 8
    assert {"skill": "python", "count": 6} in metrics.top_skills

    assert steps.refresh_salary_analytics(db) >= 8
    assert steps.refresh_salary_analytics(db) >= 8  # rerunnable: swaps cleanly over its own output

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis_client] = lambda: _DictRedis()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            by_location = (await client.get("/api/v1/analytics/salary-insights")).json()
            by_skill = (await client.get("/api/v1/analytics/salary-by-skill")).json()
            senior = (await client.get("/api/v1/analytics/salary-insights?experience_level=senior")).json()
    finally:
        app.dependency_overrides.clear()

    stockholm = next(r for r in by_location["data"] if r["dimension_value"] == "Stockholm")
    assert stockholm["job_count"] >= 6 and stockholm["p50_salary"] == 55000
    assert any(r["skill"] == "python" for r in by_skill["data"])
    assert senior["data"][0]["job_count"] >= 6


def test_active_user_ids_skips_users_without_a_default_cv(session: Any) -> None:
    from app.models.cv import CV
    from app.models.user import User
    from app.services import job_pipeline as steps

    db = session
    tag = uuid.uuid4().hex[:8]
    with_cv = User(email=f"with-cv-{tag}@example.com", hashed_password="x", is_active=True)
    no_cv = User(email=f"no-cv-{tag}@example.com", hashed_password="x", is_active=True)
    inactive = User(email=f"inactive-{tag}@example.com", hashed_password="x", is_active=False)
    db.add_all([with_cv, no_cv, inactive])
    db.flush()
    db.add(CV(user_id=with_cv.id, title="CV", filename="cv.txt", content="Python", is_default=True))
    db.add(CV(user_id=inactive.id, title="CV", filename="cv.txt", content="Python", is_default=True))
    db.add(CV(user_id=no_cv.id, title="Old", filename="old.txt", content="Java", is_default=False))
    db.commit()
    try:
        ids = set(steps.active_user_ids(db))
        assert str(with_cv.id) in ids
        assert str(no_cv.id) not in ids
        assert str(inactive.id) not in ids
    finally:
        for user in (with_cv, no_cv, inactive):
            db.delete(user)
        db.commit()

