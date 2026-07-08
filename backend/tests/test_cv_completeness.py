"""Unit tests for the deterministic CV completeness scorer."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.cv_completeness import score_cv_content

FILLER = "Built and maintained services. " * 40  # pushes past the length check

COMPLETE_EN_CV = f"""Jane Doe
jane.doe@example.com | +46 70 123 45 67
linkedin.com/in/janedoe

## Summary
Backend engineer with 8 years of experience.

## Experience
Senior Engineer, Acme — 2019–present
Engineer, DataCo — 2015–2019
{FILLER}

## Education
MSc Computer Science, KTH

## Skills
Python, FastAPI, PostgreSQL, Docker
"""

SWEDISH_CV = f"""Sven Svensson
sven@example.se
0701234567

Profil
Systemutvecklare med bred erfarenhet.

Arbetslivserfarenhet
Utvecklare, Bolaget AB, 2018–nuvarande
Konsult, Firman AB, 2014–2018
{FILLER}

Utbildning
Civilingenjör, Chalmers

Kompetenser
Python, SQL, Linux
https://github.com/svensson
"""


def _by_id(result: dict) -> dict[str, dict]:
    return {c["id"]: c for c in result["checks"]}


def test_complete_english_cv_scores_100() -> None:
    result = score_cv_content(COMPLETE_EN_CV)
    assert result["score"] == 100
    assert all(c["passed"] for c in result["checks"])


def test_swedish_headings_are_recognised() -> None:
    checks = _by_id(score_cv_content(SWEDISH_CV))
    for check_id in ("summary", "experience", "education", "skills", "contact_info", "links"):
        assert checks[check_id]["passed"], check_id


def test_empty_content_scores_zero() -> None:
    for content in (None, "", "   "):
        result = score_cv_content(content)
        assert result["score"] == 0
        assert not any(c["passed"] for c in result["checks"])


def test_missing_links_and_summary_fail_only_those_checks() -> None:
    cv = COMPLETE_EN_CV.replace("linkedin.com/in/janedoe", "").replace("## Summary", "## Intro-x")
    checks = _by_id(score_cv_content(cv))
    assert not checks["links"]["passed"]
    assert not checks["summary"]["passed"]
    for check_id in ("contact_info", "experience", "education", "skills", "length"):
        assert checks[check_id]["passed"], check_id


def test_short_cv_fails_length_check() -> None:
    short = "Jane Doe\njane@example.com\n## Skills\nPython"
    checks = _by_id(score_cv_content(short))
    assert not checks["length"]["passed"]
    assert checks["contact_info"]["passed"]
    assert checks["skills"]["passed"]


def test_experience_detected_from_year_ranges_without_heading() -> None:
    cv = f"Worked at Acme 2019–2022 and DataCo 2015–2019. {FILLER}"
    checks = _by_id(score_cv_content(cv))
    assert checks["experience"]["passed"]


def test_body_text_mentioning_keywords_is_not_a_heading() -> None:
    # "education" inside a long sentence must not satisfy the heading check
    cv = (
        "I have always valued education and my professional experience shows it, "
        "which is a long line well beyond the heading length limit for detection."
    )
    checks = _by_id(score_cv_content(cv))
    assert not checks["education"]["passed"]
