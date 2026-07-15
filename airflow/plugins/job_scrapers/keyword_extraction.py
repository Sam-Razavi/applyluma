"""Shared, boundary-safe keyword extraction for job posting text.

Stdlib-only (no Airflow imports) so it can be imported from the
extract_keywords DAG, from tests, and from scripts/backfill_keyword_false_positives.py
without an Airflow installation.

Matching uses lookaround guards instead of \\b so symbol-suffixed keywords
like "C++" and "C#" still match (a trailing \\b never matches after a
non-word character), while still avoiding substring false positives such as
"Go" inside "Google" or "SQL" inside "PostgreSQL".
"""
from __future__ import annotations

import re

# (keyword, category)
SIMPLE_SKILLS: list[tuple[str, str]] = [
    ("Python", "technical_skills"), ("JavaScript", "technical_skills"),
    ("TypeScript", "technical_skills"), ("Java", "technical_skills"),
    ("Go", "technical_skills"), ("Rust", "technical_skills"),
    ("C++", "technical_skills"), ("C#", "technical_skills"),
    ("SQL", "technical_skills"), ("PostgreSQL", "technical_skills"),
    ("MySQL", "technical_skills"), ("MongoDB", "technical_skills"),
    ("Redis", "technical_skills"), ("Docker", "technical_skills"),
    ("Kubernetes", "technical_skills"), ("Linux", "technical_skills"),
    ("AWS", "technical_skills"), ("GCP", "technical_skills"),
    ("Azure", "technical_skills"), ("Machine Learning", "technical_skills"),
    ("FastAPI", "frameworks"), ("Django", "frameworks"), ("Flask", "frameworks"),
    ("React", "frameworks"), ("Vue", "frameworks"), ("Angular", "frameworks"),
    ("NextJS", "frameworks"), ("Spring", "frameworks"), ("SpringBoot", "frameworks"),
    ("Git", "tools"), ("GitHub", "tools"), ("Jira", "tools"),
    ("Jenkins", "tools"), ("Terraform", "tools"), ("Ansible", "tools"),
    ("Leadership", "soft_skills"), ("Communication", "soft_skills"),
    ("Agile", "soft_skills"), ("Scrum", "soft_skills"),
    ("Swedish", "languages"), ("English", "languages"),
    ("Svenska", "languages"), ("Engelska", "languages"),
    ("AWS Solutions Architect", "certifications"),
    ("CKA", "certifications"), ("CKAD", "certifications"),
]


def _pattern_body(keyword: str, charclass: str) -> str:
    """Build the boundary-safe regex body for *keyword* using *charclass*.

    Single-word keywords (including symbol-suffixed ones like "C++"/"C#")
    use lookaround guards against surrounding word characters instead of
    \\b, since a trailing \\b never matches immediately after a non-word
    character. Multi-word keywords join their words with a flexible
    separator, matching the phrase-handling used in
    backend/app/services/keyword_extractor.py.
    """
    words = keyword.split()
    if len(words) > 1:
        body = r"[\s\-/]+".join(re.escape(w) for w in words)
    else:
        body = re.escape(keyword)
    return rf"(?<![{charclass}])" + body + rf"(?![{charclass}])"


# Case-insensitive pattern (built from the lowercased keyword), matched
# against the lowercased text — used for both detection and frequency.
_LOWER_PATTERNS: dict[str, re.Pattern[str]] = {
    keyword: re.compile(_pattern_body(keyword.lower(), "a-z0-9"))
    for keyword, _ in SIMPLE_SKILLS
}

# Case-sensitive pattern (built from the keyword's original case), matched
# against the original text — used only to decide confidence.
_EXACT_CASE_PATTERNS: dict[str, re.Pattern[str]] = {
    keyword: re.compile(_pattern_body(keyword, "A-Za-z0-9"))
    for keyword, _ in SIMPLE_SKILLS
}


def extract_keywords_simple(text: str) -> list[tuple[str, str, float, int]]:
    """Return list of (keyword, type, confidence, frequency) for *text*.

    frequency is the number of boundary-safe regex matches in the lowered
    text. confidence is 1.0 when the keyword's exact case appears in the
    original text, else 0.6.
    """
    if not text:
        return []

    text_lower = text.lower()
    results = []
    for keyword, kw_type in SIMPLE_SKILLS:
        matches = _LOWER_PATTERNS[keyword].findall(text_lower)
        if not matches:
            continue
        freq = len(matches)
        confidence = 1.0 if _EXACT_CASE_PATTERNS[keyword].search(text) else 0.6
        results.append((keyword, kw_type, confidence, freq))
    return results
