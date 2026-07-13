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


def structured_response(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "language": "en",
        "header": {
            "full_name": "Alex Example",
            "target_headline": "Backend Developer | Python & SQL",
            "location": "Stockholm, Sweden",
            "phone": "+1 555 0100",
            "email": "alex@example.com",
            "links": [],
        },
        "summary": {
            "tailored": "Backend developer with Python and SQL experience",
            "original": "Python developer",
            "changes": ["Added job keywords"],
        },
        "skills": {
            "groups": [{"category": "Languages", "items": ["Python", "SQL"]}],
            "original": "Python, SQL",
            "changes": [],
        },
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": {"items": [], "original": "", "changes": []},
        "additional_sections": [],
        "section_order": ["summary", "skills"],
        "meta": {
            "keywords_added": ["SQL"],
            "keywords_already_present": ["Python"],
            "intensity_applied": "medium",
            "estimated_pages": 1,
        },
    }
    payload.update(overrides)
    return payload


class FakeOpenAI:
    last_kwargs: dict[str, Any] | None = None
    all_calls: list[dict[str, Any]] = []
    content = json.dumps(structured_response())

    def __init__(self, api_key: str, timeout: float | None = None) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        FakeOpenAI.last_kwargs = kwargs
        FakeOpenAI.all_calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=FakeOpenAI.content, refusal=None),
                )
            ]
        )


CV_TEXT = "Alex Example\nalex@example.com\n+1 555 0100\nStockholm, Sweden\n\nPython, SQL"


@pytest.fixture(autouse=True)
def reset_fake() -> None:
    FakeOpenAI.last_kwargs = None
    FakeOpenAI.all_calls = []
    FakeOpenAI.content = json.dumps(structured_response())


def _run_tailor(monkeypatch: pytest.MonkeyPatch, cv_content: str = CV_TEXT) -> dict:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(tailor_service, "detect", lambda text: "en")
    return tailor_service.tailor_cv(
        cv_content=cv_content,
        jd_description="Need Python and SQL",
        jd_keywords=["Python", "SQL"],
        intensity=TailorIntensity.medium,
    )


def test_tailor_cv_calls_openai_with_structured_outputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_tailor(monkeypatch)

    assert result["language"] == "en"
    assert FakeOpenAI.last_kwargs is not None
    assert FakeOpenAI.last_kwargs["model"] == "gpt-4o"
    assert FakeOpenAI.last_kwargs["temperature"] == 0.2
    response_format = FakeOpenAI.last_kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert "Restructure bullet points" in FakeOpenAI.last_kwargs["messages"][0]["content"]
    assert "Python, SQL" in FakeOpenAI.last_kwargs["messages"][1]["content"]


def test_tailor_cv_runs_verification_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _run_tailor(monkeypatch)

    assert len(FakeOpenAI.all_calls) == 2
    verify_call = FakeOpenAI.all_calls[1]
    # The audit turn carries the first answer plus the fact-check instruction.
    assert verify_call["messages"][2]["role"] == "assistant"
    assert "audit your own output" in verify_call["messages"][3]["content"]


def test_verify_pass_restates_jd_language(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    # CV and JD are in different languages so `jd_language` is unambiguous.
    monkeypatch.setattr(
        tailor_service, "detect", lambda text: "sv" if "Behover" in text else "en"
    )

    tailor_service.tailor_cv(
        cv_content=CV_TEXT,
        jd_description="Behover Python och SQL",
        jd_keywords=["Python", "SQL"],
        intensity=TailorIntensity.medium,
    )

    verify_call = FakeOpenAI.all_calls[1]
    assert "Required output language: sv" in verify_call["messages"][3]["content"]


def test_compress_pass_restates_jd_language(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(
        tailor_service, "detect", lambda text: "sv" if "Behover" in text else "en"
    )
    # Force the "exceeds two pages" branch on the first probe, then let the
    # compressed result look shorter so it is kept.
    page_counts = iter([3, 1])
    monkeypatch.setattr(
        tailor_service, "_probe_page_count", lambda *args, **kwargs: next(page_counts)
    )

    tailor_service.tailor_cv(
        cv_content=CV_TEXT,
        jd_description="Behover Python och SQL",
        jd_keywords=["Python", "SQL"],
        intensity=TailorIntensity.medium,
    )

    assert len(FakeOpenAI.all_calls) == 3
    compress_call = FakeOpenAI.all_calls[2]
    assert "Keep every field in sv" in compress_call["messages"][-1]["content"]


def test_verify_and_compress_prompts_format_safely() -> None:
    verify_text = tailor_service._VERIFY_PROMPT.format(jd_language="sv")
    compress_text = tailor_service._COMPRESS_PROMPT.format(jd_language="sv")

    assert "sv" in verify_text
    assert "sv" in compress_text


def test_tailor_cv_result_contains_structured_cv_and_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_tailor(monkeypatch)

    assert result["structured_cv"]["header"]["full_name"] == "Alex Example"
    section_ids = [s["section_id"] for s in result["sections"]]
    assert section_ids[0] == "contact_information"
    assert "summary" in section_ids
    assert "skills" in section_ids
    summary = next(s for s in result["sections"] if s["section_id"] == "summary")
    assert summary["original"] == "Python developer"
    assert summary["tailored"] == "Backend developer with Python and SQL experience"


def test_tailor_cv_prompt_preserves_contact_information(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_tailor(monkeypatch)

    assert FakeOpenAI.last_kwargs is not None
    prompt = FakeOpenAI.last_kwargs["messages"][0]["content"]
    assert prompt.startswith("PRESERVE ALL CONTACT INFORMATION")
    assert "EXACTLY as provided in the original CV" in prompt
    contact = result["sections"][0]
    assert contact["section_id"] == "contact_information"
    assert contact["original"] == contact["tailored"]
    assert "Alex Example" in contact["tailored"]
    assert "alex@example.com" in contact["tailored"]
    assert "+1 555 0100" in contact["tailored"]
    assert "Stockholm, Sweden" in contact["tailored"]


def test_tailor_cv_drops_header_contact_not_in_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeOpenAI.content = json.dumps(
        structured_response(
            header={
                "full_name": "Alex Example",
                "target_headline": "Backend Developer",
                "location": "Stockholm, Sweden",
                "phone": "+1 999 9999",
                "email": "wrong@example.com",
                "links": ["github.com/not-in-source"],
            }
        )
    )

    result = _run_tailor(monkeypatch)

    header = result["structured_cv"]["header"]
    assert header["email"] is None
    assert header["phone"] is None
    assert header["links"] == []


def test_tailor_cv_removes_fabricated_skills_from_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeOpenAI.content = json.dumps(
        structured_response(
            skills={
                "groups": [
                    {
                        "category": "Languages",
                        "items": ["Python", "SQL", "Java", "Azure DevOps"],
                    }
                ],
                "original": "Python, SQL",
                "changes": [],
            }
        )
    )

    result = _run_tailor(monkeypatch)

    items = result["structured_cv"]["skills"]["groups"][0]["items"]
    assert "Python" in items
    assert "SQL" in items
    assert "Java" not in items
    assert "Azure DevOps" not in items
    skills_section = next(s for s in result["sections"] if s["section_id"] == "skills")
    assert "Java" not in skills_section["tailored"]


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


def test_tailor_cache_key_is_stable_for_identical_inputs() -> None:
    key_a = tailor_service.tailor_cache_key(
        None, "cv text", "jd text", ["Python", "SQL"], TailorIntensity.medium
    )
    key_b = tailor_service.tailor_cache_key(
        None, "cv text", "jd text", ["Python", "SQL"], TailorIntensity.medium
    )
    assert key_a == key_b


def test_tailor_cache_key_ignores_keyword_order() -> None:
    key_a = tailor_service.tailor_cache_key(
        None, "cv text", "jd text", ["Python", "SQL"], TailorIntensity.medium
    )
    key_b = tailor_service.tailor_cache_key(
        None, "cv text", "jd text", ["SQL", "Python"], TailorIntensity.medium
    )
    assert key_a == key_b


def test_tailor_cache_key_changes_with_cv_content() -> None:
    key_a = tailor_service.tailor_cache_key(
        None, "cv text one", "jd text", [], TailorIntensity.medium
    )
    key_b = tailor_service.tailor_cache_key(
        None, "cv text two", "jd text", [], TailorIntensity.medium
    )
    assert key_a != key_b


def test_tailor_cache_key_changes_with_intensity() -> None:
    key_a = tailor_service.tailor_cache_key(None, "cv", "jd", [], TailorIntensity.light)
    key_b = tailor_service.tailor_cache_key(None, "cv", "jd", [], TailorIntensity.aggressive)
    assert key_a != key_b


def test_tailor_cache_key_scopes_by_user() -> None:
    import uuid as uuid_module

    user_a = uuid_module.uuid4()
    user_b = uuid_module.uuid4()
    key_a = tailor_service.tailor_cache_key(user_a, "cv", "jd", [], TailorIntensity.medium)
    key_b = tailor_service.tailor_cache_key(user_b, "cv", "jd", [], TailorIntensity.medium)
    assert key_a != key_b


def test_tailor_cache_key_accepts_plain_string_intensity() -> None:
    """Defensive: some callers may pass an already-unwrapped enum value."""
    key_enum = tailor_service.tailor_cache_key(None, "cv", "jd", [], TailorIntensity.medium)
    key_str = tailor_service.tailor_cache_key(None, "cv", "jd", [], "medium")
    assert key_enum == key_str


def test_tailor_cv_rejects_non_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(tailor_service, "OpenAI", FakeOpenAI)
    FakeOpenAI.content = "not-json"

    with pytest.raises(ValueError, match="non-JSON"):
        tailor_service.tailor_cv(
            cv_content="CV",
            jd_description="JD",
            jd_keywords=[],
            intensity=TailorIntensity.aggressive,
        )
