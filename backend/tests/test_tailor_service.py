from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.models.tailor_job import TailorIntensity
from app.services import tailor_service


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
