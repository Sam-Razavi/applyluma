"""Regression tests for CV tailoring bugs: concatenation, duplicate headers,
dropped data, and fabricated skills — updated for the structured CV contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pdfplumber
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.models.tailor_job import TailorIntensity
from app.services import tailor_service
from app.services.cv_render import structured_to_sections
from app.services.pdf_generator import generate_cv_pdf
from app.services.tailor_service import (
    _extract_contact_information,
    _is_contact_section,
    _remove_fabricated_skills,
    _skill_present_in_source,
    _source_skill_slugs,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "source_cv.json"
SWEDISH_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "source_cv_swedish.json"


@pytest.fixture()
def source_cv() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def cv_text(source_cv: dict) -> str:
    return source_cv["cv_text"]


def make_structured(**overrides: Any) -> dict:
    payload: dict[str, Any] = {
        "language": "en",
        "header": {
            "full_name": "Sam Developer",
            "target_headline": "Fullstack Developer | Python & React",
            "location": "Stockholm, Sweden",
            "phone": "+46 70 123 4567",
            "email": "sam@example.com",
            "links": ["github.com/samdev"],
        },
        "summary": {
            "tailored": "Results-driven fullstack developer with strong Python and React skills.",
            "original": "Fullstack developer with experience in Python, React, and TypeScript.",
            "changes": ["Rewrote summary"],
        },
        "skills": {
            "groups": [
                {"category": "Languages", "items": ["Python", "JavaScript", "TypeScript"]},
                {"category": "Frontend", "items": ["React"]},
            ],
            "original": "Python, JavaScript, TypeScript, React",
            "changes": [],
        },
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": {"items": [], "original": "", "changes": []},
        "additional_sections": [],
        "section_order": ["summary", "skills", "experience", "projects", "education"],
        "meta": {
            "keywords_added": [],
            "keywords_already_present": [],
            "intensity_applied": "medium",
            "estimated_pages": 1,
        },
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Bug #1: Concatenation — tailored output must not duplicate source content
# ---------------------------------------------------------------------------


class TestNoConcatenation:
    def test_derived_section_text_comes_only_from_typed_fields(self) -> None:
        structured = make_structured()
        sections = structured_to_sections(structured, contact_text="")
        summary = next(s for s in sections if s["section_id"] == "summary")
        # The tailored text is exactly the typed field — the schema makes it
        # impossible for the model to prepend the original text to it.
        assert summary["tailored"] == structured["summary"]["tailored"]
        assert summary["original"] not in summary["tailored"]

    def test_pdf_contains_content_once(self, tmp_path: Path) -> None:
        sections = [
            {"section_name": "Summary", "content": "Expert Python developer."},
            {"section_name": "Skills", "content": "Python, React, TypeScript"},
        ]
        out = tmp_path / "test.pdf"
        generate_cv_pdf(sections, out)

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        assert text.count("Expert Python developer") == 1


# ---------------------------------------------------------------------------
# Bug #2: Duplicate section headers
# ---------------------------------------------------------------------------


class TestNoDuplicateHeaders:
    def test_pdf_emits_each_heading_once(self, tmp_path: Path) -> None:
        sections = [
            {"section_name": "Experience", "content": "Job 1 at Company A"},
            {"section_name": "Experience", "content": "Job 2 at Company B"},
        ]
        out = tmp_path / "test.pdf"
        generate_cv_pdf(sections, out)

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        assert text.count("Experience") == 1
        assert "Job 1 at Company A" in text
        assert "Job 2 at Company B" in text

    def test_different_headings_both_appear(self, tmp_path: Path) -> None:
        sections = [
            {"section_name": "Experience", "content": "Job 1"},
            {"section_name": "Projects", "content": "Project 1"},
        ]
        out = tmp_path / "test.pdf"
        generate_cv_pdf(sections, out)

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        assert "Experience" in text
        assert "Projects" in text


# ---------------------------------------------------------------------------
# Bug #3: Dropped data — contact, projects, education must survive tailoring
# ---------------------------------------------------------------------------


class TestNoDroppedData:
    def test_contact_info_extracted_from_source(self, cv_text: str) -> None:
        contact = _extract_contact_information(cv_text)
        assert "Sam Developer" in contact
        assert "sam@example.com" in contact
        assert "+46 70 123 4567" in contact
        assert "samcodes.com" in contact
        assert "github.com/samdev" in contact
        assert "linkedin.com/in/samdev" in contact

    def test_contact_section_always_injected_first(self, cv_text: str) -> None:
        contact = _extract_contact_information(cv_text)
        sections = structured_to_sections(make_structured(), contact_text=contact)
        assert sections[0]["section_id"] == "contact_information"
        assert sections[0]["original"] == sections[0]["tailored"]
        assert "Sam Developer" in sections[0]["tailored"]
        assert "sam@example.com" in sections[0]["tailored"]

    def test_all_projects_present_in_derived_sections(self, source_cv: dict) -> None:
        structured = make_structured(
            projects=[
                {
                    "name": name,
                    "subtitle": None,
                    "url": None,
                    "stack": [],
                    "bullets": [f"Built {name}."],
                    "original": name,
                    "changes": [],
                }
                for name in source_cv["projects"]
            ]
        )
        sections = structured_to_sections(structured, contact_text="")
        text = "\n".join(s["tailored"] for s in sections)
        for project in source_cv["projects"]:
            assert project in text, f"Project '{project}' missing from derived sections"

    def test_education_details_preserved_in_pdf(self, tmp_path: Path) -> None:
        sections = [
            {
                "section_name": "Education",
                "content": (
                    "BSc Computer Science\n"
                    "University of Gothenburg\n"
                    "2021 - 2024\n"
                    "Thesis: Machine Learning Approaches to Resume Parsing\n"
                    "180 credits\n\n"
                    "MSc Software Engineering\n"
                    "Chalmers University of Technology\n"
                    "2024 - 2026\n"
                    "Thesis: Automated CV Tailoring with Large Language Models\n"
                    "120 credits"
                ),
            }
        ]
        out = tmp_path / "test.pdf"
        generate_cv_pdf(sections, out)

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        assert "Machine Learning Approaches to Resume Parsing" in text
        assert "Automated CV Tailoring with Large Language Models" in text
        assert "180 credits" in text
        assert "120 credits" in text


# ---------------------------------------------------------------------------
# Bug #4: Fabricated content — no skill not in source may appear in output
# ---------------------------------------------------------------------------


class TestNoFabrication:
    def test_java_not_matched_inside_javascript(self, cv_text: str) -> None:
        slugs = _source_skill_slugs(cv_text)
        assert not _skill_present_in_source("Java", cv_text.lower(), slugs)
        assert _skill_present_in_source("JavaScript", cv_text.lower(), slugs)

    def test_punctuation_variants_are_tolerated(self) -> None:
        source = "Skills: Node.js, CI/CD pipelines, React"
        slugs = _source_skill_slugs(source)
        assert _skill_present_in_source("Node js", source.lower(), slugs)
        assert _skill_present_in_source("CI CD", source.lower(), slugs)

    def test_aggressive_intensity_does_not_encourage_fabrication(self) -> None:
        from app.services.tailor_service import _INTENSITY_INSTRUCTIONS, _SYSTEM_PROMPT

        aggressive = _INTENSITY_INSTRUCTIONS[TailorIntensity.aggressive].lower()
        # The old wording pushed keyword stuffing and invented metrics.
        assert "maximum keyword match" not in aggressive
        assert "quantified impact" not in aggressive
        # Aggressive must explicitly forbid inventing facts/numbers and stay on real content.
        assert "never" in aggressive
        assert "real" in aggressive or "actual" in aggressive
        # The system prompt states truthfulness overrides the intensity setting.
        assert "override" in _SYSTEM_PROMPT.lower()

    def test_removes_fabricated_skills_from_groups(self, cv_text: str) -> None:
        structured = make_structured(
            skills={
                "groups": [
                    {
                        "category": "Languages",
                        "items": ["Python", "JavaScript", "TypeScript", "Java"],
                    },
                    {"category": "Cloud", "items": ["Azure DevOps"]},
                ],
                "original": "Python, JavaScript, TypeScript, React",
                "changes": [],
            }
        )
        removed = _remove_fabricated_skills(structured, cv_text)
        assert "Java" in removed
        assert "Azure DevOps" in removed
        groups = structured["skills"]["groups"]
        # The now-empty Cloud group is dropped entirely.
        assert [g["category"] for g in groups] == ["Languages"]
        assert groups[0]["items"] == ["Python", "JavaScript", "TypeScript"]

    def test_removes_fabricated_stack_items_from_projects(self, cv_text: str) -> None:
        structured = make_structured(
            projects=[
                {
                    "name": "Memory Game",
                    "subtitle": None,
                    "url": None,
                    "stack": ["JavaScript", "Kubernetes"],
                    "bullets": ["Built a browser game."],
                    "original": "Memory Game",
                    "changes": [],
                }
            ]
        )
        removed = _remove_fabricated_skills(structured, cv_text)
        assert "Kubernetes" in removed
        assert structured["projects"][0]["stack"] == ["JavaScript"]

    def test_no_false_positives_for_existing_skills(self, cv_text: str) -> None:
        structured = make_structured(
            skills={
                "groups": [
                    {
                        "category": "Stack",
                        "items": ["Python", "React", "TypeScript", "FastAPI", "Docker"],
                    }
                ],
                "original": "Python, React, TypeScript",
                "changes": [],
            }
        )
        removed = _remove_fabricated_skills(structured, cv_text)
        assert removed == []

    def test_fabrication_check_integrated_in_tailor_cv(
        self, monkeypatch: pytest.MonkeyPatch, cv_text: str
    ) -> None:
        fabricated_response = json.dumps(
            make_structured(
                skills={
                    "groups": [
                        {
                            "category": "Languages",
                            "items": ["Python", "React", "Java", "Azure DevOps"],
                        }
                    ],
                    "original": "Python, React",
                    "changes": [],
                }
            )
        )

        class FakeOpenAI:
            def __init__(self, api_key: str, timeout: float | None = None) -> None:
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(create=self._create),
                )

            def _create(self, **kwargs: Any) -> SimpleNamespace:
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            finish_reason="stop",
                            message=SimpleNamespace(content=fabricated_response, refusal=None),
                        )
                    ]
                )

        monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
        monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
        monkeypatch.setattr(tailor_service, "detect", lambda text: "en")

        result = tailor_service.tailor_cv(
            cv_content=cv_text,
            jd_description="Need Java and Azure DevOps expertise",
            jd_keywords=["Java", "Azure DevOps"],
            intensity=TailorIntensity.medium,
        )

        for section in result["sections"]:
            if section["section_id"] == "skills":
                assert "Java" not in section["tailored"]
                assert "Azure DevOps" not in section["tailored"]
                assert "Python" in section["tailored"]
        items = result["structured_cv"]["skills"]["groups"][0]["items"]
        assert "Java" not in items
        assert "Azure DevOps" not in items


# ---------------------------------------------------------------------------
# Structured section text derivation
# ---------------------------------------------------------------------------


class TestDerivedSectionText:
    def test_experience_entry_text_format(self) -> None:
        structured = make_structured(
            experience=[
                {
                    "title": "Fullstack Developer Intern",
                    "company": "Tech Corp",
                    "location": "Stockholm",
                    "dates": "June 2025 - Present",
                    "bullets": ["Built REST APIs using FastAPI and PostgreSQL"],
                    "original": "Fullstack Developer Intern at Tech Corp",
                    "changes": [],
                }
            ]
        )
        sections = structured_to_sections(structured, contact_text="")
        exp = next(s for s in sections if s["section_id"] == "experience_0")
        assert "Fullstack Developer Intern - Tech Corp" in exp["tailored"]
        assert "June 2025 - Present | Stockholm" in exp["tailored"]
        assert "• Built REST APIs using FastAPI and PostgreSQL" in exp["tailored"]

    def test_project_entry_text_includes_url_and_stack(self) -> None:
        structured = make_structured(
            projects=[
                {
                    "name": "ApplyLuma",
                    "subtitle": "AI-powered job application platform",
                    "url": "github.com/samdev/applyluma",
                    "stack": ["FastAPI", "React"],
                    "bullets": ["Shipped end-to-end job tracking."],
                    "original": "ApplyLuma",
                    "changes": [],
                }
            ]
        )
        sections = structured_to_sections(structured, contact_text="")
        proj = next(s for s in sections if s["section_id"] == "project_0")
        assert "ApplyLuma - AI-powered job application platform" in proj["tailored"]
        assert "github.com/samdev/applyluma" in proj["tailored"]
        assert "Tech: FastAPI, React" in proj["tailored"]

    def test_swedish_language_uses_swedish_headings(self) -> None:
        structured = make_structured(language="sv")
        sections = structured_to_sections(structured, contact_text="Sam\nsam@example.com")
        names = {s["section_id"]: s["section_name"] for s in sections}
        assert names["contact_information"] == "Kontaktuppgifter"
        assert names["summary"] == "Sammanfattning"
        assert names["skills"] == "Kompetenser"


# ---------------------------------------------------------------------------
# Round 2: Swedish contact section matching
# ---------------------------------------------------------------------------


class TestSwedishContactMatching:
    @pytest.mark.parametrize(
        "section_name",
        ["Kontaktuppgifter", "Personuppgifter", "Kontaktinformation", "Header", "Personal Details"],
    )
    def test_is_contact_section_matches(self, section_name: str) -> None:
        section = {"section_id": "contact_info", "section_name": section_name}
        assert _is_contact_section(section)

    def test_non_contact_section_not_matched(self) -> None:
        section = {"section_id": "skills", "section_name": "Kompetenser"}
        assert not _is_contact_section(section)


# ---------------------------------------------------------------------------
# Round 2: Swedish stop headings in contact extraction
# ---------------------------------------------------------------------------


class TestSwedishStopHeadings:
    def test_contact_extraction_stops_at_sammanfattning(self) -> None:
        cv_text = (
            "Sam Utvecklare\nsam@example.com\n+46 70 123 4567\n"
            "Stockholm, Sverige\n\n"
            "Sammanfattning\nFullstackutvecklare med erfarenhet av Python."
        )
        contact = _extract_contact_information(cv_text)
        assert "Sam Utvecklare" in contact
        assert "sam@example.com" in contact
        assert "Sammanfattning" not in contact
        assert "Fullstackutvecklare" not in contact

    def test_contact_extraction_stops_at_kompetenser(self) -> None:
        cv_text = (
            "Sam Utvecklare\nsam@example.com\n+46 70 123 4567\n"
            "Kompetenser\nPython, JavaScript, TypeScript"
        )
        contact = _extract_contact_information(cv_text)
        assert "sam@example.com" in contact
        assert "Kompetenser" not in contact
        assert "Python" not in contact

    def test_swedish_cv_contact_extraction_full(self) -> None:
        fixture = json.loads(SWEDISH_FIXTURE_PATH.read_text(encoding="utf-8"))
        contact = _extract_contact_information(fixture["cv_text"])
        assert "Sam Utvecklare" in contact
        assert "sam@example.com" in contact
        assert "+46 70 123 4567" in contact
        assert "github.com/samdev" in contact
        assert "Sammanfattning" not in contact
        assert "Kompetenser" not in contact


# ---------------------------------------------------------------------------
# Round 2: CID artifact and over-extraction safeguards
# ---------------------------------------------------------------------------


class TestContactExtractionSafeguards:
    def test_cid_artifacts_stripped_before_extraction(self) -> None:
        cv_text = (
            "Sam Developer\n"
            "sam@example.com\n"
            "+46 70 123 4567\n\n"
            "(cid:127) Built REST APIs using FastAPI\n"
            "(cid:127) Developed React components"
        )
        contact = _extract_contact_information(cv_text)
        assert "Sam Developer" in contact
        assert "sam@example.com" in contact
        assert "+46 70 123 4567" in contact
        assert "(cid:" not in contact
        assert "Built REST APIs" not in contact

    def test_max_lines_prevents_over_extraction(self) -> None:
        lines = ["Sam Developer", "sam@example.com", "+46 70 123 4567"]
        lines += [f"Extra line {i}" for i in range(20)]
        cv_text = "\n".join(lines)
        contact = _extract_contact_information(cv_text)
        assert contact != ""
        assert contact.count("\n") < 12

    def test_no_blank_lines_still_limited(self) -> None:
        cv_text = (
            "Sam Developer\nsam@example.com\n+46 70 123 4567\n"
            "Stockholm\ngithub.com/samdev\nlinkedin.com/in/samdev\n"
            "Line 7\nLine 8\nLine 9\nLine 10\nLine 11\nLine 12\n"
            "Line 13\nLine 14\nLine 15\nLine 16\nLine 17\nLine 18"
        )
        contact = _extract_contact_information(cv_text)
        assert "Line 13" not in contact
        assert "Line 18" not in contact
