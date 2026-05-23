"""Tests for token revocation, forgot-password, and reset-password flows."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import auth as auth_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app


# ---------------------------------------------------------------------------
# Fake collaborators
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class _FakeDb:
    pass


def _fake_user(active: bool = True) -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, email="user@example.com", is_active=active)


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def exists(self, key: str) -> int:
        return 1 if key in self._store else 0

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value


class _DenylistRedis(_FakeRedis):
    """Pre-populated with one token hash already in the denylist."""

    def __init__(self, denied_key: str) -> None:
        super().__init__()
        self._store[denied_key] = "1"


class _FailingRedis:
    def exists(self, key: str) -> int:
        raise ConnectionError("Redis unavailable")

    def setex(self, key: str, ttl: int, value: str) -> None:
        raise ConnectionError("Redis unavailable")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _post(path: str, json: dict | None = None, headers: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(path, json=json or {}, headers=headers or {})


# ---------------------------------------------------------------------------
# Logout / token revocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_returns_204_and_revokes_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: fake_redis)

    from app.core.security import create_access_token
    from app.core.dependencies import get_current_user_id
    token = create_access_token(str(USER_ID))
    app.dependency_overrides[get_current_user_id] = lambda: str(USER_ID)

    response = await _post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    denylist_keys = [k for k in fake_redis._store if k.startswith("token_denylist:")]
    assert len(denylist_keys) == 1


@pytest.mark.asyncio
async def test_logout_also_revokes_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both the access token and the provided refresh token must be added to the denylist."""
    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: fake_redis)

    from app.core.security import create_access_token, create_refresh_token
    from app.core.dependencies import get_current_user_id
    access_token = create_access_token(str(USER_ID))
    refresh_token = create_refresh_token(str(USER_ID))
    app.dependency_overrides[get_current_user_id] = lambda: str(USER_ID)

    response = await _post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204
    denylist_keys = [k for k in fake_redis._store if k.startswith("token_denylist:")]
    # Both access and refresh token hashes must be stored
    assert len(denylist_keys) == 2


@pytest.mark.asyncio
async def test_refresh_rejected_after_logout(monkeypatch: pytest.MonkeyPatch) -> None:
    """/refresh must return 401 when the refresh token has been denylisted."""
    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: fake_redis)

    from app.core.security import create_access_token, create_refresh_token
    from app.core.dependencies import get_current_user_id
    access_token = create_access_token(str(USER_ID))
    refresh_token = create_refresh_token(str(USER_ID))
    app.dependency_overrides[get_current_user_id] = lambda: str(USER_ID)

    # Logout — this should denylist the refresh token
    logout_resp = await _post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 204

    # Try to use the refresh token after logout
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    refresh_resp = await _post("/api/v1/auth/refresh", {"refresh_token": refresh_token})

    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_fails_open_on_redis_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    """/refresh must not block when Redis is down — fail open."""
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: _FailingRedis())
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: _FailingRedis())

    from app.core.security import create_refresh_token
    refresh_token = create_refresh_token(str(USER_ID))
    user = _fake_user()
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: user)

    response = await _post("/api/v1/auth/refresh", {"refresh_token": refresh_token})

    # Redis down → fail open → should succeed (200) not block with 500/401
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logout_fails_open_when_redis_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: _FailingRedis())
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: _FailingRedis())

    from app.core.security import create_access_token
    from app.core.dependencies import get_current_user_id
    app.dependency_overrides[get_current_user_id] = lambda: str(USER_ID)

    token = create_access_token(str(USER_ID))
    response = await _post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should still return 204 — Redis outage must not block logout
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_always_returns_204_for_unknown_email(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: None)

    response = await _post("/api/v1/auth/forgot-password", {"email": "nobody@example.com"})

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_forgot_password_always_returns_204_for_known_email(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    user = _fake_user()
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: user)
    monkeypatch.setattr(auth_endpoint.crud_user, "create_password_reset_token", lambda db, u: "tok123")
    monkeypatch.setattr(auth_endpoint.email_service, "send_password_reset_email", lambda email, token: None)

    response = await _post("/api/v1/auth/forgot-password", {"email": user.email})

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_forgot_password_204_when_email_send_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    user = _fake_user()
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: user)
    monkeypatch.setattr(auth_endpoint.crud_user, "create_password_reset_token", lambda db, u: "tok123")

    def _bad_send(email: str, token: str) -> None:
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(auth_endpoint.email_service, "send_password_reset_email", _bad_send)

    response = await _post("/api/v1/auth/forgot-password", {"email": user.email})

    # Email failure must not propagate as an error
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_password_returns_204_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    user = _fake_user()
    monkeypatch.setattr(
        auth_endpoint.crud_user, "consume_password_reset_token", lambda db, token, pw: user
    )

    response = await _post(
        "/api/v1/auth/reset-password",
        {"token": "validtoken", "new_password": "NewSecure1!"},
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_reset_password_returns_400_for_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(
        auth_endpoint.crud_user, "consume_password_reset_token", lambda db, token, pw: None
    )

    response = await _post(
        "/api/v1/auth/reset-password",
        {"token": "badtoken", "new_password": "NewSecure1!"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_rejects_short_password(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()

    response = await _post(
        "/api/v1/auth/reset-password",
        {"token": "tok", "new_password": "short"},
    )

    assert response.status_code == 422
