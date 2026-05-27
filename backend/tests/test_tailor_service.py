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


class FakeOpenAI:
    last_kwargs: dict[str, Any] | None = None
    content = json.dumps(
        {
            "language": "en",
            "sections": [
                {
                    "section_id": "summary",
                    "section_name": "Summary",
                    "original": "Python developer",
                    "tailored": "Backend developer with Python and SQL experience",
                    "changes": ["Added job keywords"],
                }
            ],
            "meta": {
                "keywords_added": ["SQL"],
                "keywords_already_present": ["Python"],
                "intensity_applied": "medium",
            },
        }
    )

    def __init__(self, api_key: str, timeout: float | None = None) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        FakeOpenAI.last_kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=FakeOpenAI.content))]
        )


def test_tailor_cv_calls_openai_with_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(tailor_service, "detect", lambda text: "en")

    result = tailor_service.tailor_cv(
        cv_content="Python developer",
        jd_description="Need Python and SQL",
        jd_keywords=["Python", "SQL"],
        intensity=TailorIntensity.medium,
    )

    assert result["language"] == "en"
    assert result["sections"][0]["section_id"] == "summary"
    assert FakeOpenAI.last_kwargs is not None
    assert FakeOpenAI.last_kwargs["model"] == "gpt-4o"
    assert FakeOpenAI.last_kwargs["response_format"] == {"type": "json_object"}
    assert "Restructure bullet points" in FakeOpenAI.last_kwargs["messages"][0]["content"]
    assert "detected language is en" in FakeOpenAI.last_kwargs["messages"][0]["content"]
    assert "Python, SQL" in FakeOpenAI.last_kwargs["messages"][1]["content"]


def test_tailor_cv_prompt_preserves_contact_information(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(tailor_service, "detect", lambda text: "en")

    result = tailor_service.tailor_cv(
        cv_content="Alex Example\nalex@example.com\n+1 555 0100\nStockholm, Sweden",
        jd_description="Need Python and SQL",
        jd_keywords=["Python", "SQL"],
        intensity=TailorIntensity.medium,
    )

    assert FakeOpenAI.last_kwargs is not None
    prompt = FakeOpenAI.last_kwargs["messages"][0]["content"]
    assert prompt.startswith("PRESERVE ALL CONTACT INFORMATION")
    assert "EXACTLY as provided in the original CV" in prompt
    assert "The first section MUST be contact_information" in prompt
    assert result["sections"][0]["section_id"] == "contact_information"
    assert result["sections"][0]["original"] == result["sections"][0]["tailored"]
    assert "Alex Example" in result["sections"][0]["tailored"]
    assert "alex@example.com" in result["sections"][0]["tailored"]
    assert "+1 555 0100" in result["sections"][0]["tailored"]
    assert "Stockholm, Sweden" in result["sections"][0]["tailored"]


def test_tailor_cv_restores_changed_contact_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(tailor_service, "detect", lambda text: "en")
    monkeypatch.setattr(
        FakeOpenAI,
        "content",
        json.dumps(
            {
                "language": "en",
                "sections": [
                    {
                        "section_id": "contact_information",
                        "section_name": "Contact",
                        "original": "Wrong Name\nwrong@example.com",
                        "tailored": "",
                        "changes": ["Removed contact details"],
                    }
                ],
                "meta": {"intensity_applied": "medium"},
            }
        ),
    )

    result = tailor_service.tailor_cv(
        cv_content="Alex Example\nalex@example.com\n+1 555 0100\nStockholm, Sweden",
        jd_description="Need Python and SQL",
        jd_keywords=["Python", "SQL"],
        intensity=TailorIntensity.medium,
    )

    contact = result["sections"][0]
    assert contact["original"] == contact["tailored"]
    assert "Alex Example" in contact["tailored"]
    assert "wrong@example.com" not in contact["tailored"]


def test_generated_pdf_includes_contact_information(tmp_path: Path) -> None:
    output_path = tmp_path / "tailored-cv.pdf"
    generate_cv_pdf(
        [
            {
                "section_name": "Contact Information",
                "content": "Alex Example\nalex@example.com\n+1 555 0100\nStockholm, Sweden",
            },
            {"section_name": "Summary", "content": "Backend developer with Python and SQL."},
        ],
        output_path,
    )

    with pdfplumber.open(output_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "Alex Example" in text
    assert "alex@example.com" in text
    assert "+1 555 0100" in text
    assert "Stockholm, Sweden" in text


def test_tailor_cv_rejects_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        tailor_service.tailor_cv(
            cv_content="CV",
            jd_description="JD",
            jd_keywords=[],
            intensity=TailorIntensity.light,
        )


def test_tailor_cv_rejects_non_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(FakeOpenAI, "content", "not-json")

    with pytest.raises(ValueError, match="non-JSON"):
        tailor_service.tailor_cv(
            cv_content="CV",
            jd_description="JD",
            jd_keywords=[],
            intensity=TailorIntensity.aggressive,
        )
