from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import health as health_endpoint
from app.core.dependencies import get_db, get_redis_client
from app.main import app


class FakeDb:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def execute(self, query) -> int:
        if self.fail:
            raise RuntimeError("database unavailable")
        return 1


class FakeRedis:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def ping(self) -> bool:
        if self.fail:
            raise RuntimeError("redis unavailable")
        return True


class FakeInspector:
    def active(self) -> dict[str, list[object]]:
        return {"worker-1": []}


class FakeControl:
    def inspect(self, timeout: int = 1) -> FakeInspector:
        return FakeInspector()


class FakeCeleryApp:
    control = FakeControl()


@pytest.fixture(autouse=True)
def clear_overrides(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    app.dependency_overrides.clear()
    monkeypatch.setattr(health_endpoint, "celery_app", FakeCeleryApp())
    monkeypatch.setattr(health_endpoint.settings, "ADZUNA_APP_ID", "adzuna-id")
    yield
    app.dependency_overrides.clear()


async def request(method: str, path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


def override_health_dependencies(*, db_fail: bool = False, redis_fail: bool = False) -> None:
    app.dependency_overrides[get_db] = lambda: FakeDb(fail=db_fail)
    app.dependency_overrides[get_redis_client] = lambda: FakeRedis(fail=redis_fail)


@pytest.mark.asyncio
async def test_health_returns_200() -> None:
    response = await request("GET", "/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_detailed_health_returns_valid_structure_with_mocked_services() -> None:
    override_health_dependencies()

    response = await request("GET", "/api/v1/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert set(body["checks"]) == {"db", "redis", "celery", "adzuna"}
    assert body["checks"]["db"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "ok"
    assert body["checks"]["celery"]["status"] == "ok"
    assert body["checks"]["adzuna"]["configured"] is True


@pytest.mark.asyncio
async def test_detailed_health_is_degraded_when_redis_fails() -> None:
    override_health_dependencies(redis_fail=True)

    response = await request("GET", "/api/v1/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_detailed_health_is_unhealthy_when_db_fails() -> None:
    override_health_dependencies(db_fail=True)

    response = await request("GET", "/api/v1/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["checks"]["db"]["status"] == "unhealthy"
