"""assess(): ad and CV in, recommendation with reasons out.

Step 1 (model)  requirements from the ad
Step 2 (model)  a judgement per requirement, with a quote from the CV
Quote check     a judgement resting on a quote that is not in the CV does not count
Rules           decision.decide() turns the judgements into the recommendation
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.services.fit_advisor import prompts, schemas
from app.services.fit_advisor.decision import RULES_VERSION, decide
from app.services.fit_advisor.evidence import quote_in_source
from app.services.fit_advisor.llm import MODEL, FitAdvisorError, call_structured

MAX_AD_CHARS = 15_000
MAX_CV_CHARS = 20_000
MAX_REQUIREMENTS = 30
OPENAI_TIMEOUT_SECONDS = 90.0


def _clean_requirements(raw: Any) -> list[dict[str, Any]]:
    """Keep well-formed requirements and give them ids we control."""
    cleaned: list[dict[str, Any]] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
            continue
        importance = item.get("importance")
        category = item.get("category")
        cleaned.append(
            {
                "id": f"R{len(cleaned) + 1}",
                "text": str(item["text"]).strip(),
                "category": category if category in schemas.CATEGORIES else "other",
                "importance": importance if importance in schemas.IMPORTANCES else "unclear",
                "ad_quote": str(item.get("ad_quote") or "").strip(),
            }
        )
        if len(cleaned) == MAX_REQUIREMENTS:
            break
    return cleaned


def _apply_judgements(
    requirements: list[dict[str, Any]], raw: Any, cv_text: str, ad_text: str
) -> None:
    """Attach each judgement to its requirement and run the quote check."""
    by_id: dict[str, dict[str, Any]] = {}
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and isinstance(item.get("requirement_id"), str):
            by_id.setdefault(item["requirement_id"], item)

    for requirement in requirements:
        judgement = by_id.get(requirement["id"], {})
        status = judgement.get("status")
        if status not in schemas.STATUSES:
            # The model skipped this requirement: that is not evidence of anything.
            status = "not_enough_information"
        cv_quote = str(judgement.get("cv_quote") or "").strip()
        note = str(judgement.get("note") or "").strip()

        cv_quote_found = quote_in_source(cv_quote, cv_text) if cv_quote else None
        model_status = status
        downgraded = False
        if status in ("met", "partly_met") and not cv_quote_found:
            # "Met" must rest on words that are really in the CV.
            status = "not_enough_information"
            downgraded = True

        requirement.update(
            {
                "status": status,
                "model_status": model_status,
                "cv_quote": cv_quote,
                "cv_quote_found": cv_quote_found,
                "ad_quote_found": quote_in_source(requirement["ad_quote"], ad_text),
                "downgraded": downgraded,
                "note": note,
            }
        )


def _quote_stats(requirements: list[dict[str, Any]]) -> dict[str, int]:
    cv_checked = [r for r in requirements if r["cv_quote_found"] is not None]
    return {
        "ad_quotes": len(requirements),
        "ad_quotes_found": sum(1 for r in requirements if r["ad_quote_found"]),
        "cv_quotes": len(cv_checked),
        "cv_quotes_found": sum(1 for r in cv_checked if r["cv_quote_found"]),
        "downgraded": sum(1 for r in requirements if r["downgraded"]),
    }


def assess(
    cv_text: str,
    ad_text: str,
    *,
    user_id: uuid.UUID | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Assess how a CV fits a job ad. Raises FitAdvisorError on failure."""
    cv_text = (cv_text or "").strip()[:MAX_CV_CHARS]
    ad_text = (ad_text or "").strip()[:MAX_AD_CHARS]
    if not cv_text:
        raise FitAdvisorError("The CV has no text to assess")
    if not ad_text:
        raise FitAdvisorError("The job ad has no text to assess")

    if client is None:
        if not settings.OPENAI_API_KEY:
            raise FitAdvisorError("OPENAI_API_KEY is not configured")
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SECONDS)

    started = time.monotonic()

    step1, usage1 = call_structured(
        client,
        system=prompts.REQUIREMENTS_PROMPT,
        user=prompts.requirements_user_message(ad_text),
        schema=schemas.REQUIREMENTS_SCHEMA,
        purpose="fit_requirements",
        user_id=user_id,
    )
    requirements = _clean_requirements(step1.get("requirements"))

    summary = ""
    missing_information: list[str] = []
    model_recommendation: str | None = None
    usage2 = {"prompt_tokens": 0, "completion_tokens": 0}

    if requirements:
        for_model = [
            {key: r[key] for key in ("id", "text", "category", "importance")} for r in requirements
        ]
        step2, usage2 = call_structured(
            client,
            system=prompts.EVIDENCE_PROMPT,
            user=prompts.evidence_user_message(
                json.dumps(for_model, ensure_ascii=False, indent=1), cv_text
            ),
            schema=schemas.ASSESSMENT_SCHEMA,
            purpose="fit_assessment",
            user_id=user_id,
        )
        _apply_judgements(requirements, step2.get("judgements"), cv_text, ad_text)
        summary = str(step2.get("summary") or "").strip()
        missing_information = [
            str(item).strip() for item in step2.get("missing_information") or [] if str(item).strip()
        ]
        suggestion = step2.get("model_recommendation")
        model_recommendation = suggestion if suggestion in schemas.RECOMMENDATIONS else None
    else:
        summary = "The ad does not state any requirements that can be checked against the CV."

    decision = decide(requirements)

    return {
        **asdict(decision),
        "model_recommendation": model_recommendation,
        "summary": summary,
        "missing_information": missing_information,
        "requirements": requirements,
        "quote_stats": _quote_stats(requirements) if requirements else {
            "ad_quotes": 0, "ad_quotes_found": 0, "cv_quotes": 0, "cv_quotes_found": 0, "downgraded": 0,
        },
        "meta": {
            "model": MODEL,
            "prompt_version": prompts.PROMPT_VERSION,
            "rules_version": RULES_VERSION,
            "prompt_tokens": usage1["prompt_tokens"] + usage2["prompt_tokens"],
            "completion_tokens": usage1["completion_tokens"] + usage2["completion_tokens"],
            "model_calls": 2 if requirements else 1,
            "latency_ms": int((time.monotonic() - started) * 1000),
        },
    }
