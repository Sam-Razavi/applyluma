"""Webhook tests.

The endpoint is publicly reachable and mutates user data, so the security cases
carry the weight here — each mirrors one from the Stripe webhook tests.
"""

from __future__ import annotations

import json
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import inbound_email as inbound_endpoint
from app.core.config import settings
from app.main import app
from app.services.inbound_email.generic import compute_signature

SECRET = "test-inbound-secret"
DOMAIN = "in.applyluma.com"
TOKEN = "a1b2c3d4e5f60718"
USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def configure(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "INBOUND_EMAIL_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(settings, "INBOUND_EMAIL_DOMAIN", DOMAIN)
    monkeypatch.setattr(settings, "INBOUND_EMAIL_VENDOR", "generic")
    monkeypatch.setattr(
        inbound_endpoint, "SessionLocal", lambda: SimpleNamespace(close=lambda: None)
    )
    yield


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(
        inbound_endpoint,
        "process_inbound_email",
        SimpleNamespace(delay=lambda payload: captured.append(payload)),
    )
    return captured


def known_user(monkeypatch: pytest.MonkeyPatch, token: str = TOKEN) -> None:
    monkeypatch.setattr(
        inbound_endpoint,
        "crud_user",
        SimpleNamespace(
            get_by_inbox_token=lambda db, t: SimpleNamespace(id=USER_ID) if t == token else None
        ),
    )


def body(**overrides: Any) -> bytes:
    payload = {
        "to": f"u-{TOKEN}@{DOMAIN}",
        "from": "Spotify Careers <careers@spotify.com>",
        "subject": "Your application to Spotify",
        "text": "Thanks for applying.",
        "message_id": "<msg-1@spotify.com>",
        "date": "Mon, 26 Aug 2026 10:00:00 +0000",
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


async def post(raw: bytes, *, signature: str | None = "auto") -> httpx.Response:
    headers = {}
    if signature == "auto":
        headers["x-applyluma-signature"] = compute_signature(raw, SECRET)
    elif signature is not None:
        headers["x-applyluma-signature"] = signature
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post("/api/v1/inbound/email", content=raw, headers=headers)


@pytest.mark.asyncio
async def test_valid_signature_is_accepted_and_enqueued(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    known_user(monkeypatch)
    response = await post(body())
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert len(enqueued) == 1
    assert enqueued[0]["user_id"] == str(USER_ID)
    assert enqueued[0]["from_domain"] == "spotify.com"


@pytest.mark.asyncio
async def test_invalid_signature_is_rejected(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    known_user(monkeypatch)
    response = await post(body(), signature="00" * 32)
    assert response.status_code == 400
    assert not enqueued


@pytest.mark.asyncio
async def test_missing_signature_header_is_rejected(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    """A missing header must be treated exactly like a wrong one."""
    known_user(monkeypatch)
    response = await post(body(), signature=None)
    assert response.status_code == 400
    assert not enqueued


@pytest.mark.asyncio
async def test_unconfigured_secret_returns_503_without_verifying(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    """An empty key makes HMAC forgeable, so refuse before the verifier runs."""
    known_user(monkeypatch)
    monkeypatch.setattr(settings, "INBOUND_EMAIL_WEBHOOK_SECRET", "")

    called = False

    def spy(*args: Any, **kwargs: Any) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(inbound_endpoint, "get_adapter", spy)

    response = await post(body())
    assert response.status_code == 503
    assert called is False
    assert not enqueued


@pytest.mark.asyncio
async def test_unknown_recipient_token_is_ignored(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    """200, not 404: it stops vendor retries and leaks nothing about tokens."""
    known_user(monkeypatch, token="some-other-token")
    response = await post(body())
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    assert not enqueued


@pytest.mark.asyncio
async def test_wrong_recipient_domain_is_ignored(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    known_user(monkeypatch)
    response = await post(body(to=f"u-{TOKEN}@someone-else.com"))
    assert response.status_code == 200
    assert not enqueued


@pytest.mark.asyncio
async def test_unparseable_payload_is_ignored_not_retried(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    """A malformed body will not become valid on redelivery, so answer 2xx."""
    known_user(monkeypatch)
    response = await post(b"not json at all")
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    assert not enqueued


@pytest.mark.asyncio
async def test_oversized_declared_body_is_refused(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    known_user(monkeypatch)
    raw = body()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/inbound/email",
            content=raw,
            headers={
                "x-applyluma-signature": compute_signature(raw, SECRET),
                "content-length": str(inbound_endpoint.MAX_BODY_BYTES + 1),
            },
        )
    assert response.status_code == 413
    assert not enqueued


@pytest.mark.asyncio
async def test_body_is_truncated_before_reaching_the_queue(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    """The broker is durable storage, so a full body must never be handed to it."""
    known_user(monkeypatch)
    response = await post(body(text="x" * 50_000))
    assert response.status_code == 202
    assert len(enqueued[0]["snippet"]) == inbound_endpoint.SNIPPET_CHARS


@pytest.mark.asyncio
async def test_mail_from_our_own_inbound_domain_is_ignored(
    monkeypatch: pytest.MonkeyPatch, enqueued: list[dict[str, Any]]
) -> None:
    """Loop guard."""
    known_user(monkeypatch)
    response = await post(body(**{"from": f"bounce@{DOMAIN}"}))
    assert response.status_code == 200
    assert not enqueued


def test_parse_inbox_token_accepts_plus_addressing() -> None:
    assert inbound_endpoint.parse_inbox_token(f"u-{TOKEN}+greenhouse@{DOMAIN}", DOMAIN) == TOKEN


def test_parse_inbox_token_rejects_other_domains_and_shapes() -> None:
    assert inbound_endpoint.parse_inbox_token(f"u-{TOKEN}@evil.com", DOMAIN) is None
    assert inbound_endpoint.parse_inbox_token(f"postmaster@{DOMAIN}", DOMAIN) is None
    assert inbound_endpoint.parse_inbox_token("", DOMAIN) is None


def test_dedupe_key_prefers_message_id_and_is_stable() -> None:
    from app.services.inbound_email.base import NormalizedEmail

    email = NormalizedEmail(recipient="x", from_address="a@b.com", subject="s")
    first = inbound_endpoint.build_dedupe_key(message_id="<m@x>", email=email)
    second = inbound_endpoint.build_dedupe_key(message_id="<M@X>", email=email)
    assert first == second

    without = inbound_endpoint.build_dedupe_key(message_id=None, email=email)
    assert without != first
