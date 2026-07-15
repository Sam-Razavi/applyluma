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
