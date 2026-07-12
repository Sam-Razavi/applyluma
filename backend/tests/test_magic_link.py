"""Tests for magic-link email login and the auth providers discovery endpoint."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import auth as auth_endpoint
from app.core.config import settings
from app.core.dependencies import get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class FakeRedis:
    """Minimal Redis stand-in storing setex values with their TTLs."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user(active: bool = True, verified: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID,
        email="user@example.com",
        is_active=active,
        is_verified=verified,
    )


async def _post(path: str, json: dict) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(path, json=json)


async def _get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(path)


# ------------------------------------------------------------------
# POST /auth/magic-link (request)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_stores_token_and_sends_email(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    sent: list[tuple[str, str]] = []
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: _user())
    monkeypatch.setattr(
        auth_endpoint.email_service,
        "send_magic_link_email",
        lambda email, token: sent.append((email, token)),
    )

    resp = await _post("/api/v1/auth/magic-link", {"email": "user@example.com"})

    assert resp.status_code == 204
    assert len(sent) == 1
    email, token = sent[0]
    assert email == "user@example.com"
    assert fake_redis.store[f"magic_login:{token}"] == str(USER_ID)
    assert fake_redis.ttls[f"magic_login:{token}"] == 900


@pytest.mark.asyncio
async def test_request_unknown_email_is_silent_204(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    sent: list[str] = []
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: None)
    monkeypatch.setattr(
        auth_endpoint.email_service, "send_magic_link_email", lambda email, token: sent.append(email)
    )

    resp = await _post("/api/v1/auth/magic-link", {"email": "nobody@example.com"})

    assert resp.status_code == 204
    assert sent == []
    assert fake_redis.store == {}


@pytest.mark.asyncio
async def test_request_inactive_user_is_silent_204(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: FakeRedis())
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_email", lambda db, email: _user(active=False))
    monkeypatch.setattr(
        auth_endpoint.email_service, "send_magic_link_email", lambda email, token: sent.append(email)
    )

    resp = await _post("/api/v1/auth/magic-link", {"email": "user@example.com"})

    assert resp.status_code == 204
    assert sent == []


# ------------------------------------------------------------------
# POST /auth/magic-link/verify
# ------------------------------------------------------------------

def _seed_token(fake_redis: FakeRedis, token: str = "tok123") -> str:
    fake_redis.setex(f"magic_login:{token}", 900, str(USER_ID))
    return token


@pytest.mark.asyncio
async def test_verify_success_returns_tokens_and_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = FakeRedis()
    token = _seed_token(fake_redis)
    user = _user()
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: user)
    recorded: list[SimpleNamespace] = []
    monkeypatch.setattr(auth_endpoint.crud_user, "record_login", lambda db, u: recorded.append(u))

    resp = await _post("/api/v1/auth/magic-link/verify", {"token": token})

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert "access_token" in resp.cookies
    assert recorded == [user]
    # Token is single-use.
    assert fake_redis.store == {}


@pytest.mark.asyncio
async def test_verify_token_is_single_use(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    token = _seed_token(fake_redis)
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: _user())
    monkeypatch.setattr(auth_endpoint.crud_user, "record_login", lambda db, u: None)

    first = await _post("/api/v1/auth/magic-link/verify", {"token": token})
    second = await _post("/api/v1/auth/magic-link/verify", {"token": token})

    assert first.status_code == 200
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_verify_unknown_token_400(monkeypatch: pytest.MonkeyPatch) -> None:
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: FakeRedis())

    resp = await _post("/api/v1/auth/magic-link/verify", {"token": "nope"})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_inactive_user_400(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    token = _seed_token(fake_redis)
    app.dependency_overrides[get_db] = lambda: FakeDb()
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: _user(active=False))

    resp = await _post("/api/v1/auth/magic-link/verify", {"token": token})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_marks_unverified_user_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    token = _seed_token(fake_redis)
    user = _user(verified=False)
    fake_db = FakeDb()
    app.dependency_overrides[get_db] = lambda: fake_db
    monkeypatch.setattr(auth_endpoint, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(auth_endpoint.crud_user, "get_by_id", lambda db, uid: user)
    monkeypatch.setattr(auth_endpoint.crud_user, "record_login", lambda db, u: None)

    resp = await _post("/api/v1/auth/magic-link/verify", {"token": token})

    assert resp.status_code == 200
    assert user.is_verified is True
    assert fake_db.commits == 1


# ------------------------------------------------------------------
# GET /auth/providers
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_providers_reflect_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "g")
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "l")
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "r")

    resp = await _get("/api/v1/auth/providers")

    assert resp.status_code == 200
    assert resp.json() == {"google": True, "linkedin": True, "github": False, "magic_link": True}


@pytest.mark.asyncio
async def test_providers_all_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    for attr in ("GOOGLE_CLIENT_ID", "LINKEDIN_CLIENT_ID", "GITHUB_CLIENT_ID", "RESEND_API_KEY"):
        monkeypatch.setattr(settings, attr, "")

    resp = await _get("/api/v1/auth/providers")

    assert resp.status_code == 200
    assert resp.json() == {"google": False, "linkedin": False, "github": False, "magic_link": False}
