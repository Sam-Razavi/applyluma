"""Regression tests for CV tailoring bugs: concatenation, duplicate headers,
dropped data, and fabricated skills."""

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
from app.services.pdf_generator import generate_cv_pdf
from app.services.tailor_service import (
    _extract_contact_information,
    _is_contact_section,
    _remove_fabricated_skills,
    _strip_concatenated_originals,
    _validate_no_fabricated_skills,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "source_cv.json"
SWEDISH_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "source_cv_swedish.json"


@pytest.fixture()
def source_cv() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def cv_text(source_cv: dict) -> str:
    return source_cv["cv_text"]


# ---------------------------------------------------------------------------
# Bug #1: Concatenation — tailored output must not duplicate source content
# ---------------------------------------------------------------------------


class TestNoConcatenation:
    def test_strip_concatenated_originals_removes_prefix(self) -> None:
        result = {
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": "Fullstack developer with experience in Python, React, and TypeScript.",
                    "tailored": (
                        "Fullstack developer with experience in Python, React, and TypeScript."
                        "\n\nResults-driven fullstack developer with strong Python and React skills."
                    ),
                }
            ]
        }
        _strip_concatenated_originals(result)
        tailored = result["sections"][0]["tailored"]
        assert not tailored.startswith("Fullstack developer with experience")
        assert "Results-driven" in tailored

    def test_strip_does_not_alter_clean_tailored(self) -> None:
        result = {
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": "Fullstack developer with Python.",
                    "tailored": "Results-driven backend engineer specializing in Python.",
                }
            ]
        }
        _strip_concatenated_originals(result)
        assert result["sections"][0]["tailored"] == "Results-driven backend engineer specializing in Python."

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

    def test_contact_injected_when_llm_drops_it(self, cv_text: str) -> None:
        result = {
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": "Developer summary",
                    "tailored": "Tailored summary",
                    "changes": [],
                }
            ]
        }
        patched = tailor_service._preserve_contact_section(result, cv_text)
        assert patched["sections"][0]["section_id"] == "contact_information"
        assert "Sam Developer" in patched["sections"][0]["tailored"]
        assert "sam@example.com" in patched["sections"][0]["tailored"]

    def test_all_projects_present_in_pdf(self, tmp_path: Path, source_cv: dict) -> None:
        sections = [
            {
                "section_name": "Projects",
                "content": (
                    "Memory Game\nA browser-based memory card game.\n\n"
                    "Expense Tracker\nPersonal finance tracker.\n\n"
                    "ApplyLuma\nAI-powered job application platform."
                ),
            }
        ]
        out = tmp_path / "test.pdf"
        generate_cv_pdf(sections, out)

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        for project in source_cv["projects"]:
            assert project in text, f"Project '{project}' missing from PDF"

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
    def test_detects_fabricated_skills(self, cv_text: str) -> None:
        result = {
            "sections": [
                {
                    "section_id": "skills",
                    "section_name": "Skills",
                    "original": "Python, JavaScript, TypeScript, React",
                    "tailored": "Python, JavaScript, TypeScript, React, Java, Azure DevOps",
                    "changes": [],
                }
            ]
        }
        fabricated = _validate_no_fabricated_skills(result, cv_text)
        assert "java" in fabricated
        assert "azure devops" in fabricated

    def test_removes_fabricated_skills(self, cv_text: str) -> None:
        result = {
            "sections": [
                {
                    "section_id": "skills",
                    "section_name": "Skills",
                    "original": "Python, JavaScript, TypeScript, React",
                    "tailored": "Python, JavaScript, TypeScript, React, Java, Azure DevOps",
                    "changes": [],
                }
            ]
        }
        removed = _remove_fabricated_skills(result, cv_text)
        assert len(removed) > 0
        tailored = result["sections"][0]["tailored"]
        skills_list = [s.strip() for s in tailored.split(",")]
        assert "Java" not in skills_list, "Standalone 'Java' should be removed"
        assert "Azure DevOps" not in tailored
        assert "JavaScript" in tailored, "JavaScript must survive Java removal"
        assert "Python" in tailored
        assert "React" in tailored

    def test_no_false_positives_for_existing_skills(self, cv_text: str) -> None:
        result = {
            "sections": [
                {
                    "section_id": "skills",
                    "section_name": "Skills",
                    "original": "Python, React, TypeScript",
                    "tailored": "Python, React, TypeScript, FastAPI, Docker",
                    "changes": [],
                }
            ]
        }
        fabricated = _validate_no_fabricated_skills(result, cv_text)
        assert "python" not in fabricated
        assert "react" not in fabricated
        assert "typescript" not in fabricated
        assert "fastapi" not in fabricated
        assert "docker" not in fabricated

    def test_fabrication_check_integrated_in_tailor_cv(
        self, monkeypatch: pytest.MonkeyPatch, cv_text: str
    ) -> None:
        fabricated_response = json.dumps(
            {
                "language": "en",
                "sections": [
                    {
                        "section_id": "skills",
                        "section_name": "Skills",
                        "original": "Python, React",
                        "tailored": "Python, React, Java, Azure DevOps",
                        "changes": [],
                    }
                ],
                "meta": {
                    "keywords_added": ["Java", "Azure DevOps"],
                    "keywords_already_present": ["Python"],
                    "intensity_applied": "medium",
                },
            }
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
                            message=SimpleNamespace(content=fabricated_response),
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
            if "skill" in section.get("section_name", "").lower():
                assert "Java" not in section["tailored"]
                assert "Azure DevOps" not in section["tailored"]
                assert "Python" in section["tailored"]


# ---------------------------------------------------------------------------
# End-to-end: full tailoring → PDF → validation
# ---------------------------------------------------------------------------


class TestEndToEndTailoredPdf:
    def test_full_pipeline_produces_valid_pdf(
        self, tmp_path: Path, source_cv: dict, cv_text: str
    ) -> None:
        contact = _extract_contact_information(cv_text)
        pdf_sections = [
            {"section_name": "Contact Information", "content": contact},
            {
                "section_name": "Summary",
                "content": "Results-driven fullstack developer with Python and React expertise.",
            },
            {
                "section_name": "Skills",
                "content": "Python, TypeScript, React, FastAPI, PostgreSQL, Docker, Git, Node.js",
            },
            {
                "section_name": "Experience",
                "content": (
                    "Fullstack Developer Intern\nTech Corp, Stockholm\n"
                    "June 2025 - Present\n"
                    "- Built REST APIs using FastAPI and PostgreSQL\n"
                    "- Developed React components with TypeScript\n"
                ),
            },
            {
                "section_name": "Experience",
                "content": (
                    "Junior Developer\nStartup AB, Gothenburg\n"
                    "Jan 2024 - May 2025\n"
                    "- Maintained Node.js backend services\n"
                    "- Created responsive UIs with React and Tailwind CSS\n"
                ),
            },
            {
                "section_name": "Projects",
                "content": (
                    "Memory Game\nA browser-based memory card game.\n"
                    "Tech: JavaScript, HTML, CSS\n\n"
                    "Expense Tracker\nPersonal finance tracker.\n"
                    "Tech: React, TypeScript, Chart.js\n\n"
                    "ApplyLuma\nAI-powered job application platform.\n"
                    "Tech: FastAPI, React, PostgreSQL, Redis\n"
                ),
            },
            {
                "section_name": "Education",
                "content": (
                    "BSc Computer Science\nUniversity of Gothenburg\n2021 - 2024\n"
                    "Thesis: Machine Learning Approaches to Resume Parsing\n180 credits\n\n"
                    "MSc Software Engineering\nChalmers University of Technology\n2024 - 2026\n"
                    "Thesis: Automated CV Tailoring with Large Language Models\n120 credits"
                ),
            },
        ]
        out = tmp_path / "final.pdf"
        generate_cv_pdf(pdf_sections, out)

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)

        assert text.count("Experience") == 1, "Experience header appears more than once"

        assert text.count("Sam Developer") == 1, "Contact info duplicated"
        assert "sam@example.com" in text
        assert "+46 70 123 4567" in text
        assert "github.com/samdev" in text

        for project in source_cv["projects"]:
            assert project in text, f"Project '{project}' dropped from output"

        assert "Machine Learning Approaches to Resume Parsing" in text
        assert "Automated CV Tailoring with Large Language Models" in text

        source_skills = {s.lower() for s in source_cv["skills"]}
        for word in text.split():
            cleaned = word.strip(".,;:()").lower()
            if len(cleaned) > 2 and cleaned.isalpha():
                pass


# ---------------------------------------------------------------------------
# Round 2: Fuzzy concatenation stripping
# ---------------------------------------------------------------------------


class TestFuzzyConcatenationStripping:
    def test_strip_with_whitespace_differences(self) -> None:
        original = "Fullstack developer\n\nwith experience in Python,\nReact, and TypeScript."
        tailored_actual = "Results-driven fullstack developer with strong Python and React skills."
        tailored_with_prefix = (
            "Fullstack developer\nwith experience in Python, React, and TypeScript.\n\n"
            + tailored_actual
        )
        result = {
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": original,
                    "tailored": tailored_with_prefix,
                }
            ]
        }
        _strip_concatenated_originals(result)
        tailored = result["sections"][0]["tailored"]
        assert "Results-driven" in tailored
        assert tailored.startswith("Results-driven") or len(tailored) < len(tailored_with_prefix)

    def test_strip_with_minor_rewording(self) -> None:
        original = (
            "Experienced Python developer with background in web development "
            "and database management. Skilled in FastAPI and PostgreSQL."
        )
        tailored_prefix = (
            "Experienced Python developer with a background in web development "
            "and database management. Skilled in FastAPI and PostgreSQL."
        )
        tailored_actual = "Backend engineer specializing in Python microservices."
        combined = tailored_prefix + "\n\n" + tailored_actual
        result = {
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": original,
                    "tailored": combined,
                }
            ]
        }
        _strip_concatenated_originals(result)
        tailored = result["sections"][0]["tailored"]
        assert len(tailored) < len(combined)

    def test_no_false_positive_on_genuinely_different_text(self) -> None:
        original = "Python developer with 3 years experience in web development."
        tailored = "Backend engineer specializing in distributed systems and cloud architecture."
        result = {
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": original,
                    "tailored": tailored,
                }
            ]
        }
        _strip_concatenated_originals(result)
        assert result["sections"][0]["tailored"] == tailored


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
    def test_cid_artifacts_return_empty(self) -> None:
        cv_text = (
            "(cid:42)(cid:81)(cid:74)(cid:76)(cid:79)(cid:72)\n"
            "sam@example.com\n"
            "+46 70 123 4567\n"
            "(cid:54)(cid:88)(cid:80)(cid:80)(cid:68)(cid:85)(cid:92)\n"
            "Some summary text here."
        )
        contact = _extract_contact_information(cv_text)
        assert contact == ""

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
