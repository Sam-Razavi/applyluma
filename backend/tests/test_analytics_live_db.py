"""Analytics queries against a real Postgres: only live postings count.

The endpoint tests use fakes, which never run SQL. Opt-in, like the other
real-database tests:

    TEST_DATABASE_URL=postgresql://... pytest tests/test_analytics_live_db.py
"""
from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="needs TEST_DATABASE_URL")


class _NoCache:
    def get(self, key: str) -> None:
        return None

    def setex(self, key: str, ttl: int, value: str) -> None:
        pass


@pytest.fixture
def session() -> Iterator[Any]:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    import app.main  # noqa: F401  (registers every model, so relationships resolve)

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    db = sessionmaker(bind=engine)()
    db.execute(text("DELETE FROM raw_job_postings"))
    db.commit()
    yield db
    db.rollback()
    db.execute(text("DELETE FROM raw_job_postings"))
    db.commit()
    db.close()
    engine.dispose()


def _posting(db: Any, *, title: str, company: str, location: str, employment_type: str | None,
             skills: list[str] | None, remote: bool = False, **extra: Any) -> None:
    from app.models.job import RawJobPosting

    db.add(RawJobPosting(
        source="platsbanken", job_id_external=uuid.uuid4().hex, title=title, company=company,
        location=location, description="A job.", url=f"https://example.com/{uuid.uuid4().hex}",
        raw_data={}, employment_type=employment_type, extracted_skills=skills,
        remote_allowed=remote, **extra,
    ))


def _seed(db: Any) -> None:
    now = datetime.now(UTC)
    # Three live postings...
    _posting(db, title="Backend Developer", company="Acme", location="Stockholm",
             employment_type="Heltid", skills=["python", "docker"])
    _posting(db, title="Senior Engineer", company="Acme", location="Stockholm",
             employment_type="full_time", skills=["python"])
    _posting(db, title="Junior Analyst", company="Beta", location="Göteborg",
             employment_type="Deltid", skills=[], remote=True)
    # ...and three that are not the market now: archived (slimmed, so no
    # skills), past its deadline, and a cross-source duplicate.
    _posting(db, title="Backend Developer", company="Acme", location="Stockholm",
             employment_type="Heltid", skills=None, archived_at=now)
    _posting(db, title="Data Engineer", company="Gamma", location="Malmö",
             employment_type="Heltid", skills=["sql"], application_deadline=now - timedelta(days=1))
    _posting(db, title="Backend Developer", company="Acme", location="Stockholm",
             employment_type="Heltid", skills=["python"], is_duplicate=True)
    db.commit()


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data
    return [row if isinstance(row, dict) else row.model_dump() for row in data]


def test_point_in_time_analytics_count_only_live_postings(session: Any) -> None:
    from app.api.v1.endpoints.analytics.company_insights import get_company_insights
    from app.api.v1.endpoints.analytics.experience_levels import get_experience_levels
    from app.api.v1.endpoints.analytics.industry_breakdown import get_industry_breakdown
    from app.api.v1.endpoints.analytics.job_market_health import get_job_market_health
    from app.api.v1.endpoints.analytics.legacy import get_freshness
    from app.api.v1.endpoints.analytics.location_trends import get_location_trends

    _seed(session)
    cache = _NoCache()

    health = get_job_market_health(db=session, redis_client=cache).data
    health = health if isinstance(health, dict) else health.model_dump()
    assert health["total_jobs"] == 3
    assert health["unique_companies"] == 2
    # 3 skills over 3 live postings; the archived row's missing skills no longer count as 0.
    assert health["avg_skills_per_job"] == 1.0

    locations = {r["location"]: r["job_count"] for r in _rows(get_location_trends(db=session, redis_client=cache))}
    assert locations == {"Stockholm": 2, "Göteborg": 1}

    companies = {
        r["company_name"]: r["total_jobs"]
        for r in _rows(get_company_insights(limit=20, location=None, db=session, redis_client=cache))
    }
    assert companies == {"Acme": 2, "Beta": 1}

    assert sum(r["job_count"] for r in _rows(get_experience_levels(db=session, redis_client=cache))) == 3
    assert sum(r["job_count"] for r in _rows(get_industry_breakdown(db=session, redis_client=cache))) == 3

    freshness = get_freshness(_="user", db=session)
    assert freshness.total_jobs == 3

    # The same place in another case or with stray spaces is one location.
    _posting(session, title="Tester", company="Acme", location=" STOCKHOLM ",
             employment_type="Heltid", skills=[])
    session.commit()
    locations = {r["location"]: r["job_count"] for r in _rows(get_location_trends(db=session, redis_client=cache))}
    assert locations == {"Stockholm": 3, "Göteborg": 1}


def test_job_type_mix_merges_spellings_across_sources(session: Any) -> None:
    from app.api.v1.endpoints.analytics.job_type_mix import get_job_type_mix

    _seed(session)
    _posting(session, title="Designer", company="Delta", location="Remote",
             employment_type=None, skills=[], remote=True)
    _posting(session, title="Consultant", company="Delta", location="Remote",
             employment_type="freelance", skills=[], remote=True)
    session.commit()

    mix = {
        (r["job_type"], r["remote_label"]): r["job_count"]
        for r in _rows(get_job_type_mix(db=session, redis_client=_NoCache()))
    }
    # "Heltid" (Platsbanken) and "full_time" (Remotive) are one slice.
    assert mix == {
        ("full_time", "on-site"): 2,
        ("part_time", "remote"): 1,
        ("unknown", "remote"): 1,
        ("contract", "remote"): 1,
    }


def test_skill_demand_can_rank_by_volume(session: Any) -> None:
    """By growth, a skill seen once this week and never before tops the list;
    by mentions, the skills most ads ask for do."""
    from app.api.v1.endpoints.analytics.skill_demand import get_skill_demand

    now = datetime.now(UTC)
    for _ in range(3):
        _posting(session, title="Developer", company="Acme", location="Stockholm",
                 employment_type="Heltid", skills=["python"], scraped_at=now - timedelta(days=10))
    for _ in range(2):
        _posting(session, title="Developer", company="Acme", location="Stockholm",
                 employment_type="Heltid", skills=["python"])
    _posting(session, title="Developer", company="Acme", location="Stockholm",
             employment_type="Heltid", skills=["cobol"])
    session.commit()

    def skills(sort: str) -> list[str]:
        response = get_skill_demand(
            limit=10, min_growth_pct=-100.0, sort=sort, db=session, redis_client=_NoCache()
        )
        return [r["skill"] for r in _rows(response)]

    assert skills("growth") == ["cobol", "python"]
    assert skills("mentions") == ["python", "cobol"]


def test_industry_breakdown_classifies_swedish_titles(session: Any) -> None:
    """Most Platsbanken titles are Swedish; they used to land in "Other"."""
    from app.api.v1.endpoints.analytics.industry_breakdown import get_industry_breakdown

    for title in (
        "Systemutvecklare .NET",
        "Fullstackutvecklare",
        "Backend Developer",
        "Nätverkstekniker",
        "Supporttekniker till servicedesk",
        "Teknisk projektledare",
        "IT-chef",
        "Kock",
    ):
        _posting(session, title=title, company="Acme", location="Stockholm",
                 employment_type="Heltid", skills=[])
    session.commit()

    industries = {
        r["industry"]: r["job_count"]
        for r in _rows(get_industry_breakdown(db=session, redis_client=_NoCache()))
    }
    assert industries == {
        "Software Engineering": 3,
        "DevOps & Infrastructure": 1,
        "IT Support & Operations": 1,
        "Management & Leadership": 2,
        "Other": 1,
    }
