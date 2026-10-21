"""Tests for the compute_job_matching_scores Celery task."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks import matching as matching_tasks

USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
POSTING_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_posting(**overrides):
    base = {
        "id": POSTING_ID,
        "description": "Python developer role",
        "title": "Software Engineer",
        "salary_min": 50_000,
        "salary_max": 90_000,
        "location": "Stockholm",
        "remote_allowed": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _fake_score():
    return {
        "overall_score": 75.0,
        "skills_match": 80.0,
        "experience_match": 70.0,
        "salary_match": 75.0,
        "education_match": 70.0,
        "location_match": 80.0,
        "explanation": "Good match",
    }


class _FakeQuery:
    """Chainable query that returns pre-set results; filter args are ignored."""

    def __init__(self, all_results=None, first_result=None):
        self._all = all_results if all_results is not None else []
        self._first = first_result

    def filter(self, *args):
        return self

    def limit(self, n):
        return self

    def options(self, *args):
        return self

    def order_by(self, *args):
        return self

    def subquery(self):
        # Real SQLAlchemy subquery — no DB connection needed.
        # Required so ~RawJobPosting.id.in_(subq) constructs without error.
        from sqlalchemy import false, select
        from app.models.job import JobMatchingScore
        return select(JobMatchingScore.raw_job_posting_id).where(false()).subquery()

    def all(self):
        return self._all

    def first(self):
        return self._first


class _FakeDb:
    def __init__(self, postings=None, existing_score=None):
        self._postings = postings or []
        self._existing_score = existing_score
        self.added: list = []
        self.committed = False

    def query(self, model):
        from app.models.job import RawJobPosting
        if model is RawJobPosting:
            return _FakeQuery(all_results=self._postings)
        existing = [self._existing_score] if self._existing_score is not None else []
        return _FakeQuery(all_results=existing, first_result=self._existing_score)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


class _FakeCache:
    def __init__(self):
        self.stored: list = []

    def set_cached_score(self, user_id, posting_id, result):
        self.stored.append((user_id, posting_id))


def test_happy_path_scores_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    posting = _make_posting()
    db = _FakeDb(postings=[posting])
    cache = _FakeCache()

    monkeypatch.setattr(matching_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(matching_tasks, "CacheService", lambda: cache)

    class _Svc:
        def __init__(self, db): pass
        def calculate_match_score(self, uid, pid, job_data):
            return _fake_score()

    monkeypatch.setattr(matching_tasks, "MatchingService", _Svc)

    result = matching_tasks.compute_job_matching_scores.run(USER_ID)

    assert result == {"status": "ok", "scored": 1}
    assert len(db.added) == 1
    assert db.committed
    assert len(cache.stored) == 1


def test_no_postings_returns_early(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb(postings=[])
    monkeypatch.setattr(matching_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(matching_tasks, "CacheService", lambda: _FakeCache())
    monkeypatch.setattr(matching_tasks, "MatchingService", lambda db: None)

    result = matching_tasks.compute_job_matching_scores.run(USER_ID)

    assert result == {"status": "ok", "scored": 0}
    assert not db.committed


def test_invalid_uuid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb()
    monkeypatch.setattr(matching_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(matching_tasks, "CacheService", lambda: _FakeCache())
    monkeypatch.setattr(matching_tasks, "MatchingService", lambda db: None)

    with pytest.raises(Exception):
        matching_tasks.compute_job_matching_scores.run("not-a-valid-uuid")


def test_partial_failure_skips_one_posting(monkeypatch: pytest.MonkeyPatch) -> None:
    postings = [_make_posting(), _make_posting(id=uuid.uuid4())]
    db = _FakeDb(postings=postings)
    cache = _FakeCache()
    monkeypatch.setattr(matching_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(matching_tasks, "CacheService", lambda: cache)

    calls = [0]

    class _PartialService:
        def __init__(self, db): pass
        def calculate_match_score(self, uid, pid, job_data):
            calls[0] += 1
            if calls[0] == 1:
                raise ValueError("Scoring failed for first posting")
            return _fake_score()

    monkeypatch.setattr(matching_tasks, "MatchingService", _PartialService)

    result = matching_tasks.compute_job_matching_scores.run(USER_ID)

    assert result["status"] == "ok"
    assert result["scored"] == 1
    assert len(db.added) == 1


def test_updates_existing_score_in_place(monkeypatch: pytest.MonkeyPatch) -> None:
    posting = _make_posting()
    existing = SimpleNamespace(
        raw_job_posting_id=POSTING_ID,
        overall_score=50.0,
        skills_match=50.0,
        experience_match=50.0,
        salary_match=50.0,
        education_match=50.0,
        location_match=50.0,
        explanation="Old match",
        computed_at=None,
        cached_at=None,
    )
    db = _FakeDb(postings=[posting], existing_score=existing)
    cache = _FakeCache()
    monkeypatch.setattr(matching_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(matching_tasks, "CacheService", lambda: cache)

    class _Svc:
        def __init__(self, db): pass
        def calculate_match_score(self, uid, pid, job_data):
            return _fake_score()

    monkeypatch.setattr(matching_tasks, "MatchingService", _Svc)

    result = matching_tasks.compute_job_matching_scores.run(USER_ID)

    assert result["scored"] == 1
    assert len(db.added) == 0  # Updated in place — no new row
    assert existing.overall_score == 75.0
    assert existing.explanation == "Good match"


class _CapturingQuery(_FakeQuery):
    def __init__(self, log: dict, key: str, all_results=None):
        super().__init__(all_results=all_results)
        self._log = log
        self._key = key

    def filter(self, *args):
        self._log.setdefault(self._key, []).extend(args)
        return self

    def order_by(self, *args):
        self._log["order_by"] = args
        return self

    def limit(self, n):
        self._log["limit"] = n
        return self


class _ScoringService:
    def __init__(self, db):
        pass

    def calculate_match_score(self, uid, pid, job_data):
        return _fake_score()


def _run_capturing(
    monkeypatch: pytest.MonkeyPatch, postings=None, service=_ScoringService, **kwargs
) -> dict:
    from sqlalchemy.dialects import postgresql

    from app.models.job import JobMatchingScore, RawJobPosting

    log: dict = {"chained": []}

    class _Db(_FakeDb):
        def query(self, model):
            if model is RawJobPosting:
                return _CapturingQuery(log, "posting_filters", all_results=postings or [])
            if model is JobMatchingScore.raw_job_posting_id:
                return _CapturingQuery(log, "scored_filters")
            return super().query(model)

    monkeypatch.setattr(matching_tasks, "SessionLocal", lambda: _Db())
    monkeypatch.setattr(matching_tasks, "CacheService", _FakeCache)
    monkeypatch.setattr(matching_tasks, "MatchingService", service)
    monkeypatch.setattr(
        matching_tasks.compute_job_matching_scores,
        "delay",
        lambda *args, **kw: log["chained"].append((args, kw)),
    )
    log["result"] = matching_tasks.compute_job_matching_scores.run(USER_ID, **kwargs)
    log["sql"] = " ".join(
        str(f.compile(dialect=postgresql.dialect())) for f in log.get("posting_filters", [])
    )
    # The bound value of the "computed_at >= cutoff" condition.
    log["cutoff"] = next(
        f.right.value
        for f in log.get("scored_filters", [])
        if getattr(f.left, "key", None) == "computed_at"
    )
    return log


def test_scheduled_run_skips_recent_scores_and_scores_newest_live_jobs_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime, timedelta

    log = _run_capturing(monkeypatch)

    assert "NOT IN" in log["sql"]  # recently scored postings are skipped
    assert "application_deadline" in log["sql"]  # expired postings are skipped
    assert "scraped_at DESC" in str(log["order_by"][0].compile())
    assert log["limit"] == matching_tasks.BATCH_LIMIT
    assert abs(log["cutoff"] - (datetime.now(UTC) - timedelta(hours=24))) < timedelta(minutes=1)


def test_forced_run_rescores_everything_scored_before_now(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime, timedelta

    log = _run_capturing(monkeypatch, force=True)

    # Not a 24h window: anything scored against the old CV is stale.
    assert abs(log["cutoff"] - datetime.now(UTC)) < timedelta(minutes=1)


def test_forced_run_chains_the_next_batch_with_the_same_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(matching_tasks, "BATCH_LIMIT", 2)
    full_batch = [_make_posting(id=uuid.uuid4()), _make_posting(id=uuid.uuid4())]

    log = _run_capturing(monkeypatch, postings=full_batch, force=True)

    assert log["result"]["scored"] == 2
    [(args, kwargs)] = log["chained"]
    assert args == (USER_ID,)
    assert kwargs["rescore_before"] == log["cutoff"].isoformat()


def test_forced_run_stops_after_a_partial_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matching_tasks, "BATCH_LIMIT", 2)

    log = _run_capturing(monkeypatch, postings=[_make_posting()], force=True)

    assert log["chained"] == []


def test_forced_run_stops_when_nothing_could_be_scored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Postings that always fail must not re-enqueue the chain forever."""
    monkeypatch.setattr(matching_tasks, "BATCH_LIMIT", 2)

    class _FailingService(_ScoringService):
        def calculate_match_score(self, uid, pid, job_data):
            raise RuntimeError("bad posting")

    full_batch = [_make_posting(id=uuid.uuid4()), _make_posting(id=uuid.uuid4())]
    log = _run_capturing(monkeypatch, postings=full_batch, service=_FailingService, force=True)

    assert log["result"]["scored"] == 0
    assert log["chained"] == []


def test_scheduled_run_never_chains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matching_tasks, "BATCH_LIMIT", 2)
    full_batch = [_make_posting(id=uuid.uuid4()), _make_posting(id=uuid.uuid4())]

    log = _run_capturing(monkeypatch, postings=full_batch)

    assert log["chained"] == []
