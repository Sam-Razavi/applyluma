"""Tests for the authenticated in-app feedback endpoint."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import feedback as feedback_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

VALID_PAYLOAD = {
    "category": "bug",
    "subject": "Broken save button",
    "message": "The save button on the Discover page does nothing.",
}


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user(full_name: str | None = "Sam Svensson") -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID, email="sam@example.com", full_name=full_name, is_active=True
    )


async def post_feedback(
    payload: dict[str, Any],
    *,
    current_user: SimpleNamespace | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post("/api/v1/feedback", json=payload)


@pytest.mark.asyncio
async def test_submit_feedback_stores_and_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, Any] = {}
    emails: list[dict[str, Any]] = []

    def mock_create(db, **kwargs):
        stored.update(kwargs)
        return SimpleNamespace(id=uuid.uuid4(), **kwargs)

    monkeypatch.setattr(
        feedback_endpoint.crud_admin, "create_contact_submission", mock_create
    )
    monkeypatch.setattr(
        feedback_endpoint.email_service, "send_email", lambda **kwargs: emails.append(kwargs)
    )

    response = await post_feedback(VALID_PAYLOAD, current_user=user())

    assert response.status_code == 201
    assert response.json() == {"ok": True}
    assert stored["user_id"] == USER_ID
    assert stored["source"] == "in_app"
    assert stored["category"] == "bug"
    assert stored["name"] == "Sam Svensson"
    assert stored["email"] == "sam@example.com"
    assert stored["subject"] == "Broken save button"
    assert len(emails) == 1
    assert "[bug]" in emails[0]["subject"]


@pytest.mark.asyncio
async def test_submit_feedback_defaults_name_and_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored: dict[str, Any] = {}
    monkeypatch.setattr(
        feedback_endpoint.crud_admin,
        "create_contact_submission",
        lambda db, **kwargs: stored.update(kwargs),
    )
    monkeypatch.setattr(feedback_endpoint.email_service, "send_email", lambda **kwargs: None)

    payload = {"category": "question", "message": "How do I change my default CV?"}
    response = await post_feedback(payload, current_user=user(full_name=None))

    assert response.status_code == 201
    assert stored["name"] == "sam@example.com"
    assert stored["subject"] == "In-app feedback (question)"


@pytest.mark.asyncio
async def test_submit_feedback_requires_auth() -> None:
    response = await post_feedback(VALID_PAYLOAD)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_feedback_rejects_invalid_category() -> None:
    response = await post_feedback(
        {**VALID_PAYLOAD, "category": "rant"}, current_user=user()
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_rejects_short_message() -> None:
    response = await post_feedback(
        {**VALID_PAYLOAD, "message": "too short"}, current_user=user()
    )
    assert response.status_code == 422
