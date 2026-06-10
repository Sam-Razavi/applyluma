"""Smoke and validation tests for the analytics API endpoints."""
from __future__ import annotations

import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.dependencies import get_db, get_redis_client
from app.main import app
from app.schemas.analytics import ResponseMetadata


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class _FakeDb:
    pass


class _FakeRedis:
    pass


def _fake_metadata() -> ResponseMetadata:
    now = datetime.now(UTC)
    return ResponseMetadata(
        timestamp=now,
        data_freshness_hours=1,
        sample_size=100,
        applied_filters={},
        next_update=now,
    )


def _setup_deps() -> None:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedis()


async def _get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(path)


# ---------------------------------------------------------------------------
# /analytics/trending-skills
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trending_skills_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import trending_skills as ts
    monkeypatch.setattr(ts, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(ts, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/trending-skills")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_trending_skills_invalid_limit_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/trending-skills?limit=0")

    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_trending_skills_limit_too_high_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/trending-skills?limit=101")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# /analytics/salary-insights
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_salary_insights_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import salary_insights as si
    monkeypatch.setattr(si, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(si, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/salary-insights")

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_salary_insights_invalid_experience_level_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/salary-insights?experience_level=expert")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "experience_level" in body["error"]["details"]


@pytest.mark.asyncio
async def test_salary_insights_overly_long_location_returns_400() -> None:
    _setup_deps()
    long_location = "A" * 201

    response = await _get(f"/api/v1/analytics/salary-insights?location={long_location}")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# /analytics/job-market-health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_market_health_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    fixture = {
        "total_jobs": 1000,
        "unique_companies": 200,
        "remote_percentage": 40.0,
        "avg_salary_midpoint": None,
        "senior_role_pct": 30.0,
        "junior_role_pct": 20.0,
        "management_role_pct": 10.0,
        "mid_role_pct": 40.0,
        "avg_skills_per_job": 5.2,
        "data_date_range_days": 30,
        "last_updated": None,
    }
    from app.api.v1.endpoints.analytics import job_market_health as jmh
    monkeypatch.setattr(jmh, "get_or_cache", lambda *a, **kw: fixture)
    monkeypatch.setattr(jmh, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/job-market-health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "total_jobs" in body["data"]
    assert "remote_percentage" in body["data"]


# ---------------------------------------------------------------------------
# /analytics/location-trends
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_location_trends_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import location_trends as lt
    monkeypatch.setattr(lt, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(lt, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/location-trends")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/skill-demand
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_skill_demand_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import skill_demand as sd
    monkeypatch.setattr(sd, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(sd, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/skill-demand")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/experience-levels
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_experience_levels_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import experience_levels as el
    monkeypatch.setattr(el, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(el, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/experience-levels")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/hiring-patterns
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hiring_patterns_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import hiring_patterns as hp
    monkeypatch.setattr(hp, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(hp, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/hiring-patterns")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/company-insights
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_company_insights_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import company_insights as ci
    monkeypatch.setattr(ci, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(ci, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/company-insights")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/industry-breakdown
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_industry_breakdown_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import industry_breakdown as ib
    monkeypatch.setattr(ib, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(ib, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/industry-breakdown")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/job-type-mix
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_job_type_mix_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import job_type_mix as jtm
    monkeypatch.setattr(jtm, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(jtm, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/job-type-mix")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# /analytics/salary-by-skill
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_salary_by_skill_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import salary_by_skill as sbs
    monkeypatch.setattr(sbs, "get_or_cache", lambda *a, **kw: [])
    monkeypatch.setattr(sbs, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/salary-by-skill")

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# safe_execute error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trending_skills_db_error_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_deps()
    from app.api.v1.endpoints.analytics import trending_skills as ts
    from sqlalchemy.exc import SQLAlchemyError

    def _raise(*a, **kw):
        raise SQLAlchemyError("DB down")

    monkeypatch.setattr(ts, "get_or_cache", _raise)

    response = await _get("/api/v1/analytics/trending-skills")

    assert response.status_code == 500
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# Secondary parameter validation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trending_skills_invalid_min_jobs_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/trending-skills?min_jobs=0")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_hiring_patterns_invalid_days_back_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/hiring-patterns?days_back=3")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_hiring_patterns_invalid_granularity_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/hiring-patterns?granularity=hourly")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_company_insights_invalid_limit_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/company-insights?limit=0")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_salary_by_skill_invalid_limit_returns_400() -> None:
    _setup_deps()

    response = await _get("/api/v1/analytics/salary-by-skill?limit=200")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_comparison_invalid_uuid_returns_400() -> None:
    _setup_deps()
    from app.core.dependencies import get_current_user_id
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"

    response = await _get("/api/v1/analytics/comparison?resume_id=not-a-uuid")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Cache-miss path: analytics endpoints with real get_or_cache (no mock)
# This covers the query() closures inside fetch() for each endpoint.
# ---------------------------------------------------------------------------

class _FakeExecuteResult:
    def __init__(self, rows=None):
        self._rows = rows or []
    def fetchall(self): return self._rows
    def fetchone(self): return self._rows[0] if self._rows else None


class _QueryDb:
    def execute(self, *args, **kwargs):
        return _FakeExecuteResult()


class _CacheMissRedis:
    def get(self, key): return None
    def setex(self, key, ttl, value): pass


def _setup_cache_miss() -> None:
    app.dependency_overrides[get_db] = lambda: _QueryDb()
    app.dependency_overrides[get_redis_client] = lambda: _CacheMissRedis()


@pytest.mark.asyncio
async def test_hiring_patterns_cache_miss_executes_query(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_cache_miss()
    from app.api.v1.endpoints.analytics import hiring_patterns as hp
    monkeypatch.setattr(hp, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/hiring-patterns")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_job_market_health_cache_miss_executes_query(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_cache_miss()
    from app.api.v1.endpoints.analytics import job_market_health as jmh
    monkeypatch.setattr(jmh, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/job-market-health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trending_skills_cache_miss_executes_query(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_cache_miss()
    from app.api.v1.endpoints.analytics import trending_skills as ts
    monkeypatch.setattr(ts, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/trending-skills")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_salary_insights_cache_miss_executes_query(monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_cache_miss()
    from app.api.v1.endpoints.analytics import salary_insights as si
    monkeypatch.setattr(si, "build_metadata", lambda *a, **kw: _fake_metadata())

    response = await _get("/api/v1/analytics/salary-insights?experience_level=senior")

    assert response.status_code == 200
