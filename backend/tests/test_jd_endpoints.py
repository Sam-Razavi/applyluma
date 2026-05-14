from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import job_descriptions as jd_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
JD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CREATED_AT = datetime(2026, 5, 11, tzinfo=UTC)

class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[Any] = []

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: Any) -> None:
        self.refreshed.append(value)

@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()

def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)

def jd_data(jd_id: uuid.UUID = JD_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=jd_id,
        user_id=USER_ID,
        company_name="TechCorp",
        job_title="Python Developer",
        description="Write FastAPI apps and SQL queries.",
        url="https://example.com/jobs/1",
        keywords=["Python", "FastAPI", "SQL"],
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )

async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    json_body: dict[str, Any] | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=json_body)

@pytest.mark.asyncio
async def test_create_jd_extracts_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jd_endpoint, "extract_keywords", lambda text: ["Python", "SQL"])
    monkeypatch.setattr(jd_endpoint.crud_jd, "create", lambda db, user_id, body, keywords: jd_data())

    response = await request(
        "POST",
        "/api/v1/job-descriptions",
        current_user=user(),
        json_body={
            "company_name": "TechCorp",
            "job_title": "Python Developer",
            "description": "Need someone who knows Python and SQL",
            "url": "https://example.com/jobs/1",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(JD_ID)
    assert "Python" in response.json()["keywords"]

@pytest.mark.asyncio
async def test_list_jds_returns_user_data(monkeypatch: pytest.MonkeyPatch) -> None:
    jds = [jd_data(), jd_data(uuid.uuid4())]
    monkeypatch.setattr(jd_endpoint.crud_jd, "list_for_user", lambda db, user_id: jds)

    response = await request("GET", "/api/v1/job-descriptions", current_user=user())

    assert response.status_code == 200
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_get_jd_returns_404_if_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jd_endpoint.crud_jd, "get_by_id", lambda db, jd_id, user_id: None)

    response = await request("GET", f"/api/v1/job-descriptions/{JD_ID}", current_user=user())

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_jd_calls_crud(monkeypatch: pytest.MonkeyPatch) -> None:
    jd = jd_data()
    monkeypatch.setattr(jd_endpoint.crud_jd, "get_by_id", lambda db, jd_id, user_id: jd)
    
    deleted = []
    monkeypatch.setattr(jd_endpoint.crud_jd, "delete", lambda db, jd_obj: deleted.append(jd_obj))

    response = await request("DELETE", f"/api/v1/job-descriptions/{JD_ID}", current_user=user())

    assert response.status_code == 204
    assert len(deleted) == 1
