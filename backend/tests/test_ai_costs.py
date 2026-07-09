"""Tests for AI usage recording, cost computation, and admin AI-cost endpoints."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import admin as admin_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import UserRole
from app.services import ai_usage

ADMIN_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def admin_user() -> SimpleNamespace:
    return SimpleNamespace(id=ADMIN_ID, role=UserRole.admin, is_active=True, email="admin@test.com")


def regular_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=UserRole.user, is_active=True, email="user@test.com")


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=json_body)


# ── Cost computation ─────────────────────────────────────────────────────────

def test_compute_cost_gpt4o() -> None:
    # 1M input + 1M output = $2.50 + $10.00
    assert ai_usage.compute_cost_usd("gpt-4o", 1_000_000, 1_000_000) == Decimal("12.50")


def test_compute_cost_gpt4o_mini() -> None:
    assert ai_usage.compute_cost_usd("gpt-4o-mini", 1_000_000, 1_000_000) == Decimal("0.75")


def test_compute_cost_typical_tailor_call() -> None:
    # ~3k prompt + ~2k completion on gpt-4o
    cost = ai_usage.compute_cost_usd("gpt-4o", 3000, 2000)
    assert cost == Decimal("0.0275")


def test_unknown_model_uses_fallback_pricing() -> None:
    assert ai_usage.compute_cost_usd("gpt-5-preview", 1000, 1000) == ai_usage.compute_cost_usd(
        "gpt-4o", 1000, 1000
    )


# ── record_ai_usage must never raise ─────────────────────────────────────────

def test_record_ai_usage_swallows_db_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_session() -> None:
        raise RuntimeError("database is down")

    monkeypatch.setattr(ai_usage, "SessionLocal", broken_session)
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50)
    # Must not raise despite the session factory blowing up
    ai_usage.record_ai_usage(purpose="tailor", model="gpt-4o", usage=usage)


def test_record_ai_usage_handles_missing_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_usage, "SessionLocal", lambda: (_ for _ in ()).throw(RuntimeError()))
    ai_usage.record_ai_usage(purpose="tailor", model="gpt-4o", usage=None)


# ── Admin endpoints ──────────────────────────────────────────────────────────

SAMPLE_SUMMARY = {
    "today": {"cost_usd": 0.5, "calls": 3, "tokens": 12000},
    "last_7_days": {"cost_usd": 4.2, "calls": 30, "tokens": 100000},
    "last_30_days": {"cost_usd": 15.0, "calls": 120, "tokens": 400000},
    "all_time": {"cost_usd": 42.0, "calls": 400, "tokens": 1200000},
    "budget": {"monthly_usd": 50.0, "month_to_date_usd": 12.5, "pct_used": 25.0},
}


@pytest.mark.asyncio
async def test_ai_costs_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_ai_costs_summary", lambda db: SAMPLE_SUMMARY)

    response = await request("GET", "/api/v1/admin/ai-costs/summary", current_user=admin_user())

    assert response.status_code == 200
    body = response.json()
    assert body["all_time"]["cost_usd"] == 42.0
    assert body["budget"]["pct_used"] == 25.0


@pytest.mark.asyncio
async def test_ai_costs_summary_requires_admin() -> None:
    response = await request("GET", "/api/v1/admin/ai-costs/summary", current_user=regular_user())
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ai_costs_daily_passes_days(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_daily(db, days):
        captured["days"] = days
        return [{"date": "2026-07-08", "cost_usd": 1.25, "calls": 10}]

    monkeypatch.setattr(admin_endpoint.crud_admin, "list_ai_costs_daily", mock_daily)

    response = await request(
        "GET", "/api/v1/admin/ai-costs/daily?days=7", current_user=admin_user()
    )

    assert response.status_code == 200
    assert captured["days"] == 7
    assert response.json()[0]["cost_usd"] == 1.25


@pytest.mark.asyncio
async def test_ai_costs_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_ai_costs_breakdown",
        lambda db, days: {
            "by_purpose": [{"key": "tailor", "cost_usd": 10.0, "calls": 50, "tokens": 300000}],
            "by_model": [{"key": "gpt-4o", "cost_usd": 10.0, "calls": 50, "tokens": 300000}],
            "top_users": [
                {"user_id": str(ADMIN_ID), "email": "u@x.com", "cost_usd": 5.0, "calls": 20}
            ],
        },
    )

    response = await request("GET", "/api/v1/admin/ai-costs/breakdown", current_user=admin_user())

    assert response.status_code == 200
    body = response.json()
    assert body["by_purpose"][0]["key"] == "tailor"
    assert body["top_users"][0]["email"] == "u@x.com"


@pytest.mark.asyncio
async def test_update_ai_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "set_ai_budget",
        lambda db, monthly_usd: captured.update(monthly_usd=monthly_usd),
    )
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_ai_costs_summary", lambda db: SAMPLE_SUMMARY)
    monkeypatch.setattr(admin_endpoint.crud_admin, "log_admin_action", lambda db, **kw: None)

    response = await request(
        "PUT",
        "/api/v1/admin/ai-costs/budget",
        current_user=admin_user(),
        json_body={"monthly_usd": 75.0},
    )

    assert response.status_code == 200
    assert captured["monthly_usd"] == 75.0


@pytest.mark.asyncio
async def test_update_ai_budget_rejects_negative() -> None:
    response = await request(
        "PUT",
        "/api/v1/admin/ai-costs/budget",
        current_user=admin_user(),
        json_body={"monthly_usd": -5},
    )
    assert response.status_code == 422
