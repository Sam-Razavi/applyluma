"""Unit tests for crud.job skill-gap derivation."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import job as crud_job

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    """Minimal stub: db.query(CV).filter(...).first() -> the configured CV."""

    def __init__(self, cv=None):
        self._cv = cv

    def query(self, _model):
        return _FakeQuery(self._cv)


def _posting(keywords: list[str]) -> SimpleNamespace:
    return SimpleNamespace(keywords=[SimpleNamespace(keyword=k) for k in keywords])


class _StubExtractor:
    """Returns a fixed categorised keyword dict, ignoring input text."""

    def extract_keywords(self, _text: str) -> dict[str, list[dict]]:
        return {
            "technical_skills": [
                {"keyword": "Python", "confidence": 1.0, "frequency": 1},
                {"keyword": "FastAPI", "confidence": 1.0, "frequency": 1},
            ],
        }


def test_skill_gap_partitions_matched_and_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crud_job, "KeywordExtractor", _StubExtractor)
    db = _FakeDb(cv=SimpleNamespace(content="... Python and FastAPI ..."))
    posting = _posting(["Python", "FastAPI", "Rust"])

    matched, missing = crud_job._compute_skill_gap(db, USER_ID, posting)

    assert matched == ["Python", "FastAPI"]
    assert missing == ["Rust"]


def test_skill_gap_empty_when_no_default_cv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crud_job, "KeywordExtractor", _StubExtractor)
    db = _FakeDb(cv=None)
    posting = _posting(["Python", "Rust"])

    assert crud_job._compute_skill_gap(db, USER_ID, posting) == ([], [])


def test_skill_gap_empty_when_job_has_no_keywords() -> None:
    # No CV lookup or extraction should be needed when the job has no keywords.
    db = _FakeDb(cv=SimpleNamespace(content="Python"))
    posting = _posting([])

    assert crud_job._compute_skill_gap(db, USER_ID, posting) == ([], [])


def _detail_posting() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        title="Backend Engineer",
        company="Acme",
        location="Stockholm",
        salary_min=None,
        salary_max=None,
        employment_type=None,
        remote_allowed=True,
        is_remote=False,
        url="https://example.com/job",
        source="the_muse",
        scraped_at=None,
        application_deadline=None,
        description="Build things.",
    )


def test_job_to_dict_includes_already_tailored_ids_on_detail() -> None:
    cv_id = uuid.uuid4()
    cover_id = uuid.uuid4()

    data = crud_job._job_to_dict(
        _detail_posting(),
        None,
        include_description=True,
        tailored_cv_id=cv_id,
        cover_letter_job_id=cover_id,
    )

    assert data["tailored_cv_id"] == cv_id
    assert data["cover_letter_job_id"] == cover_id


def test_job_to_dict_omits_already_tailored_ids_in_list_mode() -> None:
    # The list path does not pass these and must not leak detail-only keys.
    data = crud_job._job_to_dict(_detail_posting(), None, include_description=False)

    assert "tailored_cv_id" not in data
    assert "cover_letter_job_id" not in data


def test_job_to_dict_is_saved_reflects_saved_job_not_job_description() -> None:
    posting = _detail_posting()

    unsaved = crud_job._job_to_dict(posting, None)
    assert unsaved["is_saved"] is False
    assert unsaved["saved_job_id"] is None

    saved_job = SimpleNamespace(id=uuid.uuid4())
    saved = crud_job._job_to_dict(posting, None, saved=saved_job)
    assert saved["is_saved"] is True
    assert saved["saved_job_id"] == saved_job.id


def test_is_live_deadline_clause_allows_null_or_future_deadline() -> None:
    clause = crud_job._is_live_deadline_clause()
    sql = str(clause.compile(compile_kwargs={"literal_binds": True}))

    assert "application_deadline IS NULL" in sql
    assert "application_deadline" in sql
