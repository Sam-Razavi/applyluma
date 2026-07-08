"""Tests for the structured CV renderer: context building, HTML templates,
and (where WeasyPrint's native libraries are present) PDF output."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import cv_render


def structured_cv(**overrides: Any) -> dict:
    payload: dict[str, Any] = {
        "language": "en",
        "header": {
            "full_name": "Sam Developer",
            "target_headline": "Fullstack Developer | Python & React",
            "location": "Stockholm, Sweden",
            "phone": "+46 70 123 4567",
            "email": "sam@example.com",
            "links": ["github.com/samdev", "linkedin.com/in/samdev"],
        },
        "summary": {
            "tailored": "Fullstack developer with production experience in Python and React.",
            "original": "Fullstack developer.",
            "changes": [],
        },
        "skills": {
            "groups": [
                {"category": "Languages", "items": ["Python", "TypeScript", "SQL"]},
                {"category": "Backend & APIs", "items": ["FastAPI", "PostgreSQL"]},
            ],
            "original": "Python, TypeScript, SQL, FastAPI, PostgreSQL",
            "changes": [],
        },
        "experience": [
            {
                "title": "Fullstack Developer Intern",
                "company": "Tech Corp",
                "location": "Stockholm",
                "dates": "June 2025 - Present",
                "bullets": [
                    "Built REST APIs using FastAPI and PostgreSQL.",
                    "Developed React components with TypeScript.",
                ],
                "original": "Fullstack Developer Intern\nTech Corp",
                "changes": [],
            }
        ],
        "projects": [
            {
                "name": "ApplyLuma",
                "subtitle": "AI-powered job application platform",
                "url": "github.com/samdev/applyluma",
                "stack": ["FastAPI", "React", "PostgreSQL"],
                "bullets": ["Shipped end-to-end job tracking with AI CV tailoring."],
                "original": "ApplyLuma project",
                "changes": [],
            }
        ],
        "education": [
            {
                "degree": "BSc Computer Science",
                "institution": "University of Gothenburg",
                "dates": "2021 - 2024",
                "details": "Thesis: Machine Learning Approaches to Resume Parsing",
                "relevant_coursework": ["Databases", "Algorithms"],
                "original": "BSc Computer Science, University of Gothenburg",
                "changes": [],
            }
        ],
        "certifications": {
            "items": [{"name": "AWS Cloud Practitioner", "issuer": "AWS", "date": "2025"}],
            "original": "AWS Cloud Practitioner (2025)",
            "changes": [],
        },
        "additional_sections": [
            {
                "section_name": "Languages",
                "tailored": "Swedish (native), English (fluent)",
                "original": "Swedish, English",
                "changes": [],
            }
        ],
        "section_order": ["summary", "skills", "projects", "experience", "education", "certifications"],
        "meta": {
            "keywords_added": [],
            "keywords_already_present": [],
            "intensity_applied": "medium",
            "estimated_pages": 1,
        },
    }
    payload.update(overrides)
    return payload


class TestBuildRenderContext:
    def test_all_blocks_present_in_model_order(self) -> None:
        context = cv_render.build_render_context(structured_cv())
        kinds = [b["kind"] for b in context["blocks"]]
        assert kinds == [
            "summary", "skills", "projects", "experience",
            "education", "certifications", "raw",
        ]
        assert context["header"]["full_name"] == "Sam Developer"
        assert "sam@example.com" in context["header"]["contact_bits"]
        assert "github.com/samdev" in context["header"]["contact_bits"]

    def test_rejected_section_falls_back_to_original_raw(self) -> None:
        context = cv_render.build_render_context(
            structured_cv(),
            accepted_section_ids=["skills", "experience_0", "project_0", "education_0",
                                  "certifications", "additional_0"],
        )
        summary_block = context["blocks"][0]
        assert summary_block["kind"] == "summary"
        assert summary_block["text"] == "Fullstack developer."

    def test_rejected_experience_entry_renders_original_lines(self) -> None:
        context = cv_render.build_render_context(
            structured_cv(),
            accepted_section_ids=["summary", "skills"],
        )
        exp_block = next(b for b in context["blocks"] if b["kind"] == "experience")
        entry = exp_block["entries"][0]
        assert entry["kind"] == "raw"
        assert entry["lines"][0]["text"] == "Fullstack Developer Intern"

    def test_override_takes_precedence(self) -> None:
        context = cv_render.build_render_context(
            structured_cv(),
            section_overrides={"summary": "My own edited summary."},
        )
        summary_block = context["blocks"][0]
        assert summary_block["text"] == "My own edited summary."

    def test_user_section_order_reorders_groups(self) -> None:
        context = cv_render.build_render_context(
            structured_cv(),
            section_order=["education_0", "summary", "skills"],
        )
        kinds = [b["kind"] for b in context["blocks"]]
        assert kinds[0] == "education"
        assert kinds[1] == "summary"

    def test_rejected_skills_render_original_as_raw(self) -> None:
        context = cv_render.build_render_context(
            structured_cv(),
            accepted_section_ids=["summary"],
        )
        raw_skills = next(
            b for b in context["blocks"] if b["kind"] == "raw" and b["title"] == "Skills"
        )
        assert raw_skills["lines"][0]["text"].startswith("Python, TypeScript")


class TestRenderHtml:
    @pytest.mark.parametrize("template_id", sorted(cv_render.TEMPLATES))
    def test_templates_render_all_content(self, template_id: str) -> None:
        context = cv_render.build_render_context(structured_cv())
        html = cv_render.render_html(context, template_id)
        for expected in (
            "Sam Developer",
            "Fullstack Developer | Python &amp; React",
            "sam@example.com",
            "Backend &amp; APIs",
            "Built REST APIs using FastAPI and PostgreSQL.",
            "ApplyLuma",
            "github.com/samdev/applyluma",
            "BSc Computer Science",
            "Machine Learning Approaches to Resume Parsing",
            "AWS Cloud Practitioner",
            "Swedish (native), English (fluent)",
        ):
            assert expected in html, f"'{expected}' missing from {template_id} template"

    def test_unknown_template_falls_back_to_default(self) -> None:
        context = cv_render.build_render_context(structured_cv())
        assert cv_render.render_html(context, "nope") == cv_render.render_html(
            context, cv_render.DEFAULT_TEMPLATE
        )

    def test_html_escapes_user_content(self) -> None:
        cv = structured_cv()
        cv["summary"]["tailored"] = "Uses <script>alert('x')</script> daily."
        context = cv_render.build_render_context(cv)
        html = cv_render.render_html(context)
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_swedish_headings_in_rendered_html(self) -> None:
        context = cv_render.build_render_context(structured_cv(language="sv"))
        html = cv_render.render_html(context)
        assert "Sammanfattning" in html
        assert "Kompetenser" in html
        assert "Utbildning" in html


@pytest.mark.skipif(not cv_render.is_available(), reason="WeasyPrint native libs not installed")
class TestRenderPdf:
    def test_pdf_written_with_page_count(self, tmp_path: Path) -> None:
        import pdfplumber

        context = cv_render.build_render_context(
            structured_cv(),
            contact_text="Sam Developer\nsam@example.com",
        )
        out = tmp_path / "cv.pdf"
        pages = cv_render.render_pdf(context, out)
        assert pages >= 1
        assert out.stat().st_size > 0

        with pdfplumber.open(out) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        assert "Sam Developer" in text
        assert "FastAPI" in text

    def test_count_pages_matches_render(self, tmp_path: Path) -> None:
        context = cv_render.build_render_context(structured_cv())
        counted = cv_render.count_pages(context)
        rendered = cv_render.render_pdf(context, tmp_path / "cv.pdf")
        assert counted == rendered
