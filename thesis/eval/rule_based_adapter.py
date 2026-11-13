"""The rule-based matcher on a case, unchanged.

In production the matcher reads the user's default CV and the posting from the
database. A case has neither, so this module hands `MatchingService` the CV text
through a stand-in for the one query it makes and builds `job_data` with the same
keys `MatchingService.batch_compute_scores` uses. A case has no separate location,
so the explanation line lacks the "Location: ..." ending a posting would get; no
score depends on it. No scoring logic lives here;
`backend/tests/test_thesis_eval.py` checks the result against the production path
on a real database.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from app.services.matching_service import MatchingService

_USER = uuid.UUID(int=1)
_JOB = uuid.UUID(int=2)


class _DefaultCvOnly:
    """Answers `query(CV).filter(...).first()` with the case's CV."""

    def __init__(self, cv_text: str) -> None:
        self._cv = SimpleNamespace(content=cv_text)

    def query(self, *_: Any) -> _DefaultCvOnly:
        return self

    def filter(self, *_: Any) -> _DefaultCvOnly:
        return self

    def first(self) -> SimpleNamespace:
        return self._cv


def job_data(ad_text: str, *, remote: bool = False) -> dict[str, Any]:
    """The keys `batch_compute_scores` passes; a case has only the ad text."""
    return {
        "description": ad_text,
        "title": None,
        "salary_min": None,
        "salary_max": None,
        "location": None,
        "remote_allowed": remote,
    }


def score(cv_text: str, ad_text: str, *, remote: bool = False) -> dict[str, Any]:
    service = MatchingService(_DefaultCvOnly(cv_text))  # type: ignore[arg-type]
    return service.calculate_match_score(_USER, _JOB, job_data(ad_text, remote=remote))


def priority(overall_score: float, thresholds: dict[str, float]) -> str:
    if overall_score >= thresholds["high_priority_min"]:
        return "high_priority"
    if overall_score >= thresholds["consider_min"]:
        return "consider"
    return "low_priority"
