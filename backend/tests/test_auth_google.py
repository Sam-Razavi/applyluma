"""Tests for Google OAuth: login redirect, callback flow, and user upsert."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import auth_google, oauth_common
from app.core.config import settings
from app.core.dependencies import get_db
from app.crud import user as crud_user
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeDb:
    """No-op stand-in for a SQLAlchemy session."""

    def add(self, _obj: object) -> None:  # pragma: no cover - trivial
        pass

    def commit(self) -> None:  # pragma: no cover - trivial
        pass

    def refresh(self, _obj: object) -> None:  # pragma: no cover - trivial
        pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def _get(path: str, *, cookies: dict | None = None) -> httpx.Response:
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        cookies=cookies or {},
    ) as client:
        return await client.get(path)


# ------------------------------------------------------------------
# GET /api/v1/auth/google/login
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_redirects_to_google(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id")
    resp = await _get("/api/v1/auth/google/login")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith(auth_google.GOOGLE_AUTH_URL)
    assert "oauth_state" in resp.cookies


@pytest.mark.asyncio
async def test_login_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    resp = await _get("/api/v1/auth/google/login")
    assert resp.status_code == 501


# ------------------------------------------------------------------
# GET /api/v1/auth/google/callback
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_callback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_google, "_exchange_code_for_tokens", lambda code: {"access_token": "ga"})
    monkeypatch.setattr(
        auth_google,
        "_fetch_google_user_info",
        lambda tok: {"id": "g123", "email": "x@example.com", "name": "X", "picture": "http://p"},
    )
    logged_in_user = SimpleNamespace(id=USER_ID)
    monkeypatch.setattr(
        auth_google.crud_user, "upsert_google_user", lambda *a, **kw: logged_in_user
    )
    recorded: list[SimpleNamespace] = []
    monkeypatch.setattr(
        auth_google.crud_user, "record_login", lambda db, u: recorded.append(u)
    )
    resp = await _get("/api/v1/auth/google/callback?code=abc&state=s", cookies={"oauth_state": "s"})
    assert resp.status_code == 302
    assert "/auth/callback#token=" in resp.headers["location"]
    assert "access_token" in resp.cookies
    assert recorded == [logged_in_user]


@pytest.mark.asyncio
async def test_callback_success_via_redis_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """State validates against Redis when the cookie is absent (cross-domain case)."""

    class FakeRedis:
        def get(self, key: str) -> bytes | None:
            return b"1" if key == "oauth_state:rstate" else None

        def delete(self, key: str) -> None:
            pass

    monkeypatch.setattr(oauth_common, "get_redis_client", lambda: FakeRedis())
    monkeypatch.setattr(auth_google, "_exchange_code_for_tokens", lambda code: {"access_token": "ga"})
    monkeypatch.setattr(
        auth_google,
        "_fetch_google_user_info",
        lambda tok: {"id": "g1", "email": "r@example.com", "name": "R", "picture": "http://p"},
    )
    monkeypatch.setattr(
        auth_google.crud_user, "upsert_google_user", lambda *a, **kw: SimpleNamespace(id=USER_ID)
    )
    monkeypatch.setattr(auth_google.crud_user, "record_login", lambda db, u: None)
    # No oauth_state cookie sent — validation must fall back to Redis.
    resp = await _get("/api/v1/auth/google/callback?code=abc&state=rstate")
    assert resp.status_code == 302
    assert "/auth/callback#token=" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_state_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRedis:
        def get(self, key: str) -> bytes | None:
            return None

        def delete(self, key: str) -> None:
            pass

    monkeypatch.setattr(oauth_common, "get_redis_client", lambda: FakeRedis())
    resp = await _get("/api/v1/auth/google/callback?code=abc&state=bad", cookies={"oauth_state": "good"})
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_provider_error() -> None:
    resp = await _get("/api/v1/auth/google/callback?error=access_denied")
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


# ------------------------------------------------------------------
# crud_user.upsert_google_user
# ------------------------------------------------------------------

def test_upsert_creates_new_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crud_user, "get_by_google_id", lambda db, gid: None)
    monkeypatch.setattr(crud_user, "get_by_email", lambda db, email: None)
    user = crud_user.upsert_google_user(
        FakeDb(), google_id="g1", email="new@example.com", full_name="New", avatar_url="http://a"
    )
    assert user.google_id == "g1"
    assert user.email == "new@example.com"
    assert user.auth_provider == "google"
    assert user.is_verified is True
    assert user.hashed_password is None


def test_upsert_links_existing_email(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = SimpleNamespace(
        id=USER_ID, email="me@example.com", google_id=None, auth_provider="local",
        avatar_url=None, is_verified=False, full_name=None,
    )
    monkeypatch.setattr(crud_user, "get_by_google_id", lambda db, gid: None)
    monkeypatch.setattr(crud_user, "get_by_email", lambda db, email: existing)
    user = crud_user.upsert_google_user(
        FakeDb(), google_id="g2", email="me@example.com", full_name="Me", avatar_url="http://b"
    )
    assert user is existing
    assert user.google_id == "g2"
    assert user.auth_provider == "google"
    assert user.is_verified is True


def test_upsert_returns_existing_google_user(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = SimpleNamespace(id=USER_ID, google_id="g3", avatar_url=None, full_name="Old")
    monkeypatch.setattr(crud_user, "get_by_google_id", lambda db, gid: existing)
    user = crud_user.upsert_google_user(
        FakeDb(), google_id="g3", email="old@example.com", full_name="Old", avatar_url="http://c"
    )
    assert user is existing
    assert user.avatar_url == "http://c"
