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


def test_repair_garbled_text_fixes_stored_remoteok_postings_only(session: Any) -> None:
    from sqlalchemy import text

    from app.services import job_pipeline as steps

    damaged = "Engineer — Platform".encode().decode("latin-1")
    tag = uuid.uuid4().hex[:8]
    _posting(session, source="remoteok", title=f"{damaged} {tag}", company="Sotheby’s".encode().decode("latin-1"))
    _posting(session, source="remoteok", title=f"Clean title {tag}", company="Acme")
    _posting(session, source="platsbanken", title=f"{damaged} sv {tag}", company="Åre kommun")
    session.commit()

    assert steps.repair_garbled_text(session) >= 1
    rows = dict(
        session.execute(
            text("SELECT title, company FROM raw_job_postings WHERE title LIKE :tag"), {"tag": f"%{tag}"}
        ).all()
    )
    assert rows[f"Engineer — Platform {tag}"] == "Sotheby’s"
    assert rows[f"Clean title {tag}"] == "Acme"
    assert f"{damaged} sv {tag}" in rows  # other sources are left alone
    assert steps.repair_garbled_text(session) == 0  # nothing left to repair





def test_a_job_saved_from_the_extension_stays_out_of_what_other_users_see(session: Any) -> None:
    """One user's saved page must not show in Discover, the source filter, or
    hide a scraped ad from everyone by winning the duplicate check."""
    from sqlalchemy import text

    from app.crud import job as crud_job
    from app.models.job import RawJobPosting
    from app.schemas.job import ExternalJobBookmarkRequest
    from app.services import job_pipeline as steps

    tag = uuid.uuid4().hex[:8]
    saved = crud_job.create_raw_job_from_external(
        session,
        ExternalJobBookmarkRequest(
            title=f"Backend Developer {tag}", company="Acme", location="Stockholm",
            url=f"https://careers.acme.test/jobs/{tag}", description="Python", source=f"ext-{tag}",
        ),
    )
    assert saved.user_submitted is True
    # Saved first, so it is the older of the two identical ads.
    session.execute(
        text("UPDATE raw_job_postings SET scraped_at = now() - interval '1 hour' WHERE id = :id"),
        {"id": saved.id},
    )
    _posting(session, source="remotive", title=f"Backend Developer {tag}", company="Acme")
    session.commit()

    steps.mark_duplicates(session)
    scraped = session.query(RawJobPosting).filter(
        RawJobPosting.title == f"Backend Developer {tag}", RawJobPosting.user_submitted.is_(False)
    ).one()
    assert scraped.is_duplicate is False

    listed = crud_job.list_jobs(session, uuid.uuid4(), search=tag, limit=50)
    assert [str(job["job_id"]) for job in listed] == [str(scraped.id)]
    assert f"ext-{tag}" not in {row["source"] for row in crud_job.list_sources(session)}
    # The saver still opens it by id.
    assert session.get(RawJobPosting, saved.id) is not None


def test_migration_rule_recognises_extension_rows_by_their_external_id(session: Any) -> None:
    from sqlalchemy import text

    tag = uuid.uuid4().hex[:8]
    url = f"https://www.linkedin.com/jobs/view/{tag}/"
    session.execute(
        text(
            "INSERT INTO raw_job_postings (source, job_id_external, title, company, description, url, raw_data) "
            "VALUES ('linkedin', :url, :title, 'Acme', 'd', :url, '{}')"
        ),
        {"url": url, "title": f"Old save {tag}"},
    )
    _posting(session, title=f"Scraped {tag}", company="Acme")
    session.commit()

    session.execute(
        text(
            "UPDATE raw_job_postings SET user_submitted = true "
            "WHERE job_id_external = left(url, 255) AND job_id_external LIKE 'http%'"
        )
    )
    session.commit()
    flags = dict(
        session.execute(
            text("SELECT title, user_submitted FROM raw_job_postings WHERE title LIKE :tag"), {"tag": f"%{tag}"}
        ).all()
    )
    assert flags == {f"Old save {tag}": True, f"Scraped {tag}": False}


def test_remote_jobs_are_flagged_for_the_discover_filter(session: Any) -> None:
    from sqlalchemy import text

    from app.services import job_pipeline as steps

    tag = uuid.uuid4().hex[:8]
    _posting(session, title=f"Remote by flag {tag}", company="A", location="Worldwide")
    _posting(session, title=f"Remote by place {tag}", company="B", location="Remote, EU")
    _posting(session, title=f"Distans {tag}", company="C", location="Distans")
    _posting(session, title=f"On site {tag}", company="D", location="Stockholm")
    session.flush()
    session.execute(
        text("UPDATE raw_job_postings SET remote_allowed = true WHERE title = :t"), {"t": f"Remote by flag {tag}"}
    )
    session.commit()

    assert steps.flag_remote_jobs(session) >= 3
    flags = dict(
        session.execute(
            text("SELECT title, is_remote FROM raw_job_postings WHERE title LIKE :tag"), {"tag": f"%{tag}"}
        ).all()
    )
    assert flags == {
        f"Remote by flag {tag}": True, f"Remote by place {tag}": True, f"Distans {tag}": True,
        f"On site {tag}": False,
    }
    assert steps.flag_remote_jobs(session) == 0


def test_platsbanken_deadlines_are_filled_for_ads_already_stored(session: Any) -> None:
    """The insert skips an ad that is already stored, so its deadline has to be
    written separately; every ad stored before the fix has none."""
    import psycopg2
    import psycopg2.extras
    from sqlalchemy import text

    from app.services.job_scrapers.platsbanken import UPDATE_DEADLINES_SQL

    tag = uuid.uuid4().hex[:8]
    for number in ("1", "2"):
        session.execute(
            text(
                "INSERT INTO raw_job_postings (source, job_id_external, title, company, description, url, raw_data) "
                "VALUES ('platsbanken', :ext, :title, 'Kommun', 'd', :url, '{}')"
            ),
            {"ext": f"{tag}{number}", "title": f"Ad {number} {tag}", "url": f"https://af.test/{tag}{number}"},
        )
    session.commit()

    conn = psycopg2.connect(os.environ["TEST_DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur, UPDATE_DEADLINES_SQL, [(f"{tag}1", "2026-12-01T23:59:59")], page_size=1
            )
            assert cur.rowcount == 1
            psycopg2.extras.execute_values(
                cur, UPDATE_DEADLINES_SQL, [(f"{tag}1", "2026-12-01T23:59:59")], page_size=1
            )
            assert cur.rowcount == 0  # unchanged deadlines are not rewritten
    finally:
        conn.close()

    deadlines = dict(
        session.execute(
            text("SELECT title, application_deadline FROM raw_job_postings WHERE title LIKE :tag"),
            {"tag": f"%{tag}"},
        ).all()
    )
    assert deadlines[f"Ad 1 {tag}"] is not None and deadlines[f"Ad 1 {tag}"].year == 2026
    assert deadlines[f"Ad 2 {tag}"] is None


def test_listing_check_archives_removed_ads_and_fills_deadlines(session: Any) -> None:
    import requests
    from sqlalchemy import text

    from app.services import job_pipeline as steps

    session.execute(
        text("UPDATE raw_job_postings SET archived_at = now() WHERE source = 'platsbanken' AND archived_at IS NULL")
    )
    tag = str(uuid.uuid4().int)[:9]
    answers = {"1": (False, None), "2": (True, "2026-12-24T23:59:59"), "3": (True, None)}
    for number in (*answers, "4"):
        session.execute(
            text(
                "INSERT INTO raw_job_postings (source, job_id_external, title, company, description, url, raw_data) "
                "VALUES ('platsbanken', :ext, :title, 'Kommun', 'd', :url, '{}')"
            ),
            {"ext": f"{tag}{number}", "title": f"Ad {number} {tag}", "url": f"https://af.test/{tag}{number}"},
        )
    session.commit()

    class _Client:
        asked: list[str] = []

        def ad_status(self, job_id: str) -> tuple[bool, str | None]:
            self.asked.append(job_id[-1])
            if job_id.endswith("4"):
                raise requests.ConnectionError("down")
            return answers[job_id[-1]]

    steps.LISTING_CHECK_PAUSE_SECONDS = 0
    assert steps.recheck_platsbanken_listings(session, client=_Client()) == 2  # type: ignore[arg-type]

    rows = {
        title: (archived, deadline)
        for title, archived, deadline in session.execute(
            text(
                "SELECT title, archived_at IS NOT NULL, application_deadline FROM raw_job_postings "
                "WHERE title LIKE :tag"
            ),
            {"tag": f"%{tag}"},
        ).all()
    }
    assert rows[f"Ad 1 {tag}"] == (True, None)  # taken down: archived
    assert rows[f"Ad 2 {tag}"][0] is False and rows[f"Ad 2 {tag}"][1] is not None
    assert rows[f"Ad 3 {tag}"] == (False, None)  # listed, no deadline given: untouched
    assert rows[f"Ad 4 {tag}"] == (False, None)  # the request failed: never treated as removed


def test_career_page_jobs_are_archived_when_their_board_drops_them(session: Any) -> None:
    """A stored job missing from a board that answered has been closed; a job
    on a board that did not answer must be left alone."""
    from sqlalchemy import text

    from app.services.job_scrapers.career_pages import SOURCE, CareerPagesClient

    tag = uuid.uuid4().hex[:8]

    def job(board: str, job_id: str) -> dict[str, Any]:
        return {
            "job_id_external": f"lever:{board}:{job_id}", "title": f"{job_id} {tag}", "company": "Acme",
            "location": "Stockholm", "description": "d", "url": f"https://jobs.lever.co/{board}/{job_id}",
            "remote_allowed": False, "raw_data": {},
        }

    first = CareerPagesClient(os.environ["TEST_DATABASE_URL"], boards=[])
    first.fetched_boards = [("lever", f"up{tag}"), ("lever", f"down{tag}")]
    assert first.save_to_db([job(f"up{tag}", "stays"), job(f"up{tag}", "closed"), job(f"down{tag}", "other")]) == 3

    second = CareerPagesClient(os.environ["TEST_DATABASE_URL"], boards=[])
    second.fetched_boards = [("lever", f"up{tag}")]  # the other board did not answer tonight
    assert second.save_to_db([job(f"up{tag}", "stays")]) == 0

    archived = dict(
        session.execute(
            text(
                "SELECT title, archived_at IS NOT NULL FROM raw_job_postings "
                "WHERE source = :source AND title LIKE :tag"
            ),
            {"source": SOURCE, "tag": f"%{tag}"},
        ).all()
    )
    assert archived == {f"stays {tag}": False, f"closed {tag}": True, f"other {tag}": False}


def test_career_page_jobs_are_not_archived_for_age(session: Any) -> None:
    from datetime import UTC, datetime

    from sqlalchemy import text

    from app.tasks import job_retention

    tag = uuid.uuid4().hex[:8]
    _posting(session, source="career_pages", title=f"Evergreen {tag}", company="Acme")
    _posting(session, source="remotive", title=f"Old {tag}", company="Acme")
    session.flush()
    session.execute(
        text("UPDATE raw_job_postings SET scraped_at = now() - interval '45 days' WHERE title LIKE :tag"),
        {"tag": f"%{tag}"},
    )
    session.commit()

    job_retention._archive(session, datetime.now(UTC), age_rule=True)

    archived = dict(
        session.execute(
            text("SELECT title, archived_at IS NOT NULL FROM raw_job_postings WHERE title LIKE :tag"),
            {"tag": f"%{tag}"},
        ).all()
    )
    assert archived == {f"Evergreen {tag}": False, f"Old {tag}": True}
