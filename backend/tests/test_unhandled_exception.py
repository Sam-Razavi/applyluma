from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.dependencies import get_db
from app.main import app


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def request(method: str, path: str) -> httpx.Response:
    # raise_server_exceptions=False: a real ASGI server (uvicorn) sends the
    # error response to the client before re-raising for server-side logging;
    # match that client-visible behavior here instead of letting the test
    # transport propagate the exception it already turned into a response.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


def _raise_db() -> None:
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_unhandled_exception_returns_standard_500_shape() -> None:
    app.dependency_overrides[get_db] = _raise_db

    response = await request("GET", "/api/v1/health/detailed")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert "detail" in body
    assert "boom" not in body["detail"]
