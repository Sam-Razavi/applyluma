"""Unit tests for app/crud/tailor_job.py."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import tailor_job as crud_tailor
from app.models.tailor_job import TailorIntensity, TailorStatus

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CV_ID = uuid.uuid4()
JD_ID = uuid.uuid4()


def _make_job(**overrides):
    base = {
        "id": JOB_ID,
        "user_id": USER_ID,
        "cv_id": CV_ID,
        "job_description_id": JD_ID,
        "status": TailorStatus.pending,
        "intensity": TailorIntensity.medium,
        "celery_task_id": None,
        "result_json": None,
        "language": None,
        "error_message": None,
        "output_cv_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeDb:
    def __init__(self, job=None):
        self._job = job
        self.committed = False
        self.added = None

    def query(self, model):
        return _FakeQuery(self._job)

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass


class _FakeQuery:
    def __init__(self, result=None):
        self._result = result

    def options(self, *args):
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def limit(self, n):
        return self

    def all(self):
        return [self._result] if self._result else []

    def first(self):
        return self._result

    def scalar(self):
        return 0


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_tailor_job_adds_and_commits() -> None:
    db = _FakeDb()

    crud_tailor.create(
        db,
        user_id=USER_ID,
        cv_id=CV_ID,
        job_description_id=JD_ID,
        intensity=TailorIntensity.medium,
    )

    assert db.added is not None
    assert db.committed


# ---------------------------------------------------------------------------
# set_processing
# ---------------------------------------------------------------------------

def test_set_processing_changes_status() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_tailor.set_processing(db, job)

    assert job.status == TailorStatus.processing
    assert db.committed


def test_set_processing_with_celery_task_id() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_tailor.set_processing(db, job, celery_task_id="task-abc-123")

    assert job.celery_task_id == "task-abc-123"
    assert db.committed


# ---------------------------------------------------------------------------
# set_complete
# ---------------------------------------------------------------------------

def test_set_complete_sets_result_and_status() -> None:
    job = _make_job(status=TailorStatus.processing)
    db = _FakeDb(job=job)

    crud_tailor.set_complete(
        db, job, result_json={"sections": []}, language="en"
    )

    assert job.status == TailorStatus.complete
    assert job.result_json == {"sections": []}
    assert job.language == "en"
    assert job.error_message is None
    assert db.committed


# ---------------------------------------------------------------------------
# set_failed
# ---------------------------------------------------------------------------

def test_set_failed_sets_error_message() -> None:
    job = _make_job(status=TailorStatus.processing)
    db = _FakeDb(job=job)

    crud_tailor.set_failed(db, job, "OpenAI timeout")

    assert job.status == TailorStatus.failed
    assert job.error_message == "OpenAI timeout"
    assert db.committed


# ---------------------------------------------------------------------------
# set_task_id
# ---------------------------------------------------------------------------

def test_set_task_id_stores_celery_id() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_tailor.set_task_id(db, job, "celery-task-xyz")

    assert job.celery_task_id == "celery-task-xyz"
    assert db.committed


# ---------------------------------------------------------------------------
# set_output_cv
# ---------------------------------------------------------------------------

def test_set_output_cv_stores_cv_id() -> None:
    job = _make_job()
    output_cv_id = uuid.uuid4()
    db = _FakeDb(job=job)

    crud_tailor.set_output_cv(db, job, output_cv_id)

    assert job.output_cv_id == output_cv_id
    assert db.committed


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

def test_get_by_id_returns_job() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    result = crud_tailor.get_by_id(db, JOB_ID, USER_ID)

    assert result is job


def test_get_by_id_returns_none_when_not_found() -> None:
    db = _FakeDb(job=None)

    result = crud_tailor.get_by_id(db, JOB_ID, USER_ID)

    assert result is None


# ---------------------------------------------------------------------------
# list_for_user
# ---------------------------------------------------------------------------

def test_list_for_user_returns_jobs() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    result = crud_tailor.list_for_user(db, USER_ID)

    assert job in result


# ---------------------------------------------------------------------------
# count_today
# ---------------------------------------------------------------------------

def test_count_today_returns_zero_when_empty() -> None:
    db = _FakeDb()

    count = crud_tailor.count_today(db, USER_ID)

    assert count == 0
