"""Strict JSON schemas for the two model calls (OpenAI Structured Outputs)."""

from __future__ import annotations

from typing import Any

IMPORTANCES = ("mandatory", "preferred", "unclear")
CATEGORIES = ("skill", "experience", "education", "language", "certification", "other")
STATUSES = ("met", "partly_met", "not_met", "not_enough_information")
RECOMMENDATIONS = ("high_priority", "consider", "low_priority")


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    # Strict mode needs every property required and no extras.
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


REQUIREMENTS_SCHEMA: dict[str, Any] = {
    "name": "job_requirements",
    "strict": True,
    "schema": _object(
        {
            "requirements": {
                "type": "array",
                "items": _object(
                    {
                        "id": {"type": "string"},
                        "text": {"type": "string"},
                        "category": {"type": "string", "enum": list(CATEGORIES)},
                        "importance": {"type": "string", "enum": list(IMPORTANCES)},
                        "ad_quote": {"type": "string"},
                    }
                ),
            }
        }
    ),
}

ASSESSMENT_SCHEMA: dict[str, Any] = {
    "name": "cv_evidence",
    "strict": True,
    "schema": _object(
        {
            "judgements": {
                "type": "array",
                "items": _object(
                    {
                        "requirement_id": {"type": "string"},
                        # Evidence and reasoning come before the verdict: the model
                        # writes fields in this order, and a status chosen first was
                        # sometimes contradicted by the note that followed it.
                        "cv_quote": {"type": "string"},
                        "note": {"type": "string"},
                        "status": {"type": "string", "enum": list(STATUSES)},
                    }
                ),
            },
            "summary": {"type": "string"},
            "missing_information": {"type": "array", "items": {"type": "string"}},
            "model_recommendation": {"type": "string", "enum": list(RECOMMENDATIONS)},
        }
    ),
}
