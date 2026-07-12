"""Tests for GitHub OAuth: login redirect, callback flow, and email fallback."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import auth_github, oauth_common
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
async def test_login_redirects_to_github(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "gh-client-id")
    resp = await _get("/api/v1/auth/github/login")
    assert resp.status_code == 302
    assert resp.headers["location"].startswith(auth_github.GITHUB_AUTH_URL)
    assert "oauth_state" in resp.cookies


@pytest.mark.asyncio
async def test_login_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "")
    resp = await _get("/api/v1/auth/github/login")
    assert resp.status_code == 501


@pytest.mark.asyncio
async def test_callback_success_with_public_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_github, "_exchange_code_for_tokens", lambda code: {"access_token": "gt"})
    monkeypatch.setattr(
        auth_github,
        "_fetch_github_user_info",
        lambda tok: {"id": 4242, "email": "gh@example.com", "name": "G", "login": "ghuser",
                     "avatar_url": "http://a"},
    )
    upserted: dict = {}

    def fake_upsert(db: FakeDb, **kwargs: object) -> SimpleNamespace:
        upserted.update(kwargs)
        return SimpleNamespace(id=USER_ID)

    monkeypatch.setattr(auth_github.crud_user, "upsert_oauth_user", fake_upsert)
    monkeypatch.setattr(auth_github.crud_user, "record_login", lambda db, u: None)

    resp = await _get("/api/v1/auth/github/callback?code=abc&state=s", cookies={"oauth_state": "s"})
    assert resp.status_code == 302
    assert "/auth/callback#token=" in resp.headers["location"]
    assert upserted["provider"] == "github"
    assert upserted["id_attr"] == "github_id"
    # GitHub ids are integers on the wire; must be stored as strings.
    assert upserted["provider_user_id"] == "4242"
    assert upserted["email"] == "gh@example.com"


@pytest.mark.asyncio
async def test_callback_null_email_falls_back_to_emails_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_github, "_exchange_code_for_tokens", lambda code: {"access_token": "gt"})
    monkeypatch.setattr(
        auth_github,
        "_fetch_github_user_info",
        lambda tok: {"id": 77, "email": None, "name": None, "login": "quiet-dev", "avatar_url": None},
    )
    monkeypatch.setattr(
        auth_github, "_fetch_github_primary_email", lambda tok: "primary@example.com"
    )
    upserted: dict = {}

    def fake_upsert(db: FakeDb, **kwargs: object) -> SimpleNamespace:
        upserted.update(kwargs)
        return SimpleNamespace(id=USER_ID)

    monkeypatch.setattr(auth_github.crud_user, "upsert_oauth_user", fake_upsert)
    monkeypatch.setattr(auth_github.crud_user, "record_login", lambda db, u: None)

    resp = await _get("/api/v1/auth/github/callback?code=abc&state=s", cookies={"oauth_state": "s"})
    assert resp.status_code == 302
    assert "/auth/callback#token=" in resp.headers["location"]
    assert upserted["email"] == "primary@example.com"
    # No display name on the profile — falls back to the login handle.
    assert upserted["full_name"] == "quiet-dev"


@pytest.mark.asyncio
async def test_callback_no_verified_email_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_github, "_exchange_code_for_tokens", lambda code: {"access_token": "gt"})
    monkeypatch.setattr(
        auth_github,
        "_fetch_github_user_info",
        lambda tok: {"id": 88, "email": None, "login": "no-email"},
    )
    monkeypatch.setattr(auth_github, "_fetch_github_primary_email", lambda tok: None)

    resp = await _get("/api/v1/auth/github/callback?code=abc&state=s", cookies={"oauth_state": "s"})
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_state_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeRedis:
        def get(self, key: str) -> bytes | None:
            return None

        def delete(self, key: str) -> None:
            pass

    monkeypatch.setattr(oauth_common, "get_redis_client", lambda: FakeRedis())
    resp = await _get("/api/v1/auth/github/callback?code=abc&state=bad", cookies={"oauth_state": "good"})
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_callback_provider_error() -> None:
    resp = await _get("/api/v1/auth/github/callback?error=access_denied")
    assert resp.status_code == 302
    assert "error=oauth_failed" in resp.headers["location"]


def test_primary_email_picker_prefers_primary_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    emails = [
        {"email": "old@example.com", "primary": False, "verified": True},
        {"email": "main@example.com", "primary": True, "verified": True},
    ]

    class FakeResp:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> list[dict]:
            return emails

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def get(self, *a: object, **kw: object) -> FakeResp:
            return FakeResp()

    monkeypatch.setattr(auth_github.httpx, "Client", FakeClient)
    assert auth_github._fetch_github_primary_email("tok") == "main@example.com"
