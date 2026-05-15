"""Unit tests for MatchingService scoring algorithm."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.matching_service import MatchingService


def _make_service(cv_content: str = "") -> MatchingService:
    """Return a MatchingService backed by a stub DB that returns a fake CV."""
    fake_cv = SimpleNamespace(
        content=cv_content,
        is_default=True,
    )
    db = MagicMock()
    # calculate_match_score does: db.query(CV).filter(...).first()
    db.query.return_value.filter.return_value.first.return_value = fake_cv
    return MatchingService(db)


class TestSkillScoring:
    def test_all_skills_matched(self) -> None:
        svc = _make_service("Python PostgreSQL Docker")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "PostgreSQL", "Docker"]},
        )
        assert result["skills_match"] == 100.0
        assert set(result["matched_skills"]) == {"Python", "PostgreSQL", "Docker"}
        assert result["missing_skills"] == []

    def test_no_skills_matched(self) -> None:
        svc = _make_service("Word Excel PowerPoint")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "PostgreSQL", "Docker"]},
        )
        assert result["skills_match"] == 0.0
        assert result["missing_skills"] == ["Python", "PostgreSQL", "Docker"]

    def test_partial_skills_match(self) -> None:
        svc = _make_service("Python PostgreSQL communication skills")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "PostgreSQL", "Docker", "Kubernetes"]},
        )
        # 2/4 = 50%
        assert result["skills_match"] == 50.0
        assert len(result["matched_skills"]) == 2
        assert len(result["missing_skills"]) == 2

    def test_no_required_skills_returns_neutral(self) -> None:
        svc = _make_service("Python")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": []},
        )
        assert result["skills_match"] == 70.0

    def test_skills_case_insensitive(self) -> None:
        svc = _make_service("python POSTGRESQL docker")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "PostgreSQL", "Docker"]},
        )
        assert result["skills_match"] == 100.0


class TestExperienceScoring:
    def test_exact_years_match(self) -> None:
        svc = _make_service("I have 5 years of experience in software development.")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_experience_years": 5},
        )
        assert result["experience_match"] == 100.0

    def test_exceeds_required_years(self) -> None:
        svc = _make_service("8 years of experience in software development.")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_experience_years": 5},
        )
        assert result["experience_match"] == 100.0

    def test_below_required_years(self) -> None:
        svc = _make_service("2 years of professional experience.")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_experience_years": 10},
        )
        assert result["experience_match"] == pytest.approx(20.0)

    def test_zero_required_years(self) -> None:
        svc = _make_service("Recent graduate")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_experience_years": 0},
        )
        assert result["experience_match"] == 100.0

    def test_no_years_in_cv(self) -> None:
        svc = _make_service("Skilled developer")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_experience_years": 5},
        )
        # user_yoe=0, required=5 → 0/5 * 100 = 0
        assert result["experience_match"] == 0.0


class TestWeightedScore:
    def test_weighted_average_formula(self) -> None:
        svc = _make_service("Python 5 years of experience Bachelor degree")
        job_data = {
            "required_skills": ["Python"],
            "required_experience_years": 5,
        }
        result = svc.calculate_match_score(uuid.uuid4(), uuid.uuid4(), job_data)
        # skills=100*0.40 + experience=100*0.30 + salary=70*0.15
        # + education=100*0.10 (no education req → 100) + location=70*0.05 = 94.0
        assert result["overall_score"] == pytest.approx(94.0)

    def test_score_is_0_to_100(self) -> None:
        svc = _make_service("")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "Go", "Rust"], "required_experience_years": 20},
        )
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_all_required_fields_present(self) -> None:
        svc = _make_service("Python developer with 3 years experience.")
        result = svc.calculate_match_score(uuid.uuid4(), uuid.uuid4(), {})
        required_keys = {
            "overall_score", "skills_match", "experience_match", "salary_match",
            "education_match", "location_match", "explanation",
            "matched_skills", "missing_skills",
        }
        assert required_keys.issubset(result.keys())


class TestExplanation:
    def test_explanation_includes_skill_counts(self) -> None:
        svc = _make_service("Python PostgreSQL skills")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "PostgreSQL", "Docker"]},
        )
        assert "2/3" in result["explanation"]

    def test_explanation_includes_experience(self) -> None:
        svc = _make_service("I have 8 years of experience.")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_experience_years": 5},
        )
        assert "8" in result["explanation"]
        assert "5" in result["explanation"]

    def test_explanation_includes_salary(self) -> None:
        svc = _make_service("")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"salary_min": 80000, "salary_max": 120000},
        )
        assert "80,000" in result["explanation"]
        assert "120,000" in result["explanation"]

    def test_explanation_includes_location(self) -> None:
        svc = _make_service("")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"location": "Stockholm", "remote_allowed": True},
        )
        assert "Stockholm" in result["explanation"]
        assert "remote OK" in result["explanation"]

    def test_fallback_explanation_when_no_data(self) -> None:
        svc = _make_service("")
        result = svc.calculate_match_score(uuid.uuid4(), uuid.uuid4(), {})
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 0


class TestYearsEstimation:
    def test_detect_years_pattern(self) -> None:
        svc = _make_service("")
        assert svc._estimate_years_experience("10 years of experience in software") == 10

    def test_detect_years_plus_pattern(self) -> None:
        svc = _make_service("")
        assert svc._estimate_years_experience("5+ years professional experience") == 5

    def test_swedish_years_pattern(self) -> None:
        svc = _make_service("")
        assert svc._estimate_years_experience("7 år erfarenhet inom IT") == 7

    def test_no_years_returns_zero(self) -> None:
        svc = _make_service("")
        assert svc._estimate_years_experience("Experienced developer") == 0

    def test_empty_text_returns_zero(self) -> None:
        svc = _make_service("")
        assert svc._estimate_years_experience("") == 0


class TestNoCV:
    def test_no_cv_produces_valid_score(self) -> None:
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        svc = MatchingService(db)
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python"]},
        )
        assert 0.0 <= result["overall_score"] <= 100.0
        assert isinstance(result["explanation"], str)
