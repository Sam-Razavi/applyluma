"""Tests for browser-extension support endpoints: auth token + applied-urls."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import applications as applications_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True, is_verified=True)


async def _request(method: str, path: str, *, authenticated: bool = True) -> httpx.Response:
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


# ------------------------------------------------------------------
# POST /api/v1/auth/extension-token
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extension_token_returns_bearer_pair() -> None:
    resp = await _request("POST", "/api/v1/auth/extension-token")
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_extension_token_requires_auth() -> None:
    resp = await _request("POST", "/api/v1/auth/extension-token", authenticated=False)
    assert resp.status_code == 401


# ------------------------------------------------------------------
# GET /api/v1/applications/applied-urls
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_applied_urls_returns_url_list(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_urls = ["https://example.com/a", "https://example.com/b"]
    monkeypatch.setattr(
        applications_endpoint.crud_application, "list_applied_job_urls", lambda *a, **kw: fake_urls
    )
    resp = await _request("GET", "/api/v1/applications/applied-urls")
    assert resp.status_code == 200
    assert resp.json()["urls"] == fake_urls


@pytest.mark.asyncio
async def test_applied_urls_requires_auth() -> None:
    resp = await _request("GET", "/api/v1/applications/applied-urls", authenticated=False)
    assert resp.status_code == 401
