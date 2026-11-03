"""The keywords the job pipeline stores for each posting.

A curated subset of the skill vocabulary in app.services.keyword_extractor:
the same terms, categories and matching rules, but only the ~46 skills worth
showing on a job page. The full vocabulary is used for CVs, where a wide net
is wanted; on job ads it picks up noise ("Cloud", "Security", "API").
"""
from __future__ import annotations

from app.services.keyword_extractor import EXACT_CASE_ONLY, category_of, match_skill

__all__ = [
    "EXACT_CASE_ONLY",
    "PIPELINE_SKILLS",
    "SCORED_SKILL_TYPES",
    "SIMPLE_SKILLS",
    "extract_keywords_simple",
    "scored_skills",
]

PIPELINE_SKILLS: tuple[str, ...] = (
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes",
    "Linux", "AWS", "GCP", "Azure", "Machine Learning",
    "FastAPI", "Django", "Flask", "React", "Vue", "Angular", "NextJS",
    "Spring", "SpringBoot",
    "Git", "GitHub", "Jira", "Jenkins", "Terraform", "Ansible",
    "Leadership", "Communication", "Agile", "Scrum",
    "Swedish", "English", "Svenska", "Engelska",
    "AWS Solutions Architect", "CKA", "CKAD",
)

# (keyword, category), with the category taken from the shared vocabulary.
SIMPLE_SKILLS: list[tuple[str, str]] = [(name, category_of(name)) for name in PIPELINE_SKILLS]

# Keyword types that describe what a job technically requires. Soft skills and
# spoken languages are stored too, but CVs rarely state them in the same words
# (an English CV never says "Svenska"), so they are left out of scoring.
SCORED_SKILL_TYPES: frozenset[str] = frozenset(
    {"technical_skills", "frameworks", "tools", "certifications"}
)


def extract_keywords_simple(text: str) -> list[tuple[str, str, float, int]]:
    """(keyword, type, confidence, frequency) for each pipeline skill in *text*."""
    if not text:
        return []
    text_lower = text.lower()
    results = []
    for keyword, kw_type in SIMPLE_SKILLS:
        confidence, frequency = match_skill(keyword, text, text_lower)
        if frequency:
            results.append((keyword, kw_type, confidence, frequency))
    return results


def scored_skills(text: str) -> list[str]:
    """The skills a job is scored on: the keywords the pipeline stores for the
    job and the job page shows, minus soft skills and languages."""
    return [kw for kw, kw_type, _, _ in extract_keywords_simple(text) if kw_type in SCORED_SKILL_TYPES]
