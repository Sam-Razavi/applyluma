from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import contact as contact_endpoint
from app.core.dependencies import get_db
from app.main import app

VALID_PAYLOAD = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "subject": "Question about pricing",
    "message": "Hello, I have a question about your premium plan.",
    "turnstile_token": "test-token",
    "honeypot": "",
}


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def post_contact(payload: dict[str, Any]) -> httpx.Response:
    app.dependency_overrides[get_db] = lambda: None
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post("/api/v1/contact", json=payload)


@pytest.mark.asyncio
async def test_submit_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(contact_endpoint.email_service, "send_email", lambda **kwargs: None)
    response = await post_contact(VALID_PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_submit_honeypot_filled() -> None:
    payload = {**VALID_PAYLOAD, "honeypot": "spam-bot-filled-this"}
    response = await post_contact(payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_missing_name() -> None:
    payload = {**VALID_PAYLOAD, "name": ""}
    response = await post_contact(payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_missing_message() -> None:
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "message"}
    response = await post_contact(payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_short_message() -> None:
    payload = {**VALID_PAYLOAD, "message": "Hi"}
    response = await post_contact(payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_invalid_email() -> None:
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    response = await post_contact(payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_sends_two_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def capture_send(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(contact_endpoint.email_service, "send_email", capture_send)
    response = await post_contact(VALID_PAYLOAD)
    assert response.status_code == 200
    assert len(calls) == 2
    assert calls[0]["to_email"] == "sam@samincodes.com"
    assert "[ApplyLuma Contact]" in calls[0]["subject"]
    assert calls[1]["to_email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_submit_without_subject_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        contact_endpoint.email_service, "send_email", lambda **kwargs: calls.append(kwargs)
    )
    payload = {**VALID_PAYLOAD, "subject": ""}
    response = await post_contact(payload)
    assert response.status_code == 200
    assert "No subject" in calls[0]["subject"]
