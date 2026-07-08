"""Deterministic CV completeness scoring.

Scores the parsed plain text of a CV against a checklist (contact info,
summary, experience, education, skills, links, length). Each check maps to an
actionable hint so users know what to improve before tailoring. Headings are
matched in English and Swedish, and work both for markdown-style content
("## Experience") and bare headings from PDF extraction.
"""
from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<!\d)[+(]?\d[\d\s()\-]{7,}\d")
_URL_RE = re.compile(r"(https?://\S+|linkedin\.com/\S+|github\.com/\S+)", re.IGNORECASE)
_YEAR_RANGE_RE = re.compile(
    r"20\d{2}\s*[-–—]\s*(20\d{2}|present|now|ongoing|pågående|nuvarande|nu)",
    re.IGNORECASE,
)

_MAX_HEADING_LENGTH = 48

_SUMMARY_TERMS = ("summary", "profile", "objective", "about me", "sammanfattning", "profil", "om mig")
_EXPERIENCE_TERMS = (
    "experience", "employment", "work history", "career",
    "erfarenhet", "arbetslivserfarenhet", "anställningar",
)
_EDUCATION_TERMS = ("education", "academic", "utbildning", "studier")
_SKILLS_TERMS = (
    "skills", "competencies", "technologies", "tech stack",
    "kompetenser", "färdigheter", "tekniker",
)

_MIN_WORDS = 150


def _headings(content: str) -> list[str]:
    """Short standalone lines that plausibly act as section headings."""
    headings: list[str] = []
    for line in content.splitlines():
        stripped = line.strip().removeprefix("## ").strip()
        if stripped and len(stripped) <= _MAX_HEADING_LENGTH:
            headings.append(stripped.lower())
    return headings


def _has_heading(headings: list[str], terms: tuple[str, ...]) -> bool:
    return any(term in heading for heading in headings for term in terms)


def score_cv_content(content: str | None) -> dict[str, Any]:
    """Return {"score": 0-100, "checks": [{id, label, passed, hint}]}."""
    text = (content or "").strip()
    headings = _headings(text) if text else []

    results: list[tuple[str, str, bool, str]] = [
        (
            "contact_info",
            "Contact information",
            bool(_EMAIL_RE.search(text) or _PHONE_RE.search(text)),
            "Add an email address or phone number so recruiters can reach you.",
        ),
        (
            "summary",
            "Summary or profile",
            _has_heading(headings, _SUMMARY_TERMS),
            "Open with a short summary or profile section that pitches who you are.",
        ),
        (
            "experience",
            "Work experience",
            _has_heading(headings, _EXPERIENCE_TERMS) or len(_YEAR_RANGE_RE.findall(text)) >= 2,
            "Add a work experience section with roles and date ranges.",
        ),
        (
            "education",
            "Education",
            _has_heading(headings, _EDUCATION_TERMS),
            "Add an education section with your degrees or courses.",
        ),
        (
            "skills",
            "Skills",
            _has_heading(headings, _SKILLS_TERMS),
            "List your key skills in a dedicated skills section — it drives keyword matching.",
        ),
        (
            "links",
            "Links",
            bool(_URL_RE.search(text)),
            "Include a LinkedIn, GitHub, or portfolio link.",
        ),
        (
            "length",
            "Enough detail",
            len(text.split()) >= _MIN_WORDS,
            f"Your CV looks thin — aim for at least {_MIN_WORDS} words of relevant detail.",
        ),
    ]

    checks = [
        {"id": check_id, "label": label, "passed": passed, "hint": hint}
        for check_id, label, passed, hint in results
    ]
    passed_count = sum(1 for c in checks if c["passed"])
    return {"score": round(passed_count / len(checks) * 100), "checks": checks}
