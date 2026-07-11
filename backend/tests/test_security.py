"""Tests for HTTP security headers and auth endpoint rate limiting."""
from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import auth as auth_endpoint
from app.core.dependencies import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Fake collaborators
# ---------------------------------------------------------------------------

class _FakeDb:
    pass


class _AlwaysExceededRedis:
    """Counter already above any limit — next call triggers 429."""

    def incr(self, key: str) -> int:
        return 999

    def expire(self, key: str, ttl: int) -> None:
        pass


class _NeverExceededRedis:
    """Counter on its first increment — always within limit."""

    def incr(self, key: str) -> int:
        return 1

    def expire(self, key: str, ttl: int) -> None:
        pass


class _FailingRedis:
    """Simulates a Redis outage."""

    def incr(self, key: str) -> int:
        raise ConnectionError("Redis unavailable")

    def expire(self, key: str, ttl: int) -> None:
        raise ConnectionError("Redis unavailable")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _stub_auth_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override get_db and stub authenticate to return None (→ 401)."""
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    monkeypatch.setattr(auth_endpoint.crud_user, "authenticate", lambda db, email, pw: None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(path)


async def _post(path: str, json: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(path, json=json or {})


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-xss-protection": "0",
}


@pytest.mark.asyncio
async def test_security_headers_present_on_health_endpoint() -> None:
    response = await _get("/health")

    assert response.status_code == 200
    for header, value in EXPECTED_HEADERS.items():
        assert response.headers.get(header) == value, f"Missing or wrong: {header}"


@pytest.mark.asyncio
async def test_permissions_policy_header_present() -> None:
    response = await _get("/health")

    policy = response.headers.get("permissions-policy", "")
    for directive in ("camera=()", "microphone=()", "geolocation=()"):
        assert directive in policy


@pytest.mark.asyncio
async def test_hsts_absent_outside_production() -> None:
    """HSTS must not be set in development — it would break HTTP localhost."""
    response = await _get("/health")

    assert "strict-transport-security" not in response.headers


# ---------------------------------------------------------------------------
# Auth rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_rate_limit_returns_429_when_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.main.get_redis_client", lambda: _AlwaysExceededRedis())

    response = await _post("/api/v1/auth/login", {"email": "x@x.com", "password": "pw"})

    assert response.status_code == 429
    assert response.json()["code"] == "TOO_MANY_REQUESTS"
    assert response.headers.get("retry-after") == "60"


@pytest.mark.asyncio
async def test_register_rate_limit_returns_429_when_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.main.get_redis_client", lambda: _AlwaysExceededRedis())

    response = await _post("/api/v1/auth/register", {"email": "x@x.com", "password": "Secure1!"})

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_passes_through_when_within_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the counter is within the limit the request must reach the handler."""
    monkeypatch.setattr("app.main.get_redis_client", lambda: _NeverExceededRedis())
    _stub_auth_db(monkeypatch)

    response = await _post("/api/v1/auth/login", {"email": "x@x.com", "password": "pw"})

    # 401 means the handler ran (bad credentials), not a rate-limit rejection
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit_fails_open_on_redis_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Redis is down the request must NOT be blocked — fail open."""
    monkeypatch.setattr("app.main.get_redis_client", lambda: _FailingRedis())
    _stub_auth_db(monkeypatch)

    response = await _post("/api/v1/auth/login", {"email": "x@x.com", "password": "pw"})

    # Still reaches the handler: bad credentials → 401, not 429 or 500
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_security_headers_present_on_429_rate_limit_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rate-limited responses must still carry all security headers."""
    monkeypatch.setattr("app.main.get_redis_client", lambda: _AlwaysExceededRedis())

    response = await _post("/api/v1/auth/login", {"email": "x@x.com", "password": "pw"})

    assert response.status_code == 429
    for header, value in EXPECTED_HEADERS.items():
        assert response.headers.get(header) == value, f"Security header missing on 429: {header}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/refresh",
    ],
)
async def test_previously_unlimited_auth_endpoints_are_now_rate_limited(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr("app.main.get_redis_client", lambda: _AlwaysExceededRedis())

    response = await _post(path, {})

    assert response.status_code == 429


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        # Real routes — the dict used to key on the router *prefix* only
        # ("/api/v1/tailor", "/api/v1/cover-letters"), which never matches
        # request.url.path for these endpoints, so the limit silently never
        # fired. These assert the fix, not just headers.
        "/api/v1/tailor/submit",
        "/api/v1/cover-letters/generate",
        "/api/v1/auth/change-password",
        "/api/v1/auth/extension-token",
    ],
)
async def test_expensive_endpoints_are_rate_limited_on_real_routes(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr("app.main.get_redis_client", lambda: _AlwaysExceededRedis())

    response = await _post(path, {})

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_expensive_rate_limit_dict_keys_match_real_router_paths() -> None:
    """Regression guard for the silent path-mismatch bug: every key in
    _EXPENSIVE_RATE_LIMITS must be an exact, currently-registered route path,
    not just a router prefix that happens to look similar. Uses the OpenAPI
    schema (not app.routes) since FastAPI's route list is lazily wrapped and
    doesn't expose flattened paths directly."""
    from app.main import _EXPENSIVE_RATE_LIMITS
    from app.main import app as fastapi_app

    registered_paths = set(fastapi_app.openapi()["paths"].keys())
    for limited_path in _EXPENSIVE_RATE_LIMITS:
        assert limited_path in registered_paths, (
            f"{limited_path!r} in _EXPENSIVE_RATE_LIMITS does not match any "
            "registered route — the rate limit silently never fires"
        )
