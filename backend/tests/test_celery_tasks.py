"""Tests for run_tailoring and run_cover_letter Celery tasks."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks import cover_letter as cover_letter_tasks
from app.tasks import tailor as tailor_tasks

JOB_ID = str(uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class _FakeCache:
    """In-memory stand-in for CacheService so tests never touch real Redis."""

    def __init__(self, get_raises: bool = False, set_raises: bool = False):
        self.store: dict[str, dict] = {}
        self.get_raises = get_raises
        self.set_raises = set_raises
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, dict]] = []

    def get_cached_tailor_result(self, cache_key: str):
        self.get_calls.append(cache_key)
        if self.get_raises:
            raise RuntimeError("redis down")
        return self.store.get(cache_key)

    def set_cached_tailor_result(self, cache_key: str, result: dict, ttl_seconds: int | None = None):
        self.set_calls.append((cache_key, result))
        if self.set_raises:
            raise RuntimeError("redis down")
        self.store[cache_key] = result


class _FakeDelay:
    """Records .delay(...) calls made against a Celery task without dispatching."""

    def __init__(self):
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)


# ---------------------------------------------------------------------------
# Shared fake collaborators
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, result=None):
        self._result = result

    def filter(self, *args):
        return self

    def first(self):
        return self._result


class _FakeDb:
    def __init__(self, job=None, cv=None, jd=None):
        self._job = job
        self._cv = cv
        self._jd = jd

    def query(self, model):
        from app.models.cover_letter_job import CoverLetterJob
        from app.models.cv import CV
        from app.models.job_description import JobDescription
        from app.models.tailor_job import TailorJob
        if model is TailorJob or model is CoverLetterJob:
            return _FakeQuery(self._job)
        if model is CV:
            return _FakeQuery(self._cv)
        if model is JobDescription:
            return _FakeQuery(self._jd)
        return _FakeQuery()

    def close(self):
        pass


def _make_tailor_job(**overrides):
    from app.models.tailor_job import TailorStatus
    base = {
        "id": uuid.UUID(JOB_ID),
        "user_id": USER_ID,
        "cv_id": uuid.uuid4(),
        "job_description_id": uuid.uuid4(),
        "status": TailorStatus.pending,
        "intensity": "moderate",
        "user": SimpleNamespace(email="sam@example.com"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_cl_job(**overrides):
    from app.models.cover_letter_job import CoverLetterStatus
    base = {
        "id": uuid.UUID(JOB_ID),
        "user_id": USER_ID,
        "cv_id": uuid.uuid4(),
        "job_description_id": uuid.uuid4(),
        "status": CoverLetterStatus.pending,
        "tone": "formal",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_cv(content="Experienced developer with Python skills"):
    return SimpleNamespace(id=uuid.uuid4(), content=content)


def _make_jd(**overrides):
    base = {
        "id": uuid.uuid4(),
        "description": "Looking for a backend developer",
        "keywords": ["Python", "FastAPI"],
        "company_name": "Acme Corp",
        "job_title": "Backend Developer",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# run_tailoring
# ---------------------------------------------------------------------------

def test_run_tailoring_job_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb(job=None)
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"error": "job not found"}


def test_run_tailoring_job_already_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.tailor_job import TailorStatus
    job = _make_tailor_job(status=TailorStatus.complete)
    db = _FakeDb(job=job)
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert "already" in result["error"]


def _patch_tailor_common(monkeypatch: pytest.MonkeyPatch, cache: _FakeCache) -> _FakeDelay:
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_processing", lambda db, j: None)
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_complete", lambda db, j, **kw: None)
    monkeypatch.setattr(tailor_tasks, "CacheService", lambda: cache)
    notify_delay = _FakeDelay()
    monkeypatch.setattr(tailor_tasks.send_notification_async, "delay", notify_delay)
    return notify_delay


def test_run_tailoring_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_tailor_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=_make_jd())
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)

    fake_result = {"sections": [], "language": "en"}
    monkeypatch.setattr(tailor_tasks, "tailor_cv", lambda **kw: fake_result)
    cache = _FakeCache()
    notify_delay = _patch_tailor_common(monkeypatch, cache)

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"status": "complete", "job_id": JOB_ID}
    # The result was cached for next time, and the completion notification
    # was dispatched async rather than sent inline.
    assert cache.set_calls == [(cache.get_calls[0], fake_result)]
    assert len(notify_delay.calls) == 1
    assert notify_delay.calls[0]["type"] == "tailor_complete"
    assert notify_delay.calls[0]["send_email"] is True


def test_run_tailoring_cache_hit_skips_tailor_cv(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_tailor_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=_make_jd())
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)

    tailor_cv_calls: list[dict] = []
    monkeypatch.setattr(
        tailor_tasks, "tailor_cv", lambda **kw: tailor_cv_calls.append(kw) or {"language": "en"}
    )
    cache = _FakeCache()
    cached_result = {"sections": [], "language": "en", "structured_cv": {}}
    # Pre-seed the cache under the exact key run_tailoring will compute.
    key = tailor_tasks.tailor_cache_key(
        job.user_id, db._cv.content, db._jd.description, db._jd.keywords or [], job.intensity
    )
    cache.store[key] = cached_result
    _patch_tailor_common(monkeypatch, cache)

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"status": "complete", "job_id": JOB_ID}
    assert tailor_cv_calls == []  # no OpenAI call made on a cache hit
    assert cache.set_calls == []  # re-caching an already-cached result is pointless


def test_run_tailoring_cache_read_failure_falls_back_to_fresh_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Redis outage on the cache read must not break tailoring."""
    job = _make_tailor_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=_make_jd())
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)

    fake_result = {"sections": [], "language": "en"}
    monkeypatch.setattr(tailor_tasks, "tailor_cv", lambda **kw: fake_result)
    cache = _FakeCache(get_raises=True)
    _patch_tailor_common(monkeypatch, cache)

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"status": "complete", "job_id": JOB_ID}


def test_run_tailoring_cache_write_failure_still_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Redis outage on the cache write must not break tailoring either."""
    job = _make_tailor_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=_make_jd())
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)

    fake_result = {"sections": [], "language": "en"}
    monkeypatch.setattr(tailor_tasks, "tailor_cv", lambda **kw: fake_result)
    cache = _FakeCache(set_raises=True)
    _patch_tailor_common(monkeypatch, cache)

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"status": "complete", "job_id": JOB_ID}


def test_run_tailoring_missing_cv_content_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing CV content is deterministic: the job is failed immediately, no retries."""
    job = _make_tailor_job()
    db = _FakeDb(job=job, cv=_make_cv(content=""), jd=_make_jd())
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_processing", lambda db, j: None)
    failed: list[str] = []
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_failed", lambda db, j, msg: failed.append(msg))

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"error": "CV has no text content"}
    assert failed == ["CV has no text content"]


def test_run_tailoring_missing_jd_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_tailor_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=None)
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_processing", lambda db, j: None)
    failed: list[str] = []
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_failed", lambda db, j, msg: failed.append(msg))

    result = tailor_tasks.run_tailoring.run(JOB_ID)

    assert result == {"error": "Job description not found"}
    assert failed == ["Job description not found"]


# ---------------------------------------------------------------------------
# run_cover_letter
# ---------------------------------------------------------------------------

def test_run_cover_letter_job_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _FakeDb(job=None)
    monkeypatch.setattr(cover_letter_tasks, "SessionLocal", lambda: db)

    result = cover_letter_tasks.run_cover_letter.run(JOB_ID)

    assert result == {"error": "job not found"}


def test_run_cover_letter_job_already_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.cover_letter_job import CoverLetterStatus
    job = _make_cl_job(status=CoverLetterStatus.complete)
    db = _FakeDb(job=job)
    monkeypatch.setattr(cover_letter_tasks, "SessionLocal", lambda: db)

    result = cover_letter_tasks.run_cover_letter.run(JOB_ID)

    assert "already" in result["error"]


def test_run_cover_letter_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_cl_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=_make_jd())
    monkeypatch.setattr(cover_letter_tasks, "SessionLocal", lambda: db)

    fake_result = {"cover_letter_text": "Dear Hiring Manager...", "language": "en", "word_count": 250}
    monkeypatch.setattr(cover_letter_tasks, "generate_cover_letter", lambda **kw: fake_result)
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_processing", lambda db, j: None)
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_complete", lambda db, j, **kw: None)
    monkeypatch.setattr(
        cover_letter_tasks.notification_service, "create_notification", lambda db, **kw: None
    )

    result = cover_letter_tasks.run_cover_letter.run(JOB_ID)

    assert result == {"status": "complete", "job_id": JOB_ID}


def test_run_cover_letter_missing_cv_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_cl_job()
    db = _FakeDb(job=job, cv=None, jd=_make_jd())
    monkeypatch.setattr(cover_letter_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_processing", lambda db, j: None)
    failed: list[str] = []
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_failed", lambda db, j, msg: failed.append(msg))

    result = cover_letter_tasks.run_cover_letter.run(JOB_ID)

    assert result == {"error": "CV has no text content"}
    assert failed == ["CV has no text content"]


def test_run_cover_letter_missing_jd_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_cl_job()
    db = _FakeDb(job=job, cv=_make_cv(), jd=None)
    monkeypatch.setattr(cover_letter_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_processing", lambda db, j: None)
    failed: list[str] = []
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_failed", lambda db, j, msg: failed.append(msg))

    result = cover_letter_tasks.run_cover_letter.run(JOB_ID)

    assert result == {"error": "Job description not found"}
    assert failed == ["Job description not found"]


# ---------------------------------------------------------------------------
# on_failure callbacks
# ---------------------------------------------------------------------------

def test_tailor_task_on_failure_marks_job_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.tailor_job import TailorStatus
    job = _make_tailor_job(status=TailorStatus.processing)
    db = _FakeDb(job=job)
    monkeypatch.setattr(tailor_tasks, "SessionLocal", lambda: db)
    failed: list[str] = []
    monkeypatch.setattr(tailor_tasks.crud_tailor, "set_failed", lambda db, j, msg: failed.append(msg))

    tailor_tasks.run_tailoring.on_failure(ValueError("boom"), "tid", [JOB_ID], {}, None)

    assert len(failed) == 1
    assert "boom" in failed[0]


def test_tailor_task_on_failure_no_job_id_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """on_failure with no args and empty kwargs returns early without touching the DB."""
    tailor_tasks.run_tailoring.on_failure(ValueError("err"), "tid", [], {}, None)


def test_cover_letter_task_on_failure_marks_job_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.cover_letter_job import CoverLetterStatus
    job = _make_cl_job(status=CoverLetterStatus.processing)
    db = _FakeDb(job=job)
    monkeypatch.setattr(cover_letter_tasks, "SessionLocal", lambda: db)
    failed: list[str] = []
    monkeypatch.setattr(cover_letter_tasks.crud_cl, "set_failed", lambda db, j, msg: failed.append(msg))

    cover_letter_tasks.run_cover_letter.on_failure(ValueError("cl-err"), "tid", [JOB_ID], {}, None)

    assert len(failed) == 1
    assert "cl-err" in failed[0]


def test_cover_letter_task_on_failure_no_job_id_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """on_failure with empty args/kwargs returns early without DB access."""
    cover_letter_tasks.run_cover_letter.on_failure(ValueError("err"), "tid", [], {}, None)
