"""Admin user-control endpoints: activity timeline, delete, password reset,
verify, tailor-limit override, and database stats."""
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
    *,
    is_verified: bool = False,
    hashed_password: str | None = "hashed",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="user@test.com",
        full_name="Test User",
        role=role,
        is_active=True,
        is_verified=is_verified,
        verification_token=None,
        hashed_password=hashed_password,
        subscription_status=None,
        created_at=CREATED_AT,
        last_login_at=None,
        login_count=0,
        daily_tailor_limit_override=None,
    )


def sample_profile(**overrides: Any) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "id": USER_ID,
        "email": "user@test.com",
        "full_name": "Test User",
        "role": UserRole.user,
        "is_active": True,
        "is_verified": False,
        "subscription_status": None,
        "created_at": CREATED_AT,
        "last_login_at": None,
        "login_count": 0,
        "auth_provider": "local",
        "avatar_url": None,
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "subscription_ends_at": None,
        "updated_at": CREATED_AT,
        "daily_tailor_limit_override": None,
        "activity": {
            "cvs": 2,
            "tailored_cvs": 1,
            "job_descriptions": 3,
            "applications": 4,
            "saved_jobs": 5,
            "tailor_jobs": 6,
            "tailor_jobs_failed": 1,
            "cover_letters": 2,
            "cover_letters_failed": 0,
            "notifications": 7,
            "unread_notifications": 2,
        },
        "ai_costs": {"last_30_days_usd": 0.5, "all_time_usd": 1.25, "all_time_calls": 7},
    }
    profile.update(overrides)
    return profile


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


# ── Activity timeline ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_activity_requires_auth() -> None:
    response = await request("GET", f"/api/v1/admin/users/{USER_ID}/activity")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_activity_requires_admin_role() -> None:
    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}/activity", current_user=regular_user()
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_activity_404_for_unknown_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)
    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}/activity", current_user=admin_user()
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_activity_returns_paginated_events(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        {
            "type": "cv_uploaded",
            "title": "My CV",
            "status": None,
            "timestamp": CREATED_AT,
            "ref_id": uuid.uuid4(),
        },
        {
            "type": "application_created",
            "title": "Engineer @ Acme",
            "status": "applied",
            "timestamp": CREATED_AT,
            "ref_id": uuid.uuid4(),
        },
    ]
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )
    captured: dict[str, Any] = {}

    def fake_activity(db: Any, user_id: uuid.UUID, *, page: int, size: int) -> tuple[list, int]:
        captured.update({"user_id": user_id, "page": page, "size": size})
        return events, 12

    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_activity", fake_activity)

    response = await request(
        "GET",
        f"/api/v1/admin/users/{USER_ID}/activity?page=2&size=10",
        current_user=admin_user(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 12
    assert data["page"] == 2
    assert data["size"] == 10
    assert [e["type"] for e in data["items"]] == ["cv_uploaded", "application_created"]
    assert captured == {"user_id": USER_ID, "page": 2, "size": 10}


# ── Send single-user notification ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_notification_writes_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )
    monkeypatch.setattr(
        admin_endpoint.notification_service, "create_notification", lambda db, **kwargs: None
    )
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "log_admin_action",
        lambda db, **kwargs: audits.append(kwargs),
    )

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Heads up", "body": "Your CV was reviewed."},
    )

    assert response.status_code == 204
    assert len(audits) == 1
    assert audits[0]["action"] == "user.notified"
    assert audits[0]["target_user_id"] == USER_ID


# ── Delete user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_user_requires_admin_role() -> None:
    response = await request(
        "DELETE", f"/api/v1/admin/users/{USER_ID}", current_user=regular_user()
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_blocks_self() -> None:
    response = await request(
        "DELETE", f"/api/v1/admin/users/{ADMIN_ID}", current_user=admin_user()
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_user_blocks_other_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    other_admin = sample_user(role=UserRole.admin)
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: other_admin
    )
    response = await request(
        "DELETE", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )
    assert response.status_code == 400
    assert "demote" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_user_404_for_unknown_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)
    response = await request(
        "DELETE", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_deletes_and_audits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )
    deleted: list[uuid.UUID] = []
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "delete_user_admin",
        lambda db, uid: deleted.append(uid) or True,
    )
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "log_admin_action",
        lambda db, **kwargs: audits.append(kwargs),
    )

    response = await request(
        "DELETE", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )

    assert response.status_code == 204
    assert deleted == [USER_ID]
    assert audits[0]["action"] == "user.deleted"
    assert audits[0]["details"]["email"] == "user@test.com"
    assert audits[0]["details"]["deleted_user_id"] == str(USER_ID)


# ── Password reset ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_password_reset_sends_email_and_audits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )
    monkeypatch.setattr(
        admin_endpoint.crud_user, "create_password_reset_token", lambda db, user: "tok-123"
    )
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        admin_endpoint.email_service,
        "send_password_reset_email",
        lambda email, token: sent.append((email, token)),
    )
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "log_admin_action",
        lambda db, **kwargs: audits.append(kwargs),
    )

    response = await request(
        "POST", f"/api/v1/admin/users/{USER_ID}/password-reset", current_user=admin_user()
    )

    assert response.status_code == 204
    assert sent == [("user@test.com", "tok-123")]
    assert audits[0]["action"] == "user.password_reset_sent"


@pytest.mark.asyncio
async def test_password_reset_rejects_google_only_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_user_by_id_admin",
        lambda db, uid: sample_user(hashed_password=None),
    )
    response = await request(
        "POST", f"/api/v1/admin/users/{USER_ID}/password-reset", current_user=admin_user()
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_password_reset_502_when_email_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )
    monkeypatch.setattr(
        admin_endpoint.crud_user, "create_password_reset_token", lambda db, user: "tok-123"
    )

    def boom(email: str, token: str) -> None:
        raise RuntimeError("smtp down")

    monkeypatch.setattr(admin_endpoint.email_service, "send_password_reset_email", boom)

    response = await request(
        "POST", f"/api/v1/admin/users/{USER_ID}/password-reset", current_user=admin_user()
    )
    assert response.status_code == 502


# ── Verify user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_user_sets_flag_and_audits(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_verify(db: Any, user: SimpleNamespace) -> SimpleNamespace:
        user.is_verified = True
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_verified", fake_verify)
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "log_admin_action",
        lambda db, **kwargs: audits.append(kwargs),
    )

    response = await request(
        "PATCH", f"/api/v1/admin/users/{USER_ID}/verify", current_user=admin_user()
    )

    assert response.status_code == 200
    assert response.json()["is_verified"] is True
    assert audits[0]["action"] == "user.verified"


@pytest.mark.asyncio
async def test_verify_user_idempotent_when_already_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_user_by_id_admin",
        lambda db, uid: sample_user(is_verified=True),
    )
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "log_admin_action",
        lambda db, **kwargs: audits.append(kwargs),
    )

    response = await request(
        "PATCH", f"/api/v1/admin/users/{USER_ID}/verify", current_user=admin_user()
    )

    assert response.status_code == 200
    assert response.json()["is_verified"] is True
    assert audits == []


# ── Tailor-limit override ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_limits_sets_override(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)
    captured: dict[str, Any] = {}

    def fake_set(db: Any, user: SimpleNamespace, value: int | None) -> SimpleNamespace:
        captured["value"] = value
        user.daily_tailor_limit_override = value
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_tailor_limit_override", fake_set)
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_user_profile_admin",
        lambda db, uid: sample_profile(daily_tailor_limit_override=5),
    )
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "log_admin_action",
        lambda db, **kwargs: audits.append(kwargs),
    )

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/limits",
        current_user=admin_user(),
        json_body={"daily_tailor_limit_override": 5},
    )

    assert response.status_code == 200
    assert captured["value"] == 5
    assert response.json()["daily_tailor_limit_override"] == 5
    assert audits[0]["action"] == "user.limits_changed"
    assert audits[0]["details"]["new_daily_tailor_limit_override"] == 5


@pytest.mark.asyncio
async def test_update_limits_clears_override(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    target.daily_tailor_limit_override = 5
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)
    captured: dict[str, Any] = {}

    def fake_set(db: Any, user: SimpleNamespace, value: int | None) -> SimpleNamespace:
        captured["value"] = value
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_tailor_limit_override", fake_set)
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_profile_admin", lambda db, uid: sample_profile()
    )
    monkeypatch.setattr(admin_endpoint.crud_admin, "log_admin_action", lambda db, **kwargs: None)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/limits",
        current_user=admin_user(),
        json_body={"daily_tailor_limit_override": None},
    )

    assert response.status_code == 200
    assert captured["value"] is None
    assert response.json()["daily_tailor_limit_override"] is None


@pytest.mark.asyncio
async def test_update_limits_rejects_negative() -> None:
    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/limits",
        current_user=admin_user(),
        json_body={"daily_tailor_limit_override": -1},
    )
    assert response.status_code == 422


# ── Profile includes new fields ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_profile_includes_ai_costs_and_login_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_user_profile_admin",
        lambda db, uid: sample_profile(login_count=3, last_login_at=CREATED_AT),
    )

    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}/profile", current_user=admin_user()
    )

    assert response.status_code == 200
    data = response.json()
    assert data["login_count"] == 3
    assert data["last_login_at"] is not None
    assert data["ai_costs"] == {
        "last_30_days_usd": 0.5,
        "all_time_usd": 1.25,
        "all_time_calls": 7,
    }
    assert data["daily_tailor_limit_override"] is None


# ── Database stats ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_database_stats_requires_admin_role() -> None:
    response = await request(
        "GET", "/api/v1/admin/database/stats", current_user=regular_user()
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_database_stats_returns_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_database_stats",
        lambda db: {
            "database_size_bytes": 123456789,
            "generated_at": CREATED_AT,
            "tables": [
                {
                    "table_name": "raw_job_postings",
                    "approx_row_count": 810,
                    "total_bytes": 9000000,
                    "rows_7d": 70,
                    "rows_30d": 300,
                },
                {
                    "table_name": "alembic_version",
                    "approx_row_count": 1,
                    "total_bytes": 8192,
                    "rows_7d": None,
                    "rows_30d": None,
                },
            ],
        },
    )

    response = await request("GET", "/api/v1/admin/database/stats", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["database_size_bytes"] == 123456789
    assert data["tables"][0]["table_name"] == "raw_job_postings"
    assert data["tables"][0]["rows_7d"] == 70
    assert data["tables"][1]["rows_7d"] is None


# ── crud_admin.delete_user_admin: real CRUD, not the endpoint mock ────────────

class _FakeExecuteResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeCoreDb:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount
        self.committed = False

    def execute(self, _stmt: Any) -> _FakeExecuteResult:
        return _FakeExecuteResult(self.rowcount)

    def commit(self) -> None:
        self.committed = True


def test_delete_user_admin_erases_files_same_as_self_service_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin-initiated delete must trigger the same GDPR file erasure as
    crud_user.delete (self-service account deletion) — it bypasses the ORM
    with a Core DELETE for the DB row, so file cleanup needs an explicit call."""
    from app.crud import admin as crud_admin_module

    erased: list[str] = []
    monkeypatch.setattr(
        "app.crud.user._remove_user_files", lambda user_id: erased.append(user_id)
    )

    db = _FakeCoreDb(rowcount=1)
    result = crud_admin_module.delete_user_admin(db, USER_ID)

    assert result is True
    assert db.committed is True
    assert erased == [str(USER_ID)]


def test_delete_user_admin_skips_file_erasure_when_user_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.crud import admin as crud_admin_module

    erased: list[str] = []
    monkeypatch.setattr(
        "app.crud.user._remove_user_files", lambda user_id: erased.append(user_id)
    )

    db = _FakeCoreDb(rowcount=0)
    result = crud_admin_module.delete_user_admin(db, USER_ID)

    assert result is False
    assert erased == []
