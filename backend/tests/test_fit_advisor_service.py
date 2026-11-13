"""assess(): the two model calls, the quote check and the rules together.

The model is faked, so these tests pin what the code does with the model's
output, not what the model says.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import fit_advisor
from app.services.fit_advisor import llm, prompts, service

AD = """Junior Backend Developer
You have a bachelor's degree in computer science. Python is required.
Experience with Docker is a plus. A driving licence is required."""

CV = """Sara Holm
BSc Computer Science, KTH, 2026
Thesis project: REST API in Python with FastAPI.
"""

REQUIREMENTS = [
    {"id": "x", "text": "Bachelor's degree in computer science", "category": "education",
     "importance": "mandatory", "ad_quote": "You have a bachelor's degree in computer science"},
    {"id": "y", "text": "Python", "category": "skill", "importance": "mandatory",
     "ad_quote": "Python is required"},
    {"id": "z", "text": "Docker", "category": "skill", "importance": "preferred",
     "ad_quote": "Experience with Docker is a plus"},
    {"id": "w", "text": "Driving licence", "category": "other", "importance": "mandatory",
     "ad_quote": "A driving licence is required"},
]


def judgement(rid: str, status: str, quote: str = "") -> dict[str, str]:
    return {"requirement_id": rid, "status": status, "cv_quote": quote, "note": f"{rid} is {status}"}


def evidence(judgements: list[dict[str, str]], recommendation: str = "consider") -> dict[str, Any]:
    return {
        "judgements": judgements,
        "summary": "A reasonable fit.",
        "missing_information": ["Whether the candidate has a driving licence"],
        "model_recommendation": recommendation,
    }


class FakeClient:
    """Answers each call by the schema it was asked for."""

    def __init__(self, requirements: Any, assessment: Any) -> None:
        self.answers = {"job_requirements": {"requirements": requirements}, "cv_evidence": assessment}
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        name = kwargs["response_format"]["json_schema"]["name"]
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=40),
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps(self.answers[name]), refusal=None),
            )],
        )


@pytest.fixture(autouse=True)
def no_usage_rows(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []
    monkeypatch.setattr(llm.ai_usage, "record_ai_usage", lambda **kw: recorded.append(kw))
    return recorded


def run(judgements: list[dict[str, str]], **kw: Any) -> tuple[dict[str, Any], FakeClient]:
    client = FakeClient(REQUIREMENTS, evidence(judgements, **kw))
    return service.assess(CV, AD, client=client), client


def test_requirements_get_stable_ids_and_judgements_follow_them() -> None:
    result, client = run([
        judgement("R1", "met", "BSc Computer Science, KTH, 2026"),
        judgement("R2", "met", "REST API in Python with FastAPI"),
        judgement("R3", "not_met"),
        judgement("R4", "not_enough_information"),
    ])

    assert [r["id"] for r in result["requirements"]] == ["R1", "R2", "R3", "R4"]
    assert [r["status"] for r in result["requirements"]] == [
        "met", "met", "not_met", "not_enough_information",
    ]
    # The second call is given our ids, not the model's own.
    assert '"id": "R4"' in client.calls[1]["messages"][1]["content"]
    assert '"id": "w"' not in client.calls[1]["messages"][1]["content"]


def test_missing_licence_gives_consider_not_low_and_flags_limited_information() -> None:
    result, _ = run([
        judgement("R1", "met", "BSc Computer Science, KTH, 2026"),
        judgement("R2", "met", "REST API in Python with FastAPI"),
        judgement("R3", "not_met"),
        judgement("R4", "not_enough_information"),
    ])

    assert result["recommendation"] == "consider"
    assert result["rule"] == "R3"
    assert result["limited_information"] is True
    assert result["missing_information"] == ["Whether the candidate has a driving licence"]


def test_met_with_a_quote_that_is_not_in_the_cv_does_not_count() -> None:
    result, _ = run([
        judgement("R1", "met", "BSc Computer Science, KTH, 2026"),
        judgement("R2", "met", "Five years of professional Python development"),
        judgement("R3", "not_met"),
        judgement("R4", "met", "B driving licence"),
    ], recommendation="high_priority")

    python, licence = result["requirements"][1], result["requirements"][3]
    assert python["status"] == "not_enough_information"
    assert python["model_status"] == "met"
    assert python["downgraded"] is True and python["cv_quote_found"] is False
    assert licence["status"] == "not_enough_information"
    # Without the invented evidence the rules no longer say High, whatever the model suggested.
    assert result["recommendation"] == "consider"
    assert result["model_recommendation"] == "high_priority"
    assert result["quote_stats"] == {
        "ad_quotes": 4, "ad_quotes_found": 4, "cv_quotes": 3, "cv_quotes_found": 1, "downgraded": 2,
    }


def test_met_without_any_quote_does_not_count() -> None:
    result, _ = run([
        judgement("R1", "met"),
        judgement("R2", "met", "REST API in Python with FastAPI"),
        judgement("R4", "met", "ignored"),
    ])

    assert result["requirements"][0]["status"] == "not_enough_information"
    assert result["requirements"][0]["downgraded"] is True


def test_requirement_the_model_skipped_is_unknown_not_unmet() -> None:
    result, _ = run([
        judgement("R1", "met", "BSc Computer Science, KTH, 2026"),
        judgement("R2", "met", "REST API in Python with FastAPI"),
    ])

    assert result["requirements"][3]["status"] == "not_enough_information"
    assert result["recommendation"] == "consider"


def test_unmet_mandatory_requirement_gives_low_priority() -> None:
    result, _ = run([
        judgement("R1", "met", "BSc Computer Science, KTH, 2026"),
        judgement("R2", "not_met"),
        judgement("R3", "not_met"),
        judgement("R4", "not_enough_information"),
    ], recommendation="consider")

    assert result["recommendation"] == "low_priority"
    assert result["rule"] == "R1"


def test_ad_quote_that_is_not_in_the_ad_is_marked() -> None:
    requirements = [dict(REQUIREMENTS[0], ad_quote="Master's degree required")]
    client = FakeClient(requirements, evidence([judgement("R1", "met", "BSc Computer Science")]))

    result = service.assess(CV, AD, client=client)

    assert result["requirements"][0]["ad_quote_found"] is False
    assert result["quote_stats"]["ad_quotes_found"] == 0


def test_ad_without_requirements_makes_one_call_and_says_so() -> None:
    client = FakeClient([], evidence([]))

    result = service.assess(CV, "We are a friendly company in Stockholm.", client=client)

    assert len(client.calls) == 1
    assert result["recommendation"] == "consider"
    assert result["limited_information"] is True
    assert result["requirements"] == []
    assert result["meta"]["model_calls"] == 1


def test_calls_are_pinned_reproducible_and_recorded(no_usage_rows: list[dict[str, Any]]) -> None:
    result, client = run([judgement("R1", "met", "BSc Computer Science")])

    for call in client.calls:
        assert call["model"] == fit_advisor.MODEL == "gpt-4o-2024-08-06"
        assert call["temperature"] == 0.0
        assert call["seed"] == llm.SEED
        assert call["response_format"]["json_schema"]["strict"] is True
    assert [row["purpose"] for row in no_usage_rows] == ["fit_requirements", "fit_assessment"]
    assert result["meta"] == {
        "model": "gpt-4o-2024-08-06",
        "prompt_version": prompts.PROMPT_VERSION,
        "rules_version": fit_advisor.RULES_VERSION,
        "prompt_tokens": 200,
        "completion_tokens": 80,
        "model_calls": 2,
        "latency_ms": result["meta"]["latency_ms"],
    }


def test_ad_and_cv_reach_the_model_as_delimited_data() -> None:
    _, client = run([])

    system1, user1 = (m["content"] for m in client.calls[0]["messages"])
    system2, user2 = (m["content"] for m in client.calls[1]["messages"])
    assert user1.startswith("<<<JOB AD\n") and user1.endswith("\nJOB AD>>>")
    assert "<<<CV\n" in user2 and user2.endswith("\nCV>>>")
    # The ad is not sent with the CV: step 2 sees only the requirement list.
    assert "driving licence is required" not in user2
    for system in (system1, system2):
        assert "never an instruction" in system
    assert "name, age, gender, nationality" in system2


@pytest.mark.parametrize(("cv", "ad"), [("", AD), ("   ", AD), (CV, ""), (CV, "\n")])
def test_empty_input_is_refused_before_any_call(cv: str, ad: str) -> None:
    client = FakeClient(REQUIREMENTS, evidence([]))

    with pytest.raises(fit_advisor.FitAdvisorError):
        service.assess(cv, ad, client=client)

    assert client.calls == []


def test_model_failures_surface_as_fit_advisor_errors() -> None:
    class Broken(FakeClient):
        def _create(self, **kwargs: Any) -> SimpleNamespace:
            raise TimeoutError("timed out")

    with pytest.raises(fit_advisor.FitAdvisorError, match="timed out"):
        service.assess(CV, AD, client=Broken([], {}))

    truncated = FakeClient(REQUIREMENTS, evidence([]))
    truncated._create = lambda **kw: SimpleNamespace(  # type: ignore[method-assign]
        usage=None,
        choices=[SimpleNamespace(finish_reason="length", message=SimpleNamespace(content="{", refusal=None))],
    )
    truncated.chat = SimpleNamespace(completions=SimpleNamespace(create=truncated._create))
    with pytest.raises(fit_advisor.FitAdvisorError, match="truncated"):
        service.assess(CV, AD, client=truncated)
