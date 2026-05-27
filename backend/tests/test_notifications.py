from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import notifications as notifications_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.services import email_service
from app.tasks import notifications as notification_tasks

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NOTIFICATION_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
APPLICATION_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CREATED_AT = datetime(2026, 5, 14, tzinfo=UTC)


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, email="sam@example.com", is_active=True)


def notification_data(**overrides: Any) -> SimpleNamespace:
    data = {
        "id": NOTIFICATION_ID,
        "user_id": USER_ID,
        "type": "tailor_complete",
        "title": "Your tailored CV is ready",
        "body": "Your AI-tailored CV has finished processing.",
        "related_id": APPLICATION_ID,
        "related_type": "tailor_job",
        "is_read": False,
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
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_list_notifications_returns_paginated_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get_for_user(db, user_id, skip, limit):
        assert user_id == USER_ID
        assert skip == 5
        assert limit == 10
        return [notification_data()], 25, 3

    monkeypatch.setattr(notifications_endpoint.crud_notification, "get_for_user", mock_get_for_user)

    response = await request(
        "GET",
        "/api/v1/notifications?skip=5&limit=10",
        current_user=user(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 25
    assert body["unread_count"] == 3
    assert body["skip"] == 5
    assert body["limit"] == 10
    assert body["items"][0]["id"] == str(NOTIFICATION_ID)


@pytest.mark.asyncio
async def test_mark_read_sets_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_mark_read(db, notification_id, user_id):
        assert notification_id == NOTIFICATION_ID
        assert user_id == USER_ID
        return notification_data(is_read=True)

    monkeypatch.setattr(notifications_endpoint.crud_notification, "mark_read", mock_mark_read)

    response = await request(
        "PATCH",
        f"/api/v1/notifications/{NOTIFICATION_ID}/read",
        current_user=user(),
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True


@pytest.mark.asyncio
async def test_mark_all_read_clears_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        notifications_endpoint.crud_notification,
        "mark_all_read",
        lambda db, user_id: 4,
    )

    response = await request(
        "POST",
        "/api/v1/notifications/mark-all-read",
        current_user=user(),
    )

    assert response.status_code == 200
    assert response.json() == {"updated": 4}


def test_stale_application_task_creates_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    stale_application = SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        company_name="Spotify",
        applied_date=datetime.now(UTC) - timedelta(days=8),
        user=SimpleNamespace(email="sam@example.com"),
    )

    class FakeQuery:
        def filter(self, *args):
            return self

        def all(self):
            return [stale_application]

    class TaskDb:
        def query(self, model):
            return FakeQuery()

        def close(self):
            pass

    created: list[dict[str, Any]] = []

    def mock_create_notification(db, **kwargs):
        created.append(kwargs)
        return notification_data()

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: TaskDb())
    monkeypatch.setattr(
        notification_tasks.notification_service,
        "create_notification",
        mock_create_notification,
    )

    result = notification_tasks.check_stale_applications.run()

    assert result == {"created": 1}
    assert created[0]["type"] == "application_stale"
    assert created[0]["user_id"] == USER_ID
    assert created[0]["related_id"] == APPLICATION_ID
    assert created[0]["send_email"] is True


def test_email_service_is_noop_when_sendgrid_key_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "")
    email_service.send_email("sam@example.com", "Subject", "<p>Body</p>")
