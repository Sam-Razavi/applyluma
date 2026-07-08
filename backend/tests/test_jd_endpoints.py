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

import httpx as httpx_lib

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
        source_raw_job_posting_id=None,
        company_name="TechCorp",
        job_title="Python Developer",
        description="Write FastAPI apps and SQL queries.",
        url="https://example.com/jobs/1",
        keywords=["Python", "FastAPI", "SQL"],
        starred=False,
        notes=None,
        list_name=None,
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
    fake_extractor = SimpleNamespace(
        extract_keywords=lambda text: {},
        keywords_as_flat_list=lambda extracted, min_confidence=0.0: ["Python", "SQL"],
    )
    monkeypatch.setattr(jd_endpoint, "_extractor", fake_extractor)
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
    monkeypatch.setattr(jd_endpoint.crud_jd, "list_for_user", lambda db, user_id, **kw: jds)

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


_SCRAPED = {
    "job_title": "Senior Python Engineer",
    "company_name": "TechCorp",
    "description": "We are looking for a Senior Python Engineer...",
    "url": "https://example.com/jobs/senior-python-engineer",
}


@pytest.mark.asyncio
async def test_scrape_url_returns_extracted_data(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scrape(url: str) -> dict:
        return _SCRAPED

    monkeypatch.setattr(jd_endpoint, "scrape_job_url", fake_scrape)

    response = await request(
        "POST",
        "/api/v1/job-descriptions/scrape-url",
        current_user=user(),
        json_body={"url": "https://example.com/jobs/senior-python-engineer"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["job_title"] == "Senior Python Engineer"
    assert data["company_name"] == "TechCorp"
    assert "Python Engineer" in data["description"]


@pytest.mark.asyncio
async def test_scrape_url_requires_auth() -> None:
    response = await request(
        "POST",
        "/api/v1/job-descriptions/scrape-url",
        json_body={"url": "https://example.com/jobs/1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scrape_url_returns_422_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scrape(url: str) -> dict:
        raise httpx_lib.HTTPStatusError(
            "Not Found",
            request=httpx_lib.Request("GET", url),
            response=httpx_lib.Response(404),
        )

    monkeypatch.setattr(jd_endpoint, "scrape_job_url", fake_scrape)

    response = await request(
        "POST",
        "/api/v1/job-descriptions/scrape-url",
        current_user=user(),
        json_body={"url": "https://example.com/missing"},
    )

    assert response.status_code == 422
    assert "404" in response.json()["detail"]


@pytest.mark.asyncio
async def test_scrape_url_returns_422_on_generic_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_scrape(url: str) -> dict:
        raise RuntimeError("Connection timeout")

    monkeypatch.setattr(jd_endpoint, "scrape_job_url", fake_scrape)

    response = await request(
        "POST",
        "/api/v1/job-descriptions/scrape-url",
        current_user=user(),
        json_body={"url": "https://example.com/jobs/1"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# get_or_create_from_raw_job: concurrent-submit race on uq_jd_user_raw_job
# ---------------------------------------------------------------------------


def test_get_or_create_from_raw_job_recovers_from_unique_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When CV tailor and cover letter submits race to create the same JD,
    the loser of the unique-index race must reuse the winner's row instead
    of surfacing a 500."""
    from sqlalchemy.exc import IntegrityError

    from app.crud import job_description as crud_jd

    raw_job_id = uuid.uuid4()
    raw_job = SimpleNamespace(
        id=raw_job_id,
        company="Acme",
        title="Backend Engineer",
        description="Python and SQL",
        url="https://example.com/job",
        extracted_skills={},
    )
    winner_row = SimpleNamespace(id=JD_ID, source_raw_job_posting_id=raw_job_id)

    # No row exists at first check; after the failed commit the winner's row
    # is visible.
    lookups = iter([None, winner_row])
    monkeypatch.setattr(
        crud_jd, "get_by_source_raw_job", lambda db, user_id, raw_id: next(lookups)
    )
    monkeypatch.setattr(crud_jd, "_keywords_from_raw_job", lambda db, rj: ["python"])

    class RacyDb:
        def __init__(self) -> None:
            self.rolled_back = False

        def query(self, model: Any) -> Any:
            return SimpleNamespace(filter=lambda *a: SimpleNamespace(first=lambda: raw_job))

        def add(self, obj: Any) -> None:
            pass

        def commit(self) -> None:
            raise IntegrityError("INSERT INTO job_descriptions", {}, Exception("uq_jd_user_raw_job"))

        def rollback(self) -> None:
            self.rolled_back = True

        def refresh(self, obj: Any) -> None:
            raise AssertionError("refresh must not run after a failed commit")

    db = RacyDb()
    result = crud_jd.get_or_create_from_raw_job(
        db, user_id=USER_ID, raw_job_posting_id=raw_job_id
    )

    assert db.rolled_back
    assert result is winner_row
