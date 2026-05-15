from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import billing as billing_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import UserRole

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CREATED_AT = datetime(2026, 5, 14, tzinfo=UTC)


class FakeDb:
    def __init__(self, user: SimpleNamespace | None = None) -> None:
        self.user = user
        self.commits = 0

    def get(self, model, value):
        if self.user and self.user.id == value:
            return self.user
        return None

    def commit(self) -> None:
        self.commits += 1


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user(**overrides: Any) -> SimpleNamespace:
    data = {
        "id": USER_ID,
        "email": "sam@example.com",
        "full_name": "Sam",
        "is_active": True,
        "is_verified": True,
        "role": UserRole.user,
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "subscription_status": None,
        "subscription_ends_at": None,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    db: FakeDb | None = None,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    if db is not None:
        app.dependency_overrides[get_db] = lambda: db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, content=content, headers=headers)


def configure_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setattr(settings, "STRIPE_PREMIUM_PRICE_ID", "price_123")


@pytest.mark.asyncio
async def test_create_checkout_session_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_stripe(monkeypatch)
    captured: dict[str, Any] = {}

    def mock_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/session")

    monkeypatch.setattr(billing_endpoint.stripe.checkout.Session, "create", mock_create)

    response = await request(
        "POST",
        "/api/v1/billing/create-checkout-session",
        current_user=user(),
    )

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "https://checkout.stripe.test/session"}
    assert captured["mode"] == "subscription"
    assert captured["line_items"][0]["price"] == "price_123"
    assert captured["metadata"] == {"user_id": str(USER_ID)}


@pytest.mark.asyncio
async def test_webhook_valid_signature_sets_user_premium(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_stripe(monkeypatch)
    db_user = user()
    fake_db = FakeDb(db_user)

    def mock_construct_event(payload, sig_header, secret):
        assert payload == b'{"ok": true}'
        assert sig_header == "sig"
        assert secret == "whsec_123"
        return {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"user_id": str(USER_ID)},
                    "customer": "cus_123",
                    "subscription": "sub_123",
                }
            },
        }

    monkeypatch.setattr(billing_endpoint.stripe.Webhook, "construct_event", mock_construct_event)

    response = await request(
        "POST",
        "/api/v1/billing/webhook",
        db=fake_db,
        content=b'{"ok": true}',
        headers={"stripe-signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert db_user.role == UserRole.premium
    assert db_user.stripe_customer_id == "cus_123"
    assert db_user.stripe_subscription_id == "sub_123"
    assert db_user.subscription_status == "active"
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_webhook_bad_signature_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_stripe(monkeypatch)

    def mock_construct_event(payload, sig_header, secret):
        raise ValueError("bad signature")

    monkeypatch.setattr(billing_endpoint.stripe.Webhook, "construct_event", mock_construct_event)

    response = await request(
        "POST",
        "/api/v1/billing/webhook",
        db=FakeDb(user()),
        content=b"{}",
        headers={"stripe-signature": "bad"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_portal_endpoint_returns_url(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_stripe(monkeypatch)
    captured: dict[str, Any] = {}

    def mock_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://billing.stripe.test/portal")

    monkeypatch.setattr(billing_endpoint.stripe.billing_portal.Session, "create", mock_create)

    response = await request(
        "GET",
        "/api/v1/billing/portal",
        current_user=user(stripe_customer_id="cus_123"),
    )

    assert response.status_code == 200
    assert response.json() == {"portal_url": "https://billing.stripe.test/portal"}
    assert captured["customer"] == "cus_123"
