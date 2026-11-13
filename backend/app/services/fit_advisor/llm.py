"""One structured-output call to the model, with usage recorded."""

from __future__ import annotations

import json
import uuid
from typing import Any

from openai import AuthenticationError, RateLimitError

from app.services import ai_usage

# A dated snapshot, not the moving "gpt-4o" alias, so every run of the
# evaluation uses the same model.
MODEL = "gpt-4o-2024-08-06"
TEMPERATURE = 0.0
SEED = 20261113
MAX_OUTPUT_TOKENS = 4096


class FitAdvisorError(Exception):
    """The assessment could not be produced (model, network or output error)."""


def call_structured(
    client: Any,
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    purpose: str,
    user_id: uuid.UUID | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return the parsed JSON object and the token usage of one call."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            seed=SEED,
            max_tokens=MAX_OUTPUT_TOKENS,
            response_format={"type": "json_schema", "json_schema": schema},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except AuthenticationError as exc:
        raise FitAdvisorError("AI service authentication failed; check OPENAI_API_KEY") from exc
    except RateLimitError as exc:
        raise FitAdvisorError("AI service rate limit exceeded, please try again later") from exc
    except Exception as exc:
        raise FitAdvisorError(f"AI API error: {exc}") from exc

    usage = getattr(response, "usage", None)
    ai_usage.record_ai_usage(purpose=purpose, model=MODEL, usage=usage, user_id=user_id)

    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise FitAdvisorError("AI response was truncated (token limit reached)")
    if getattr(choice.message, "refusal", None):
        raise FitAdvisorError(f"AI refused the request: {choice.message.refusal}")

    try:
        parsed = json.loads(choice.message.content or "")
    except json.JSONDecodeError as exc:
        raise FitAdvisorError(f"AI returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise FitAdvisorError("AI returned JSON that is not an object")

    tokens = {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
    }
    return parsed, tokens
