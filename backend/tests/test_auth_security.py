"""Tests for token revocation, refresh edge cases, forgot-password, and reset-password flows."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from jose import jwt

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

    def set(self, key: str, value: str, **kwargs) -> None:
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

    def set(self, key: str, value: str, **kwargs) -> None:
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
# Login tracking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_records_login_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    user = _fake_user()
    monkeypatch.setattr(auth_endpoint.crud_user, "authenticate", lambda db, email, pw: user)
    recorded: list[SimpleNamespace] = []
    monkeypatch.setattr(auth_endpoint.crud_user, "record_login", lambda db, u: recorded.append(u))

    response = await _post("/api/v1/auth/login", {"email": user.email, "password": "pw"})

    assert response.status_code == 200
    assert recorded == [user]


@pytest.mark.asyncio
async def test_login_does_not_record_login_on_bad_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(auth_endpoint.crud_user, "authenticate", lambda db, email, pw: None)
    recorded: list[SimpleNamespace] = []
    monkeypatch.setattr(auth_endpoint.crud_user, "record_login", lambda db, u: recorded.append(u))

    response = await _post("/api/v1/auth/login", {"email": "nobody@example.com", "password": "pw"})

    assert response.status_code == 401
    assert recorded == []


@pytest.mark.asyncio
async def test_login_does_not_record_login_for_inactive_user(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    user = _fake_user(active=False)
    monkeypatch.setattr(auth_endpoint.crud_user, "authenticate", lambda db, email, pw: user)
    recorded: list[SimpleNamespace] = []
    monkeypatch.setattr(auth_endpoint.crud_user, "record_login", lambda db, u: recorded.append(u))

    response = await _post("/api/v1/auth/login", {"email": user.email, "password": "pw"})

    assert response.status_code == 400
    assert recorded == []


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


# ---------------------------------------------------------------------------
# Refresh endpoint edge cases
# ---------------------------------------------------------------------------

def _make_expired_refresh_token() -> str:
    """Build a syntactically valid refresh JWT whose exp is in the past."""
    from app.core.config import settings
    return jwt.encode(
        {"exp": datetime.now(UTC) - timedelta(seconds=1), "sub": str(USER_ID), "type": "refresh"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_refresh_rejects_malformed_token() -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()

    response = await _post("/api/v1/auth/refresh", {"refresh_token": "not.a.jwt"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token() -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    expired = _make_expired_refresh_token()

    response = await _post("/api/v1/auth/refresh", {"refresh_token": expired})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_access_token() -> None:
    """Passing an access token to the refresh endpoint must be rejected."""
    from app.core.security import create_access_token
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    access_token = create_access_token(str(USER_ID))

    response = await _post("/api/v1/auth/refresh", {"refresh_token": access_token})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_when_user_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid refresh token for a deleted user must return 401."""
    from app.core.security import create_refresh_token
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: _FakeRedis())
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: _FakeRedis())
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: None)
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    token = create_refresh_token(str(USER_ID))

    response = await _post("/api/v1/auth/refresh", {"refresh_token": token})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_when_user_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid refresh token for a deactivated user must return 401."""
    from app.core.security import create_refresh_token
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: _FakeRedis())
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: _FakeRedis())
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: _fake_user(active=False))
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    token = create_refresh_token(str(USER_ID))

    response = await _post("/api/v1/auth/refresh", {"refresh_token": token})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Register endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: _fake_user())

    response = await _post(
        "/api/v1/auth/register",
        {"email": "existing@example.com", "password": "SecurePass1!", "full_name": "Test User"},
    )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Account deletion (GDPR right to erasure)
# ---------------------------------------------------------------------------

def test_delete_user_removes_files_on_disk(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """crud_user.delete must erase the user's cvs/ and cover_letters/ subtrees."""
    from unittest.mock import Mock

    from app.crud import user as crud_user

    monkeypatch.setattr("app.crud.user.settings.STORAGE_DIR", str(tmp_path))
    cv_dir = tmp_path / "cvs" / str(USER_ID)
    cl_dir = tmp_path / "cover_letters" / str(USER_ID)
    cv_dir.mkdir(parents=True)
    cl_dir.mkdir(parents=True)
    (cv_dir / "resume.pdf").write_bytes(b"pdf")
    (cl_dir / "letter.pdf").write_bytes(b"pdf")
    # Another user's files must survive
    other_dir = tmp_path / "cvs" / "other-user"
    other_dir.mkdir(parents=True)
    (other_dir / "resume.pdf").write_bytes(b"pdf")

    db = Mock()
    user = _fake_user()
    crud_user.delete(db, user)

    db.delete.assert_called_once_with(user)
    db.commit.assert_called_once()
    assert not cv_dir.exists()
    assert not cl_dir.exists()
    assert (other_dir / "resume.pdf").exists()


def test_delete_user_succeeds_when_file_cleanup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A disk error during file cleanup must not propagate — DB deletion already committed."""
    from unittest.mock import Mock

    from app.crud import user as crud_user

    def _bad_rmtree(*args, **kwargs):
        raise OSError("disk error")

    monkeypatch.setattr("app.crud.user.shutil.rmtree", _bad_rmtree)

    db = Mock()
    user = _fake_user()
    crud_user.delete(db, user)  # must not raise

    db.delete.assert_called_once_with(user)
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Cookie-based refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_accepts_token_from_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh endpoint uses the refresh_token cookie when the body token is absent."""
    from app.core.security import create_refresh_token

    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.core.dependencies.get_redis_client", lambda: fake_redis)

    user = _fake_user()
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: user)

    refresh_token = create_refresh_token(str(USER_ID))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={},  # no refresh_token in body
            cookies={"refresh_token": refresh_token},
        )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
