"""Tests for the daily job-posting retention task (archive → slim → purge)."""
from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks import job_retention


def _sql(clause) -> str:
    return " ".join(str(clause.compile(dialect=postgresql.dialect())).split())


class _Query:
    def __init__(self, log: list, model):
        self._log = log
        self._model = model

    def filter(self, *args):
        self._log.append(("filter", self._model, args))
        return self

    def update(self, values, synchronize_session=None):
        self._log.append(("update", self._model, values))
        return 2

    def delete(self, synchronize_session=None):
        self._log.append(("delete", self._model, None))
        return 1


class _Db:
    def __init__(self):
        self.log: list = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def query(self, model):
        return _Query(self.log, model)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_is_referenced_covers_saved_jobs_and_applications() -> None:
    sql = _sql(job_retention._is_referenced())
    assert "FROM saved_jobs" in sql
    assert "FROM applications" in sql


def test_task_archives_slims_and_purges(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting

    db = _Db()
    monkeypatch.setattr(job_retention, "SessionLocal", lambda: db)

    result = job_retention.archive_and_purge_job_postings.run()

    assert result == {"archived": 2, "slimmed": 2, "purged": 1}
    assert db.committed and db.closed and not db.rolled_back

    filters = [args for kind, model, args in db.log if kind == "filter" and model is RawJobPosting]
    archive_sql = " ".join(_sql(c) for c in filters[0])
    assert "archived_at IS NULL" in archive_sql
    assert "application_deadline <" in archive_sql
    assert "scraped_at <" in archive_sql

    purge_sql = " ".join(_sql(c) for c in filters[-1])
    assert "archived_at <" in purge_sql
    assert "NOT ((EXISTS" in purge_sql  # referenced postings are never purged

    deleted = [model for kind, model, _ in db.log if kind == "delete"]
    assert deleted == [JobMatchingScore, ExtractedKeyword, RawJobPosting]


def test_task_rolls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailingDb(_Db):
        def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb()
    monkeypatch.setattr(job_retention, "SessionLocal", lambda: db)

    with pytest.raises(RuntimeError):
        job_retention.archive_and_purge_job_postings.run()
    assert db.rolled_back and db.closed


# ---------------------------------------------------------------------------
# Against a real, migrated Postgres (opt-in: CI has no database).
#   TEST_DATABASE_URL=postgresql://... pytest tests/test_job_retention.py
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="needs TEST_DATABASE_URL")
def test_retention_against_real_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.crud import job as crud_job
    from app.models.application import Application
    from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting, SavedJob
    from app.models.user import User

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(job_retention, "SessionLocal", Session)

    now = datetime.now(UTC)
    tag = uuid.uuid4().hex[:8]
    db = Session()
    user = User(email=f"retention-{tag}@example.com", hashed_password="x")
    db.add(user)
    db.flush()
    user_id = user.id

    def posting(name: str, **kw) -> uuid.UUID:
        p = RawJobPosting(
            source=f"test-{tag}", job_id_external=name, title=name, company="Acme",
            description="long description " * 50, url=f"https://example.com/{tag}/{name}",
            raw_data={"big": "x" * 500}, **kw,
        )
        db.add(p)
        db.flush()
        db.add(ExtractedKeyword(raw_job_posting_id=p.id, keyword="python", keyword_type="technical_skills"))
        db.add(JobMatchingScore(user_id=user_id, raw_job_posting_id=p.id, overall_score=90.0))
        return p.id

    ids = {
        "fresh": posting("fresh"),
        "expired": posting("expired", application_deadline=now - timedelta(days=1)),
        "old": posting("old", scraped_at=now - timedelta(days=40)),
        "old_saved": posting("old_saved", scraped_at=now - timedelta(days=40)),
        "old_applied": posting("old_applied", scraped_at=now - timedelta(days=40)),
        "stale_archive": posting(
            "stale_archive", scraped_at=now - timedelta(days=200), archived_at=now - timedelta(days=100)
        ),
        "stale_archive_saved": posting(
            "stale_archive_saved", scraped_at=now - timedelta(days=200), archived_at=now - timedelta(days=100)
        ),
    }
    db.add(SavedJob(user_id=user_id, raw_job_posting_id=ids["old_saved"]))
    db.add(SavedJob(user_id=user_id, raw_job_posting_id=ids["stale_archive_saved"]))
    db.add(Application(
        user_id=user_id, raw_job_posting_id=ids["old_applied"],
        company_name="Acme", job_title="Dev", status="applied",
    ))
    db.commit()
    db.close()

    try:
        job_retention.archive_and_purge_job_postings.run()
        # Idempotent: a second run finds nothing new for these rows.
        job_retention.archive_and_purge_job_postings.run()

        db = Session()

        def state(name: str):
            p = db.get(RawJobPosting, ids[name])
            if p is None:
                return None
            scores = db.query(JobMatchingScore).filter_by(raw_job_posting_id=p.id).count()
            return p.archived_at is not None, bool(p.description), scores

        assert state("fresh") == (False, True, 1)
        assert state("expired") == (True, False, 0)  # archived and slimmed
        assert state("old") == (True, False, 0)
        assert state("old_saved") == (True, True, 1)  # referenced: content kept
        assert state("old_applied") == (True, True, 1)
        assert state("stale_archive") is None  # purged
        assert state("stale_archive_saved") == (True, True, 1)

        feed = {j["title"] for j in crud_job.list_jobs(db, user_id, limit=100)}
        assert "fresh" in feed
        assert feed.isdisjoint(set(ids) - {"fresh"})
        db.close()
    finally:
        db = Session()
        db.query(User).filter_by(id=user_id).delete()
        db.query(RawJobPosting).filter_by(source=f"test-{tag}").delete()
        db.commit()
        db.close()
