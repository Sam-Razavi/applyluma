"""Tests for LinkedIn OAuth (OIDC): login redirect, callback flow, and upsert wiring."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import auth_linkedin, oauth_common
from app.core.config import settings
from app.core.dependencies import get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeDb:
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


@pytest.mark.asyncio
async def test_login_redirects_to_linkedin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "li-client-id")
    resp = await _get("/api/v1/auth/linkedin/login")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith(auth_linkedin.LINKEDIN_AUTH_URL)
    assert "scope=openid+profile+email" in resp.headers["location"]
    assert "oauth_state" in resp.cookies


@pytest.mark.asyncio
async def test_login_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LINKEDIN_CLIENT_ID", "")
    resp = await _get("/api/v1/auth/linkedin/login")
    assert resp.status_code == 501


@pytest.mark.asyncio
async def test_callback_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_linkedin, "_exchange_code_for_tokens", lambda code: {"access_token": "la"})
    monkeypatch.setattr(
        auth_linkedin,
        "_fetch_linkedin_user_info",
        lambda tok: {"sub": "li-9", "email": "li@example.com", "name": "L", "picture": "http://p"},
    )
    upserted: dict = {}

    def fake_upsert(db: FakeDb, **kwargs: object) -> SimpleNamespace:
        upserted.update(kwargs)
        return SimpleNamespace(id=USER_ID)

    monkeypatch.setattr(auth_linkedin.crud_user, "upsert_oauth_user", fake_upsert)
    monkeypatch.setattr(auth_linkedin.crud_user, "record_login", lambda db, u: None)

    resp = await _get("/api/v1/auth/linkedin/callback?code=abc&state=s", cookies={"oauth_state": "s"})
    assert resp.status_code == 302
    assert "/auth/callback#token=" in resp.headers["location"]
    assert "access_token" in resp.cookies
    assert upserted["provider"] == "linkedin"
    assert upserted["id_attr"] == "linkedin_id"
    assert upserted["provider_user_id"] == "li-9"
    assert upserted["email"] == "li@example.com"


@pytest.mark.asyncio
async def test_callback_success_via_redis_state(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRedis:
        def get(self, key: str) -> bytes | None:
            return b"1" if key == "oauth_state:rstate" else None

        def delete(self, key: str) -> None:
            pass

    monkeypatch.setattr(oauth_common, "get_redis_client", lambda: FakeRedis())
    monkeypatch.setattr(auth_linkedin, "_exchange_code_for_tokens", lambda code: {"access_token": "la"})
    monkeypatch.setattr(
        auth_linkedin,
        "_fetch_linkedin_user_info",
        lambda tok: {"sub": "li-10", "email": "r@example.com", "name": "R", "picture": None},
    )
    monkeypatch.setattr(
        auth_linkedin.crud_user, "upsert_oauth_user", lambda db, **kw: SimpleNamespace(id=USER_ID)
    )
    monkeypatch.setattr(auth_linkedin.crud_user, "record_login", lambda db, u: None)

    resp = await _get("/api/v1/auth/linkedin/callback?code=abc&state=rstate")
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
    resp = await _get("/api/v1/auth/linkedin/callback?code=abc&state=bad", cookies={"oauth_state": "good"})
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_provider_error() -> None:
    resp = await _get("/api/v1/auth/linkedin/callback?error=user_cancelled_login")
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_missing_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_linkedin, "_exchange_code_for_tokens", lambda code: {"access_token": "la"})
    monkeypatch.setattr(
        auth_linkedin, "_fetch_linkedin_user_info", lambda tok: {"sub": "li-11", "name": "NoEmail"}
    )
    resp = await _get("/api/v1/auth/linkedin/callback?code=abc&state=s", cookies={"oauth_state": "s"})
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]
