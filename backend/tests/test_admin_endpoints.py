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

from app.api.v1.endpoints import admin as admin_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import UserRole

ADMIN_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

SAMPLE_STATS = {
    "total_users": 42,
    "premium_users": 5,
    "admin_users": 1,
    "new_users_this_week": 3,
    "total_cvs": 30,
    "total_job_descriptions": 20,
    "total_applications": 60,
    "total_tailor_jobs": 15,
    "tailor_jobs_complete": 10,
    "tailor_jobs_failed": 2,
    "tailor_jobs_pending": 3,
    "total_cover_letters": 8,
}


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[Any] = []

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: Any) -> None:
        self.refreshed.append(value)


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def admin_user() -> SimpleNamespace:
    return SimpleNamespace(id=ADMIN_ID, role=UserRole.admin, is_active=True, email="admin@test.com")


def regular_user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, role=UserRole.user, is_active=True, email="user@test.com")


def sample_user(
    user_id: uuid.UUID = USER_ID,
    role: UserRole = UserRole.user,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="user@test.com",
        full_name="Test User",
        role=role,
        is_active=True,
        is_verified=False,
        subscription_status=None,
        created_at=CREATED_AT,
    )


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    json_body: dict[str, Any] | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=json_body)


# ── Auth/role guard tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_requires_auth() -> None:
    response = await request("GET", "/api/v1/admin/stats")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stats_requires_admin_role() -> None:
    response = await request("GET", "/api/v1/admin/stats", current_user=regular_user())
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_users_requires_admin_role() -> None:
    response = await request("GET", "/api/v1/admin/users", current_user=regular_user())
    assert response.status_code == 403


# ── Stats endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_overview_stats", lambda db: SAMPLE_STATS)

    response = await request("GET", "/api/v1/admin/stats", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 42
    assert data["premium_users"] == 5
    assert data["admin_users"] == 1
    assert data["new_users_this_week"] == 3
    assert data["total_tailor_jobs"] == 15
    assert data["tailor_jobs_complete"] == 10
    assert data["total_cover_letters"] == 8


# ── User list endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_returns_paginated_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    users = [sample_user() for _ in range(3)]
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "list_users", lambda db, **kwargs: (users, 47)
    )

    response = await request("GET", "/api/v1/admin/users", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 47
    assert data["size"] == 25
    assert data["page"] == 1
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_users_passes_search_to_crud(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list(db: Any, **kwargs: Any) -> tuple[list, int]:
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(admin_endpoint.crud_admin, "list_users", fake_list)
    await request("GET", "/api/v1/admin/users?search=alice&role=premium", current_user=admin_user())

    assert captured.get("search") == "alice"
    assert captured.get("role") == UserRole.premium


# ── Get single user ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_returns_404_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)

    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_returns_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )

    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"


# ── Role update ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_role_rejects_self_change(monkeypatch: pytest.MonkeyPatch) -> None:
    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{ADMIN_ID}/role",
        current_user=admin_user(),
        json_body={"role": "user"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_role_returns_404_for_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/role",
        current_user=admin_user(),
        json_body={"role": "premium"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_role_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_set_role(db: Any, user: Any, role: UserRole) -> Any:
        user.role = role
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_role", fake_set_role)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/role",
        current_user=admin_user(),
        json_body={"role": "premium"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "premium"


# ── Active update ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_active_rejects_self_disable() -> None:
    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{ADMIN_ID}/active",
        current_user=admin_user(),
        json_body={"is_active": False},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_active_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_set_active(db: Any, user: Any, is_active: bool) -> Any:
        user.is_active = is_active
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_active", fake_set_active)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/active",
        current_user=admin_user(),
        json_body={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# ── Notify user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notify_returns_404_for_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Hello", "body": "Message"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_notify_creates_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    calls: list[dict[str, Any]] = []

    def fake_notify(db: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(admin_endpoint.notification_service, "create_notification", fake_notify)

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Hi there", "body": "Admin says hello", "type": "admin_message"},
    )
    assert response.status_code == 204
    assert len(calls) == 1
    assert calls[0]["title"] == "Hi there"
    assert calls[0]["body"] == "Admin says hello"
    assert calls[0]["type"] == "admin_message"


@pytest.mark.asyncio
async def test_notify_rejects_invalid_notification_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """NotificationType Literal must reject unknown type strings with 422."""
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Hi", "body": "Bad type", "type": "hacked"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_role_emits_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing a user's role must emit a logger.warning with audit fields."""
    import logging

    target = sample_user(role=UserRole.user)
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_set_role(db: Any, user: Any, role: UserRole) -> Any:
        user.role = role
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_role", fake_set_role)

    log_records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(record)

    handler = _Capture()
    admin_endpoint.logger.addHandler(handler)
    try:
        response = await request(
            "PATCH",
            f"/api/v1/admin/users/{USER_ID}/role",
            current_user=admin_user(),
            json_body={"role": "premium"},
        )
    finally:
        admin_endpoint.logger.removeHandler(handler)

    assert response.status_code == 200
    assert any(r.getMessage() == "admin_role_changed" for r in log_records), (
        "Expected 'admin_role_changed' log record"
    )
