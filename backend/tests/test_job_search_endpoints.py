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

from app.api.v1.endpoints import job_search as job_search_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, get_redis_client
from app.main import app
from app.schemas.job_search import AdzunaJobResult, JobSearchResponse

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.set_calls = 0

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        assert ttl == 600
        self.set_calls += 1
        self.store[key] = value


class FakePipelineLogDb:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        del statement
        if params is not None:
            self.rows.append(params)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


def response_data(page: int = 1) -> JobSearchResponse:
    return JobSearchResponse(
        results=[
            AdzunaJobResult(
                id="adzuna-1",
                title="Backend Engineer",
                company_name="Spotify",
                location="Stockholm",
                salary_min=600000,
                salary_max=800000,
                contract_type="permanent",
                redirect_url="https://example.com/job",
                description="Build APIs with Python and FastAPI.",
                created="2026-05-14T10:00:00Z",
            )
        ],
        count=1,
        page=page,
        total_pages=1,
    )


async def request(
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    redis_client: FakeRedis | None = None,
    db: FakePipelineLogDb | None = None,
    raise_app_exceptions: bool = True,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    if redis_client is not None:
        app.dependency_overrides[get_redis_client] = lambda: redis_client
    app.dependency_overrides[get_db] = lambda: db or FakePipelineLogDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions),
        base_url="http://test",
    ) as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_search_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "app-id")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")
    monkeypatch.setattr(settings, "ADZUNA_COUNTRY", "se")

    calls: list[dict[str, Any]] = []

    async def mock_search_jobs(**kwargs):
        calls.append(kwargs)
        return response_data(page=kwargs["page"])

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_search_jobs)

    response = await request(
        "/api/v1/jobs/search?q=python&location=Stockholm&page=2&results_per_page=20&source=adzuna",
        current_user=user(),
        redis_client=FakeRedis(),
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "Backend Engineer"
    assert calls[0]["country"] == "se"
    assert calls[0]["q"] == "python"
    assert calls[0]["location"] == "Stockholm"
    assert calls[0]["page"] == 2
    assert calls[0]["results_per_page"] == 20


@pytest.mark.asyncio
async def test_successful_search_logs_jobsearch_pipeline_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "app-id")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")
    db = FakePipelineLogDb()

    async def mock_search_jobs(**kwargs):
        return response_data(page=kwargs["page"])

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_search_jobs)

    response = await request(
        "/api/v1/jobs/search?q=python&source=adzuna",
        current_user=user(),
        redis_client=FakeRedis(),
        db=db,
    )

    assert response.status_code == 200
    assert db.commits == 1
    assert db.rows == [
        {
            "pipeline_name": "JobSearch API",
            "rows_affected": 1,
            "status": "success",
            "error_message": None,
        }
    ]


@pytest.mark.asyncio
async def test_failed_search_logs_jobsearch_pipeline_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "app-id")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")
    db = FakePipelineLogDb()

    async def mock_search_jobs(**kwargs):
        del kwargs
        raise RuntimeError("Adzuna unavailable")

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_search_jobs)

    response = await request(
        "/api/v1/jobs/search?q=python&source=adzuna",
        current_user=user(),
        redis_client=FakeRedis(),
        db=db,
        raise_app_exceptions=False,
    )

    assert response.status_code == 500
    assert db.commits == 1
    assert db.rows == [
        {
            "pipeline_name": "JobSearch API",
            "rows_affected": 0,
            "status": "failed",
            "error_message": "Adzuna unavailable",
        }
    ]


@pytest.mark.asyncio
async def test_search_returns_cached_results_on_second_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "app-id")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")
    fake_redis = FakeRedis()
    call_count = 0

    async def mock_search_jobs(**kwargs):
        nonlocal call_count
        call_count += 1
        return response_data(page=kwargs["page"])

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_search_jobs)

    first = await request(
        "/api/v1/jobs/search?q=python&location=Stockholm&source=adzuna",
        current_user=user(),
        redis_client=fake_redis,
    )
    second = await request(
        "/api/v1/jobs/search?q=python&location=Stockholm&source=adzuna",
        current_user=user(),
        redis_client=fake_redis,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert call_count == 1
    assert fake_redis.set_calls == 1
    assert second.json()["results"][0]["company_name"] == "Spotify"


@pytest.mark.asyncio
async def test_search_returns_empty_when_adzuna_app_id_is_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")
    called = False

    async def mock_search_jobs(**kwargs):
        nonlocal called
        called = True
        return response_data()

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_search_jobs)

    response = await request(
        "/api/v1/jobs/search?q=python&source=adzuna",
        current_user=user(),
        redis_client=FakeRedis(),
    )

    assert response.status_code == 200
    assert response.json() == {"results": [], "count": 0, "page": 1, "total_pages": 0}
    assert called is False


@pytest.mark.asyncio
async def test_search_platsbanken_source(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    async def mock_platsbanken(**kwargs):
        calls.append(kwargs)
        return JobSearchResponse(
            results=[
                AdzunaJobResult(
                    id="pb-1",
                    title="Python Developer",
                    company_name="IKEA",
                    location="Malmö",
                    redirect_url="https://arbetsformedlingen.se/platsbanken/annonser/pb-1",
                    description="Build systems with Python.",
                    source="platsbanken",
                )
            ],
            count=1,
            page=1,
            total_pages=1,
        )

    monkeypatch.setattr(
        job_search_endpoint.platsbanken_search_service, "search_jobs", mock_platsbanken,
    )

    response = await request(
        "/api/v1/jobs/search?q=python&source=platsbanken",
        current_user=user(),
        redis_client=FakeRedis(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "platsbanken"
    assert data["results"][0]["company_name"] == "IKEA"
    assert calls[0]["q"] == "python"


@pytest.mark.asyncio
async def test_search_all_sources_merges_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "app-id")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")

    async def mock_adzuna(**kwargs):
        return response_data(page=kwargs["page"])

    async def mock_platsbanken(**kwargs):
        return JobSearchResponse(
            results=[
                AdzunaJobResult(
                    id="pb-2",
                    title="Frontend Dev",
                    company_name="Volvo",
                    location="Gothenburg",
                    redirect_url="https://arbetsformedlingen.se/platsbanken/annonser/pb-2",
                    description="React and TypeScript.",
                    source="platsbanken",
                )
            ],
            count=1,
            page=kwargs["page"],
            total_pages=1,
        )

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_adzuna)
    monkeypatch.setattr(
        job_search_endpoint.platsbanken_search_service, "search_jobs", mock_platsbanken,
    )

    response = await request(
        "/api/v1/jobs/search?q=developer&source=all",
        current_user=user(),
        redis_client=FakeRedis(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["results"]) == 2
    sources = {r["source"] for r in data["results"]}
    assert sources == {"adzuna", "platsbanken"}


@pytest.mark.asyncio
async def test_search_all_graceful_degradation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "app-id")
    monkeypatch.setattr(settings, "ADZUNA_API_KEY", "app-key")

    async def mock_adzuna(**kwargs):
        raise RuntimeError("Adzuna down")

    async def mock_platsbanken(**kwargs):
        return JobSearchResponse(
            results=[
                AdzunaJobResult(
                    id="pb-3",
                    title="DevOps Engineer",
                    company_name="Ericsson",
                    location="Stockholm",
                    redirect_url="https://arbetsformedlingen.se/platsbanken/annonser/pb-3",
                    description="Kubernetes and Docker.",
                    source="platsbanken",
                )
            ],
            count=1,
            page=kwargs["page"],
            total_pages=1,
        )

    monkeypatch.setattr(job_search_endpoint.adzuna_service, "search_jobs", mock_adzuna)
    monkeypatch.setattr(
        job_search_endpoint.platsbanken_search_service, "search_jobs", mock_platsbanken,
    )

    response = await request(
        "/api/v1/jobs/search?q=devops&source=all",
        current_user=user(),
        redis_client=FakeRedis(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "platsbanken"


@pytest.mark.asyncio
async def test_search_requires_authentication() -> None:
    response = await request("/api/v1/jobs/search?q=python", redis_client=FakeRedis())

    assert response.status_code == 401
