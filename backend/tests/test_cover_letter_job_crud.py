"""Unit tests for app/crud/cover_letter_job.py."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import cover_letter_job as crud_cl
from app.models.cover_letter_job import CoverLetterStatus, CoverLetterTone

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
        "status": CoverLetterStatus.pending,
        "tone": CoverLetterTone.formal,
        "celery_task_id": None,
        "generated_text": None,
        "saved_text": None,
        "is_saved": False,
        "title": None,
        "language": None,
        "word_count": 0,
        "error_message": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeDb:
    def __init__(self, job=None):
        self._job = job
        self.committed = False
        self.added = None
        self.deleted = None

    def query(self, model):
        return _FakeQuery(self._job)

    def add(self, obj):
        self.added = obj

    def delete(self, obj):
        self.deleted = obj

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

def test_create_cl_job_adds_and_commits() -> None:
    db = _FakeDb()

    crud_cl.create(
        db,
        user_id=USER_ID,
        cv_id=CV_ID,
        job_description_id=JD_ID,
        tone=CoverLetterTone.formal,
    )

    assert db.added is not None
    assert db.committed


# ---------------------------------------------------------------------------
# set_processing
# ---------------------------------------------------------------------------

def test_set_processing_changes_status() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_cl.set_processing(db, job)

    assert job.status == CoverLetterStatus.processing
    assert db.committed


def test_set_processing_with_celery_task_id() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_cl.set_processing(db, job, celery_task_id="celery-123")

    assert job.celery_task_id == "celery-123"
    assert db.committed


# ---------------------------------------------------------------------------
# set_task_id
# ---------------------------------------------------------------------------

def test_set_task_id_stores_id() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_cl.set_task_id(db, job, "task-xyz")

    assert job.celery_task_id == "task-xyz"
    assert db.committed


# ---------------------------------------------------------------------------
# set_complete
# ---------------------------------------------------------------------------

def test_set_complete_sets_all_fields() -> None:
    job = _make_job(status=CoverLetterStatus.processing)
    db = _FakeDb(job=job)

    crud_cl.set_complete(
        db,
        job,
        generated_text="Dear Hiring Manager...",
        language="en",
        word_count=250,
    )

    assert job.status == CoverLetterStatus.complete
    assert job.generated_text == "Dear Hiring Manager..."
    assert job.language == "en"
    assert job.word_count == 250
    assert job.error_message is None
    assert db.committed


# ---------------------------------------------------------------------------
# set_failed
# ---------------------------------------------------------------------------

def test_set_failed_sets_error() -> None:
    job = _make_job(status=CoverLetterStatus.processing)
    db = _FakeDb(job=job)

    crud_cl.set_failed(db, job, "Generation failed")

    assert job.status == CoverLetterStatus.failed
    assert job.error_message == "Generation failed"
    assert db.committed


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------

def test_save_sets_saved_fields() -> None:
    job = _make_job(status=CoverLetterStatus.complete, generated_text="Dear Hiring Manager...")
    db = _FakeDb(job=job)

    crud_cl.save(db, job, saved_text="Edited letter text.", title="My Cover Letter")

    assert job.is_saved is True
    assert job.saved_text == "Edited letter text."
    assert job.title == "My Cover Letter"
    assert db.committed


def test_save_without_title_skips_title() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_cl.save(db, job, saved_text="Letter text.", title=None)

    assert job.is_saved is True
    assert db.committed


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_cl_job_commits() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    crud_cl.delete(db, job)

    assert db.deleted is job
    assert db.committed


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

def test_get_by_id_returns_job() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    result = crud_cl.get_by_id(db, JOB_ID, USER_ID)

    assert result is job


def test_get_by_id_returns_none_when_not_found() -> None:
    db = _FakeDb(job=None)

    result = crud_cl.get_by_id(db, JOB_ID, USER_ID)

    assert result is None


# ---------------------------------------------------------------------------
# list_for_user
# ---------------------------------------------------------------------------

def test_list_for_user_returns_jobs() -> None:
    job = _make_job()
    db = _FakeDb(job=job)

    result = crud_cl.list_for_user(db, USER_ID)

    assert job in result


# ---------------------------------------------------------------------------
# count_today
# ---------------------------------------------------------------------------

def test_count_today_returns_zero() -> None:
    db = _FakeDb()

    count = crud_cl.count_today(db, USER_ID)

    assert count == 0
