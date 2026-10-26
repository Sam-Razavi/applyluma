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


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Query:
    def __init__(self, db, model):
        self._db = db
        self._model = model

    def filter(self, *args):
        return self

    def update(self, values, synchronize_session=None):
        self._db.writes.append(("update", self._model))
        return self._db.last_batch_size

    def delete(self, synchronize_session=None):
        self._db.writes.append(("delete", self._model))
        return self._db.last_batch_size


class _BatchDb:
    """Serves queued id batches to db.execute() and records writes/commits."""

    def __init__(self, batches):
        self._batches = list(batches)
        self.writes: list = []
        self.commits = 0
        self.last_batch_size = 0

    def execute(self, stmt):
        rows = self._batches.pop(0) if self._batches else []
        self.last_batch_size = len(rows)
        return _Result([(r,) for r in rows])

    def query(self, model):
        return _Query(self, model)

    def commit(self):
        self.commits += 1


def test_is_referenced_covers_saved_jobs_and_applications() -> None:
    sql = _sql(job_retention._is_referenced())
    assert "FROM saved_jobs" in sql
    assert "FROM applications" in sql


def test_purge_commits_each_batch_until_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job_retention, "BATCH_SIZE", 2)
    db = _BatchDb([["a", "b"], ["c", "d"], ["e"], []])

    purged = job_retention._purge(db, datetime.now(UTC))

    assert purged == 5
    assert db.commits == 3  # one commit per non-empty batch, never one big transaction


def test_purge_stops_at_the_per_run_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(job_retention, "BATCH_SIZE", 2)
    monkeypatch.setattr(job_retention, "MAX_BATCHES_PER_RUN", 3)
    db = _BatchDb([["a", "b"]] * 10)  # a backlog bigger than one night's cap

    purged = job_retention._purge(db, datetime.now(UTC))

    assert purged == 6
    assert db.commits == 3


def test_archive_slims_unreferenced_in_the_same_write(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting

    monkeypatch.setattr(job_retention, "BATCH_SIZE", 3)
    # batch of 3 eligible ids; of those, "a" and "b" are unreferenced; then empty.
    db = _BatchDb([["a", "b", "c"], ["a", "b"], []])

    archived, slimmed = job_retention._archive(db, datetime.now(UTC))

    assert archived == 3
    assert slimmed == 2
    assert db.commits == 1
    assert db.writes == [
        ("delete", JobMatchingScore),
        ("delete", ExtractedKeyword),
        ("update", RawJobPosting),  # archive + slim the unreferenced rows at once
        ("update", RawJobPosting),  # archive only the referenced row
    ]


def test_task_purges_first_and_reports_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class _Db:
        closed = False

        def rollback(self):
            pass

        def close(self):
            self.closed = True

    db = _Db()
    monkeypatch.setattr(job_retention, "SessionLocal", lambda: db)
    monkeypatch.setattr(job_retention, "_purge", lambda d, now: calls.append("purge") or 4)
    monkeypatch.setattr(
        job_retention, "_archive", lambda d, now: calls.append("archive") or (10, 7)
    )
    monkeypatch.setattr(job_retention, "_slim_released", lambda d: calls.append("slim") or 1)

    result = job_retention.archive_and_purge_job_postings.run()

    assert calls == ["purge", "archive", "slim"]  # free space before using any
    assert result == {"archived": 10, "slimmed": 8, "purged": 4}
    assert db.closed


def test_task_rolls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Db:
        rolled_back = closed = False

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    def boom(d, now):
        raise RuntimeError("db down")

    db = _Db()
    monkeypatch.setattr(job_retention, "SessionLocal", lambda: db)
    monkeypatch.setattr(job_retention, "_purge", boom)

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
    # Tiny batches so archive, slim and purge each span several commits.
    monkeypatch.setattr(job_retention, "BATCH_SIZE", 2)

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
