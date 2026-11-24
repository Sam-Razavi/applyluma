"""assess(): the two model calls, the quote check and the rules together.

The model is faked, so these tests pin what the code does with the model's
output, not what the model says.
"""

from __future__ import annotations

import json
import sys
from datetime import date
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
    # R3's not_met has nothing quoted, so it is not counted as a mismatch (rules v2).
    assert [r["status"] for r in result["requirements"]] == [
        "met", "met", "not_enough_information", "not_enough_information",
    ]
    assert result["requirements"][2]["model_status"] == "not_met"
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
    # Three set aside: the two invented "met" quotes and the unquoted "not_met".
    assert result["quote_stats"] == {
        "ad_quotes": 4, "ad_quotes_found": 4, "cv_quotes": 3, "cv_quotes_found": 1, "downgraded": 3,
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


def test_unmet_mandatory_requirement_with_quoted_evidence_gives_low_priority() -> None:
    cv = CV + "Driving licence: none.\n"
    client = FakeClient(REQUIREMENTS, evidence([
        judgement("R1", "met", "BSc Computer Science, KTH, 2026"),
        judgement("R2", "met", "REST API in Python with FastAPI"),
        judgement("R4", "not_met", "Driving licence: none."),
    ], recommendation="consider"))

    result = service.assess(cv, AD, client=client)

    assert result["recommendation"] == "low_priority"
    assert result["rule"] == "R1"
    assert result["requirements"][3]["downgraded"] is False


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
    client = FakeClient(REQUIREMENTS, evidence([judgement("R1", "met", "BSc Computer Science")]))
    result = service.assess(CV, AD, client=client, today=date(2026, 11, 13))

    # The model is told the date, or it reads a 2026 degree as unfinished.
    user2 = client.calls[1]["messages"][1]["content"]
    assert user2.startswith("Today's date: 2026-11-13. Any study or job period in the CV that ends in 2026")
    assert user2.endswith("Reminder: today is 2026-11-13. Any study or job period in the CV that ends in 2026 or earlier has ended.")
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
        "reference_date": "2026-11-13",
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
    assert "<<<CV\n" in user2 and "\nCV>>>\n\nReminder: today is" in user2
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


# ---- prompt 6 / rules 2: missing evidence is not a mismatch -------------------
#
# Scenario numbers refer to the list in thesis/DESIGN_LOG.md (prompt 6 / rules 2).
# The model is faked: these pin what the code does with its answers. Whether the
# real model follows the prompt is checked on the practice cases, not here.

AD_K8S = """Junior Platform Engineer
Requirements: a bachelor's degree in computer science. Python is required.
Kubernetes is required. At least 2 years of professional experience.
Experience of user support is required. Terraform is a plus."""

K8S_REQUIREMENTS = [
    {"id": "a", "text": "Bachelor's degree in computer science", "category": "education",
     "importance": "mandatory", "ad_quote": "a bachelor's degree in computer science"},
    {"id": "b", "text": "Python", "category": "skill", "importance": "mandatory",
     "ad_quote": "Python is required"},
    {"id": "c", "text": "Kubernetes", "category": "skill", "importance": "mandatory",
     "ad_quote": "Kubernetes is required"},
    {"id": "d", "text": "At least 2 years of professional experience", "category": "experience",
     "importance": "mandatory", "ad_quote": "At least 2 years of professional experience"},
    {"id": "e", "text": "Experience of user support", "category": "experience",
     "importance": "mandatory", "ad_quote": "Experience of user support is required"},
    {"id": "f", "text": "Terraform", "category": "skill", "importance": "preferred",
     "ad_quote": "Terraform is a plus"},
]

CV_K8S = """Ali Berg
BSc Computer Science, Uppsala University, 2022-2025
Developer, Lumen AB, January 2025 - present: Python services on Kubernetes.
Internship, IT helpdesk, Uppsala kommun, summer 2024: helped staff with laptops and accounts.
Skills: Python, Kubernetes, Docker, Git"""


def assess_k8s(
    judgements: list[dict[str, str]], cv: str = CV_K8S, requirements: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    client = FakeClient(requirements or K8S_REQUIREMENTS, evidence(judgements))
    return service.assess(cv, AD_K8S, client=client, today=date(2026, 12, 1))


ALL_MET = [
    judgement("R1", "met", "BSc Computer Science, Uppsala University, 2022-2025"),
    judgement("R2", "met", "Python services on Kubernetes"),
    judgement("R3", "met", "Kubernetes"),
    judgement("R4", "met", "Developer, Lumen AB, January 2025 - present"),
    judgement("R5", "met", "helped staff with laptops and accounts"),
    judgement("R6", "not_enough_information"),
]


def with_judgement(index: int, item: dict[str, str]) -> list[dict[str, str]]:
    return [item if i == index else j for i, j in enumerate(ALL_MET)]


CV_NO_K8S = CV_K8S.replace(" on Kubernetes", "").replace("Kubernetes, ", "")


def test_unmentioned_mandatory_skill_is_not_enough_information_and_not_low() -> None:
    """Scenario 1: Kubernetes required, the CV never mentions it."""
    result = assess_k8s(with_judgement(2, judgement("R3", "not_enough_information")), cv=CV_NO_K8S)

    assert result["requirements"][2]["status"] == "not_enough_information"
    assert result["recommendation"] == "consider" and result["rule"] == "R3"


def test_a_model_not_met_for_an_unmentioned_skill_is_set_aside() -> None:
    """Scenarios 1 and 6: the old reading (absent, so unmet) no longer gives Low."""
    result = assess_k8s(with_judgement(2, judgement("R3", "not_met")), cv=CV_NO_K8S)

    k8s = result["requirements"][2]
    assert (k8s["status"], k8s["model_status"], k8s["downgraded"], k8s["downgrade_reason"]) == (
        "not_enough_information", "not_met", True, "cv_quote_missing",
    )
    assert result["recommendation"] == "consider"


def test_a_not_met_whose_quote_is_not_in_the_cv_is_set_aside() -> None:
    """Scenario 6: an invented quote cannot carry a mismatch."""
    result = assess_k8s(
        with_judgement(2, judgement("R3", "not_met", "No experience with Kubernetes")), cv=CV_NO_K8S
    )

    k8s = result["requirements"][2]
    assert (k8s["status"], k8s["downgrade_reason"], k8s["cv_quote_found"]) == (
        "not_enough_information", "cv_quote_not_found", False,
    )
    assert result["recommendation"] == "consider"


def test_a_cv_that_states_the_lack_gives_low() -> None:
    """Scenario 2: the CV itself says the qualification is missing."""
    cv = CV_NO_K8S + "\nNot yet worked with Kubernetes."
    result = assess_k8s(with_judgement(2, judgement("R3", "not_met", "Not yet worked with Kubernetes")), cv=cv)

    assert result["requirements"][2]["status"] == "not_met"
    assert result["requirements"][2]["downgrade_reason"] == ""
    assert result["recommendation"] == "low_priority" and result["rule"] == "R1"


def test_an_unfinished_degree_is_not_met() -> None:
    """Scenario 3: a completed degree is required, the CV says it ends in 2027."""
    cv = CV_K8S.replace("2022-2025", "2024-2027 (expected)")
    result = assess_k8s(with_judgement(0, judgement("R1", "not_met", "2024-2027 (expected)")), cv=cv)

    assert result["requirements"][0]["status"] == "not_met"
    assert result["recommendation"] == "low_priority"


def test_positive_evidence_for_every_mandatory_requirement_gives_high() -> None:
    """Scenario 4; also scenario 7: an internship meets "experience of user support",
    an amount of experience asked without a number."""
    result = assess_k8s(ALL_MET)

    assert result["recommendation"] == "high_priority" and result["rule"] == "R2"
    assert result["requirements"][4]["status"] == "met"
    assert all(not r["downgraded"] for r in result["requirements"])


def test_positive_judgement_without_evidence_is_still_set_aside() -> None:
    """Scenario 5: the downgrade from version 1 is unchanged."""
    result = assess_k8s(with_judgement(2, judgement("R3", "met", "Kubernetes certified")), cv=CV_NO_K8S)

    k8s = result["requirements"][2]
    assert (k8s["status"], k8s["model_status"], k8s["downgrade_reason"]) == (
        "not_enough_information", "met", "cv_quote_not_found",
    )
    assert result["recommendation"] == "consider"


@pytest.mark.parametrize(
    ("status", "quote", "expected"),
    [
        # Scenario 8: enough dated evidence, judged by the documented half rule.
        ("met", "Developer, Lumen AB, January 2025 - present", "high_priority"),
        ("partly_met", "Developer, Lumen AB, January 2025 - present", "consider"),
        # Scenario 9: a short or undated history is not a confirmed shortfall.
        ("not_enough_information", "Developer, Lumen AB, January 2025 - present", "consider"),
        ("not_met", "", "consider"),
    ],
)
def test_quantified_experience(status: str, quote: str, expected: str) -> None:
    result = assess_k8s(with_judgement(3, judgement("R4", status, quote)))

    assert result["recommendation"] == expected


def test_a_stated_total_below_half_is_a_confirmed_shortfall() -> None:
    """Scenario 8: the CV states the total, so the shortfall is documented."""
    cv = CV_K8S + "\nIn total 6 months of professional experience."
    result = assess_k8s(
        with_judgement(3, judgement("R4", "not_met", "In total 6 months of professional experience")), cv=cv
    )

    assert result["requirements"][3]["status"] == "not_met"
    assert result["recommendation"] == "low_priority"


def test_a_found_quote_is_not_checked_for_what_it_means() -> None:
    """The limit of the code-level check, pinned so it is not mistaken for more.

    The prompt says a dated period alone never confirms a shortfall. If the model
    still says not_met and quotes a dated period, the quote IS in the CV and the
    code keeps the judgement: substring matching cannot tell whether the words
    establish the mismatch. Manual review of the evaluation output covers this.
    """
    result = assess_k8s(
        with_judgement(3, judgement("R4", "not_met", "Developer, Lumen AB, January 2025 - present"))
    )

    assert result["requirements"][3]["status"] == "not_met"
    assert result["recommendation"] == "low_priority"


def test_preferred_and_unclear_requirements_do_not_make_it_low() -> None:
    """Scenario 10."""
    requirements = [*K8S_REQUIREMENTS[:5], dict(K8S_REQUIREMENTS[5], importance="unclear"),
                    dict(K8S_REQUIREMENTS[5], id="g", importance="preferred")]
    cv = CV_K8S + "\nNever used Terraform."
    judgements = [*ALL_MET[:5], judgement("R6", "not_met", "Never used Terraform"),
                  judgement("R7", "not_met", "Never used Terraform")]

    result = assess_k8s(judgements, cv=cv, requirements=requirements)

    assert result["recommendation"] == "high_priority"


# ---- rules 2: requirements whose wording is not in the ad ---------------------


def test_an_invented_mandatory_requirement_cannot_make_it_low() -> None:
    """Scenario 11: the requirement is not in the ad, its 'not met' is not decisive."""
    invented = {"id": "x", "text": "Security clearance", "category": "other", "importance": "mandatory",
                "ad_quote": "Security clearance is required"}
    cv = CV_K8S + "\nNo security clearance."
    judgements = [*ALL_MET[:5], judgement("R6", "not_enough_information"),
                  judgement("R7", "not_met", "No security clearance.")]

    result = assess_k8s(judgements, cv=cv, requirements=[*K8S_REQUIREMENTS, invented])

    item = result["requirements"][6]
    assert item["ad_quote_found"] is False and item["status"] == "not_met"
    assert result["recommendation"] == "consider" and result["rule"] == "R4"
    assert result["limited_information"] is True
    # Kept in the output for audit, and counted apart.
    assert result["mandatory_unverified"] == 1 and result["mandatory_total"] == 5
    assert result["quote_stats"]["ad_quotes_found"] == 6


def test_validly_quoted_requirements_behave_as_before() -> None:
    """Scenario 16: every quote is found, so rules 2 give what rules 1 gave."""
    result = assess_k8s(ALL_MET)

    assert all(r["ad_quote_found"] for r in result["requirements"])
    assert result["mandatory_unverified"] == 0
    assert (result["mandatory_total"], result["mandatory_met"]) == (5, 5)


def test_the_evidence_prompt_no_longer_treats_absence_as_a_mismatch() -> None:
    """Pins prompt 6 against the phrases that made absence count as not_met.

    A prompt change once shifted judgements on unrelated requirements, so the
    rules for dates, licences, skills, certifications and experience are pinned
    together.
    """
    text = prompts.EVIDENCE_PROMPT
    assert prompts.PROMPT_VERSION == "7"
    assert "a CV normally" not in text and "normally lists" not in text
    assert "always lists the jobs" not in text
    assert "never not_met only because the CV does not mention it" in text
    assert "Required for met, partly_met and not_met" in text
    for silent in ("driving licence", "work permit", "language level", "willingness to travel"):
        assert silent in text.split("not_enough_information: the CV does not settle it")[1]
    assert "states the person's total relevant experience" in text
    assert "a short added-up total does not show that the person's total is short" in text
    # Prompt 7 (stress case s09): a stated total below half is not_met, said outright,
    # and the note must say whether the total is stated or added up.
    assert "A total stated by the CV that is below half is always not_met" in text
    assert "say whether the CV states that total itself or you added it up" in text
    assert "half of the amount asked" in text  # the half rule itself is unchanged
    assert "An education or job is completed when its end date is before today" in text
    assert "is never not_met in that case" in text  # experience without a number


def test_the_requirements_prompt_reads_list_headings() -> None:
    """Prompt 7 (stress case s08): items under a "Requirements" heading are
    mandatory; a heading that only describes the person decides nothing."""
    text = prompts.REQUIREMENTS_PROMPT
    mandatory = text.split("- mandatory:")[1].split("- preferred:")[0]
    preferred = text.split("- preferred:")[1].split("- unclear:")[0]
    unclear = text.split("- unclear:")[1].split("- ad_quote:")[0]
    for heading in ('"Requirements"', '"Must have"', '"Krav"', '"Vi kräver"'):
        assert heading in mandatory
    for heading in ('"Nice to have"', '"Meriterande"'):
        assert heading in preferred
    for heading in ('"About you"', '"Vi tror att du"', '"Om dig"'):
        assert heading in unclear
    assert "Do not guess" in unclear
