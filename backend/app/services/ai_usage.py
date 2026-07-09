"""AI usage recording and cost computation.

One `record_ai_usage` call per OpenAI request. Recording must never break the
AI feature that triggered it: every failure is swallowed and logged. The
function opens its own short-lived DB session so call sites don't need to
thread a session through service layers.

Budget alerts: when the admin has set a monthly budget (app_settings key
`ai_budget_monthly_usd`), crossing 80% or 100% of it sends one email per
threshold per month to CONTACT_RECIPIENT_EMAIL (throttled via the
`ai_budget_alert_state` setting, value format "YYYY-MM:<level>").
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ai_usage_log import AIUsageLog, AppSetting

logger = logging.getLogger(__name__)

BUDGET_SETTING_KEY = "ai_budget_monthly_usd"
BUDGET_ALERT_STATE_KEY = "ai_budget_alert_state"

# (input, output) USD per 1M tokens. Update here when OpenAI prices change.
PRICES_PER_MTOK: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
}
# Unknown models are priced like gpt-4o so costs are overestimated, not hidden.
_FALLBACK_PRICE = PRICES_PER_MTOK["gpt-4o"]

_MTOK = Decimal(1_000_000)


def compute_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    input_price, output_price = PRICES_PER_MTOK.get(model, _FALLBACK_PRICE)
    cost = (Decimal(prompt_tokens) * input_price + Decimal(completion_tokens) * output_price) / _MTOK
    return cost.quantize(Decimal("0.000001"))


def record_ai_usage(
    *,
    purpose: str,
    model: str,
    usage: Any,
    user_id: uuid.UUID | None = None,
) -> None:
    """Persist one usage row. Never raises; `usage` is `response.usage`."""
    if usage is None:
        return
    try:
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        cost = compute_cost_usd(model, prompt_tokens, completion_tokens)

        with SessionLocal() as db:
            db.add(
                AIUsageLog(
                    user_id=user_id,
                    purpose=purpose,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                )
            )
            db.commit()
            _check_budget_alert(db)
    except Exception:
        logger.exception("Failed to record AI usage (purpose=%s model=%s)", purpose, model)


def get_setting(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row else None


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


def month_to_date_cost(db: Session) -> Decimal:
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(
        select(func.coalesce(func.sum(AIUsageLog.cost_usd), 0)).where(
            AIUsageLog.created_at >= month_start
        )
    )
    return Decimal(total or 0)


def _check_budget_alert(db: Session) -> None:
    raw_budget = get_setting(db, BUDGET_SETTING_KEY)
    if not raw_budget:
        return
    try:
        budget = Decimal(raw_budget)
    except Exception:
        return
    if budget <= 0:
        return

    spend = month_to_date_cost(db)
    pct = spend / budget
    level = 100 if pct >= 1 else 80 if pct >= Decimal("0.8") else 0
    if level == 0:
        return

    month = datetime.now(UTC).strftime("%Y-%m")
    state = get_setting(db, BUDGET_ALERT_STATE_KEY) or ""
    already_alerted = 0
    if state.startswith(f"{month}:"):
        try:
            already_alerted = int(state.split(":", 1)[1])
        except ValueError:
            already_alerted = 0
    if level <= already_alerted:
        return

    set_setting(db, BUDGET_ALERT_STATE_KEY, f"{month}:{level}")

    from app.services import email_service  # late import to avoid cycles

    email_service.send_email(
        to_email=settings.CONTACT_RECIPIENT_EMAIL,
        subject=f"[ApplyLuma] AI budget alert: {level}% of monthly budget used",
        html_body=(
            f"<p>AI spending this month is <strong>${spend:.2f}</strong> of the "
            f"<strong>${budget:.2f}</strong> budget ({pct * 100:.0f}%).</p>"
            f"<p>Review usage at applyluma.com/admin/ai-costs.</p>"
        ),
    )
