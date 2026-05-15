from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.dependencies import get_current_user, get_db
from app.crud import application as crud_application
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.rows


class FakeDb:
    def __init__(self, results: list[list[dict[str, Any]]]) -> None:
        self.results = results
        self.queries: list[str] = []

    def execute(self, query, params: dict[str, Any]) -> FakeResult:
        self.queries.append(str(query))
        return FakeResult(self.results.pop(0) if self.results else [])


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


def fake_db_for_analytics() -> FakeDb:
    return FakeDb(
        [
            [
                {"status": "applied", "count": 2},
                {"status": "interview", "count": 1},
                {"status": "offer", "count": 1},
            ],
            [{"average_response_days": 3.5}],
            [
                {"week_start": "2026-03-02", "count": 1},
                {"week_start": "2026-03-09", "count": 3},
            ],
            [
                {"source": "linkedin", "count": 3},
                {"source": "referral", "count": 1},
            ],
            [
                {"bucket": "30-60k", "count": 2},
                {"bucket": "60-90k", "count": 1},
            ],
        ]
    )


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    if db is not None:
        app.dependency_overrides[get_db] = lambda: db
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_analytics_returns_correct_structure_with_mocked_db() -> None:
    db = fake_db_for_analytics()

    response = await request(
        "GET",
        "/api/v1/applications/analytics",
        current_user=user(),
        db=db,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["funnel"][0] == {"status": "wishlist", "count": 0}
    assert body["funnel"][1] == {"status": "applied", "count": 2}
    assert body["response_rate"] == 0.5
    assert body["offer_rate"] == 0.25
    assert body["average_response_days"] == 3.5
    assert body["weekly_counts"][1] == {"week_start": "2026-03-09", "count": 3}
    assert body["top_sources"][0] == {"source": "linkedin", "count": 3}
    assert body["salary_distribution"][1] == {"bucket": "30-60k", "count": 2}
    assert len(db.queries) == 5


def test_response_rate_is_0_when_no_applications_past_applied() -> None:
    db = FakeDb(
        [
            [{"status": "applied", "count": 3}],
            [{"average_response_days": None}],
            [],
            [],
            [],
        ]
    )

    analytics = crud_application.get_analytics(db, USER_ID)

    assert analytics.response_rate == 0
    assert analytics.offer_rate == 0
    assert analytics.funnel[1].count == 3


@pytest.mark.asyncio
async def test_endpoint_requires_authentication() -> None:
    response = await request("GET", "/api/v1/applications/analytics")

    assert response.status_code == 401
