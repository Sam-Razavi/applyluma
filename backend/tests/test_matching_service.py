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
        # full coverage, but 3 of the 5 skills needed for full evidence
        assert result["skills_match"] == 80.0
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
        # coverage 2/4, evidence 2/5: 0.5 * (0.5 + 0.2) = 35
        assert result["skills_match"] == 35.0
        assert len(result["matched_skills"]) == 2
        assert len(result["missing_skills"]) == 2

    def test_no_required_skills_returns_neutral(self) -> None:
        svc = _make_service("Python")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": []},
        )
        assert result["skills_match"] == MatchingService.NO_SKILLS_SCORE == 30.0

    def test_job_skills_come_from_the_scored_vocabulary(self) -> None:
        # Soft skills and spoken languages are not scored; ordinary words that
        # happen to be tech names ("the rest of", "go the extra mile") are not skills.
        svc = _make_service("Python Django Docker")
        description = (
            "You will join the rest of the team and go the extra mile. We use Python, "
            "Django and Kubernetes. Strong communication and leadership. Svenska och engelska."
        )
        result = svc.calculate_match_score(uuid.uuid4(), uuid.uuid4(), {"description": description})
        assert set(result["matched_skills"]) == {"Python", "Django"}
        assert result["missing_skills"] == ["Kubernetes"]
        assert result["skills_match"] == pytest.approx(46.7)  # 2/3 coverage, 2/5 evidence

    def test_a_real_partial_match_outranks_a_job_with_no_skills(self) -> None:
        svc = _make_service("Python Django PostgreSQL Docker AWS")
        backend = svc.calculate_match_score(
            uuid.uuid4(), uuid.uuid4(),
            {"description": "Python, Django, PostgreSQL, Kubernetes and Terraform."},
        )
        vague = svc.calculate_match_score(
            uuid.uuid4(), uuid.uuid4(),
            {"description": "Partner with marketing and the rest of the revenue team."},
        )
        assert backend["skills_match"] == 48.0  # 3/5 coverage, 3/5 evidence
        assert vague["skills_match"] == MatchingService.NO_SKILLS_SCORE
        assert backend["overall_score"] > vague["overall_score"]

    def test_skills_case_insensitive(self) -> None:
        svc = _make_service("python POSTGRESQL docker")
        result = svc.calculate_match_score(
            uuid.uuid4(),
            uuid.uuid4(),
            {"required_skills": ["Python", "PostgreSQL", "Docker"]},
        )
        assert result["skills_match"] == 80.0


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
        # skills=60*0.40 (1/1 matched, 1/5 evidence) + experience=100*0.30
        # + salary=70*0.15 + education=100*0.10 (no requirement) + location=70*0.05 = 78.0
        assert result["overall_score"] == pytest.approx(78.0)

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


def test_cv_is_loaded_and_extracted_once_per_user() -> None:
    """A batch scores hundreds of jobs against the same CV; it must not be
    re-queried and re-extracted for every job."""
    svc = _make_service("Python PostgreSQL Docker")
    user_id = uuid.uuid4()
    calls: list[str] = []
    original = svc.extractor.extract_keywords

    def counting_extract(text: str):
        calls.append(text)
        return original(text)

    svc.extractor.extract_keywords = counting_extract  # type: ignore[method-assign]
    for _ in range(3):
        result = svc.calculate_match_score(
            user_id, uuid.uuid4(), {"required_skills": ["Python", "Docker"]}
        )
        assert result["matched_skills"] == ["Python", "Docker"]

    assert calls.count("Python PostgreSQL Docker") == 1
    assert svc.db.query.call_count == 1
