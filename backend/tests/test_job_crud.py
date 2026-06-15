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
