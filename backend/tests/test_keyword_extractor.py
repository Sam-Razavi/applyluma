"""Tests for KeywordExtractor word-boundary matching, including the
symbol-suffixed keyword fix (C++/C# were unmatchable with plain \\b)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.keyword_extractor import KeywordExtractor


def _extractor() -> KeywordExtractor:
    return KeywordExtractor(enable_nlp=False)


def test_cpp_and_csharp_are_extracted() -> None:
    result = _extractor().extract_keywords("5 years of C++ and C# development")
    flat = {item["keyword"] for items in result.values() for item in items}
    assert "C++" in flat
    assert "C#" in flat


def test_react_does_not_match_reactive() -> None:
    result = _extractor().extract_keywords("Reactive programming experience")
    flat = {item["keyword"] for items in result.values() for item in items}
    assert "React" not in flat


def test_apache_kafka_requires_adjacent_phrase() -> None:
    ext = _extractor()
    assert ext._confidence_score("Apache Kafka", "We use Apache tools and separately Kafka queues") == 0.0
    assert ext._confidence_score("Apache Kafka", "We use Apache Kafka for streaming") == 1.0


def test_cpp_confidence_case_sensitive_and_insensitive() -> None:
    ext = _extractor()
    assert ext._confidence_score("C++", "Expert in C++ development") == 1.0
    assert ext._confidence_score("C#", "Solid c# background") == 0.6


def test_everyday_words_are_not_skills_in_any_text() -> None:
    """One matching rule for CVs, job descriptions and pipeline keywords:
    skill names that are also ordinary words count only when capitalised."""
    ext = KeywordExtractor(enable_nlp=False)
    prose = (
        "Collaborate with engineering teams, express interest early, support "
        "the rest of the team, go the extra mile, start spring 2027, linear channels."
    )
    found = {i["keyword"] for items in ext.extract_keywords(prose).values() for i in items}
    assert not found & {"Teams", "Express", "REST", "Go", "Spring", "Linear"}

    skills = "Microsoft Teams, Express and REST APIs in Go, Spring Boot services."
    found = {i["keyword"] for items in ext.extract_keywords(skills).values() for i in items}
    assert {"Teams", "Express", "REST", "Go", "Spring"} <= found


def test_frequency_counts_whole_words_only() -> None:
    ext = KeywordExtractor(enable_nlp=False)
    tools = ext.extract_keywords("Go and Google, Go again")["technical_skills"]
    go = next(i for i in tools if i["keyword"] == "Go")
    assert go["frequency"] == 2  # not the "Go" inside "Google"


def test_pipeline_keywords_are_a_subset_of_the_shared_vocabulary() -> None:
    from app.services.job_scrapers.keyword_extraction import SIMPLE_SKILLS
    from app.services.keyword_extractor import category_of

    assert SIMPLE_SKILLS, "pipeline vocabulary is empty"
    for keyword, kw_type in SIMPLE_SKILLS:
        assert category_of(keyword) == kw_type
    assert dict(SIMPLE_SKILLS)["Terraform"] == "tools"
