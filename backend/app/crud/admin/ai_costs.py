"""Admin AI cost reporting and the monthly budget."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_usage_log import AIUsageLog
from app.models.user import User


def _ai_cost_window(db: Session, since: datetime | None) -> dict[str, Any]:
    q = select(
        func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
        func.count().label("calls"),
        func.coalesce(
            func.sum(AIUsageLog.prompt_tokens + AIUsageLog.completion_tokens), 0
        ).label("tokens"),
    )
    if since is not None:
        q = q.where(AIUsageLog.created_at >= since)
    row = db.execute(q).one()
    return {"cost_usd": float(row.cost), "calls": int(row.calls), "tokens": int(row.tokens)}


def get_ai_costs_summary(db: Session) -> dict[str, Any]:
    from app.services import ai_usage

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    budget_raw = ai_usage.get_setting(db, ai_usage.BUDGET_SETTING_KEY)
    monthly_budget = float(budget_raw) if budget_raw else None
    mtd = float(ai_usage.month_to_date_cost(db))

    return {
        "today": _ai_cost_window(db, today_start),
        "last_7_days": _ai_cost_window(db, now - timedelta(days=7)),
        "last_30_days": _ai_cost_window(db, now - timedelta(days=30)),
        "all_time": _ai_cost_window(db, None),
        "budget": {
            "monthly_usd": monthly_budget,
            "month_to_date_usd": mtd,
            "pct_used": round(mtd / monthly_budget * 100, 1) if monthly_budget else None,
        },
    }


def list_ai_costs_daily(db: Session, days: int = 30) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=days)
    day = func.date_trunc("day", AIUsageLog.created_at).label("day")
    rows = db.execute(
        select(
            day,
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
            func.count().label("calls"),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(day)
        .order_by(day)
    ).all()
    return [
        {"date": row.day.date().isoformat(), "cost_usd": float(row.cost), "calls": int(row.calls)}
        for row in rows
    ]


def get_ai_costs_breakdown(db: Session, days: int = 30) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)

    def grouped(column: Any) -> list[dict[str, Any]]:
        rows = db.execute(
            select(
                column.label("key"),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
                func.count().label("calls"),
                func.coalesce(
                    func.sum(AIUsageLog.prompt_tokens + AIUsageLog.completion_tokens), 0
                ).label("tokens"),
            )
            .where(AIUsageLog.created_at >= since)
            .group_by(column)
            .order_by(func.sum(AIUsageLog.cost_usd).desc())
        ).all()
        return [
            {
                "key": str(row.key),
                "cost_usd": float(row.cost),
                "calls": int(row.calls),
                "tokens": int(row.tokens),
            }
            for row in rows
        ]

    user_rows = db.execute(
        select(
            AIUsageLog.user_id,
            User.email,
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
            func.count().label("calls"),
        )
        .outerjoin(User, User.id == AIUsageLog.user_id)
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.user_id, User.email)
        .order_by(func.sum(AIUsageLog.cost_usd).desc())
        .limit(10)
    ).all()

    return {
        "by_purpose": grouped(AIUsageLog.purpose),
        "by_model": grouped(AIUsageLog.model),
        "top_users": [
            {
                "user_id": row.user_id,
                "email": row.email,
                "cost_usd": float(row.cost),
                "calls": int(row.calls),
            }
            for row in user_rows
        ],
    }


def set_ai_budget(db: Session, monthly_usd: float | None) -> None:
    from app.services import ai_usage

    value = "" if monthly_usd is None else str(monthly_usd)
    ai_usage.set_setting(db, ai_usage.BUDGET_SETTING_KEY, value)
