"""Skill tagging for raw_job_postings.extracted_skills.

Ported from the scrape_jobs / scrape_swedish_jobs Airflow DAGs. Platsbanken
ads carry their own must-have / nice-to-have skill lists; every other source
is matched against TRACKED_SKILLS with word boundaries.
"""
from __future__ import annotations

import re
from typing import Any

TRACKED_SKILLS: list[str] = [
    "fastapi", "django", "flask",
    "react", "next.js", "vue", "angular",
    "typescript", "javascript", "python", "golang", "rust", "java", "kotlin",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "graphql", "rest api", "grpc",
    "celery", "airflow", "kafka", "rabbitmq",
    "machine learning", "llm", "openai", "langchain",
    "ci/cd", "github actions", "terraform",
]

_PATTERNS = [(skill, re.compile(r"\b" + re.escape(skill) + r"\b")) for skill in TRACKED_SKILLS]


def extract_tracked_skills(text: str) -> list[str]:
    text_lower = (text or "").lower()
    return [skill for skill, pattern in _PATTERNS if pattern.search(text_lower)]


def platsbanken_skills(raw_data: Any) -> list[str]:
    """Platsbanken's own skill labels, de-duplicated, in a stable order."""
    if not isinstance(raw_data, dict):
        return []
    labels = (raw_data.get("must_have_skills") or []) + (raw_data.get("nice_to_have_skills") or [])
    return sorted({label for label in labels if label})


def skills_for_posting(source: str, description: str, raw_data: Any) -> list[str]:
    if source == "platsbanken":
        labels = platsbanken_skills(raw_data)
        if labels:
            return labels
    return extract_tracked_skills(description)
