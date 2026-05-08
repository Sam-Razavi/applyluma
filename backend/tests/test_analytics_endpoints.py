from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.dependencies import get_current_user_id, get_db, get_redis_client
from app.main import app

USER_ID = "e98457aa-987c-4bc6-97ca-679dfacec5a7"
RESUME_ID = "5a601f4f-ae42-4287-ae01-a20dac3293b0"


class FakeRow:
    def __init__(self, **values: Any) -> None:
        self._mapping = values

    def __getattr__(self, name: str) -> Any:
        return self._mapping[name]


class FakeResult:
    def __init__(self, rows: list[FakeRow] | None = None, scalar_value: Any = None) -> None:
        self.rows = rows or []
        self.scalar_value = scalar_value

    def fetchall(self) -> list[FakeRow]:
        return self.rows

    def fetchone(self) -> FakeRow | None:
        return self.rows[0] if self.rows else None

    def scalar(self) -> Any:
        return self.scalar_value


class FakeRedis:
    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self.store = initial or {}
        self.set_count = 0

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.set_count += 1
        self.store[key] = value

    def incr(self, key: str) -> int:
        value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(value)
        return value

    def expire(self, key: str, seconds: int) -> None:
        return None


class FakeDb:
    def __init__(self, mode: str = "happy") -> None:
        self.mode = mode
        self.calls = 0

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        self.calls += 1
        if self.mode == "error":
            raise SQLAlchemyError("boom")

        sql = str(statement).lower()
        if "count(*) from" in sql:
            return FakeResult(scalar_value=3)
        if "max(dbt_updated_at)" in sql or "max(updated_at)" in sql:
            return FakeResult(scalar_value=None)

        if "from public.cvs" in sql:
            return FakeResult([
                FakeRow(id=uuid.UUID(RESUME_ID), title="Backend CV", content="Python SQL Docker", user_id=uuid.UUID(USER_ID))
            ])

        if self.mode == "empty":
            if "count(distinct job_id)" in sql and "from analytics.fct_job_postings" in sql and "group by" not in sql:
                return FakeResult([FakeRow(
                    total_jobs=0,
                    unique_companies=0,
                    remote_percentage=0,
                    avg_salary_midpoint=None,
                    senior_role_pct=0,
                    junior_role_pct=0,
                    management_role_pct=0,
                    avg_skills_per_job=0,
                    data_date_range_days=0,
                    last_updated=None,
                )])
            return FakeResult([])

        if "from analytics.dim_skills" in sql and "rank() over" in sql:
            return FakeResult([
                FakeRow(skill_name="Python", total_job_mentions=100, mentions_this_week=20, mentions_last_week=10, trending_score_pct=100.0, avg_salary_min=70000, avg_salary_max=110000, trend="up", market_demand_rank=1),
                FakeRow(skill_name="SQL", total_job_mentions=80, mentions_this_week=12, mentions_last_week=10, trending_score_pct=20.0, avg_salary_min=65000, avg_salary_max=95000, trend="up", market_demand_rank=2),
                FakeRow(skill_name="Kubernetes", total_job_mentions=70, mentions_this_week=8, mentions_last_week=8, trending_score_pct=0.0, avg_salary_min=80000, avg_salary_max=120000, trend="stable", market_demand_rank=3),
            ])
        if "from analytics.dim_skills" in sql and "total_mentions" in sql:
            return FakeResult([FakeRow(skill="Python", total_mentions=100, mentions_this_week=20, mentions_last_week=10, trending_score_pct=100.0, avg_salary_min=70000, avg_salary_max=110000, trend="up")])
        if "from analytics.dim_skills" in sql:
            return FakeResult([FakeRow(skill="Python", frequency=100, frequency_pct=33.3, avg_salary_min=70000, avg_salary_max=110000, trending_score_pct=100.0, trend="up")])
        if "from analytics.agg_salary_insights" in sql and "breakdown_type = 'skill'" in sql:
            return FakeResult([FakeRow(skill="Python", breakdown_value="Python", avg_salary=90000, p25_salary=70000, p50_salary=85000, p75_salary=105000, p90_salary=130000, min_salary_floor=50000, max_salary_ceiling=160000, job_count=100)])
        if "from analytics.agg_salary_insights" in sql:
            return FakeResult([FakeRow(dimension_type="location", dimension_value="London", p25_salary=60000, p50_salary=80000, p75_salary=100000, p90_salary=130000, avg_salary=85000, min_salary_floor=40000, max_salary_ceiling=150000, job_count=25)])
        if "from analytics.fct_daily_metrics" in sql:
            return FakeResult([FakeRow(period="2026-05-01", job_count=10, remote_count=4, remote_percentage=40.0, avg_salary=80000)])
        if "from analytics.dim_companies" in sql:
            return FakeResult([FakeRow(company_name="Acme", total_jobs=10, remote_jobs=4, remote_percentage=40.0, avg_salary_min=60000, avg_salary_max=90000, most_common_employment_type="full_time", first_seen_date="2026-01-01", last_seen_date="2026-05-01", hiring_velocity=1.2)])
        if "count(distinct job_id)" in sql and "from analytics.fct_job_postings" in sql and "group by" not in sql:
            return FakeResult([FakeRow(total_jobs=30, unique_companies=7, remote_percentage=40.0, avg_salary_midpoint=85000, senior_role_pct=20.0, junior_role_pct=10.0, management_role_pct=5.0, avg_skills_per_job=4.2, data_date_range_days=30, last_updated=None)])
        if "by_location" in sql:
            return FakeResult([FakeRow(location="London", job_count=10, pct_of_total=33.3, avg_salary_midpoint=85000, remote_percentage=40.0)])
        if "classified" in sql and "industry" in sql:
            return FakeResult([FakeRow(industry="Software Engineering", job_count=10, pct_of_total=33.3, avg_salary_min=60000, avg_salary_max=90000, remote_percentage=40.0)])
        if "classified" in sql and "level" in sql:
            return FakeResult([FakeRow(level="mid", job_count=10, pct_of_total=33.3, avg_salary_min=60000, avg_salary_max=90000, remote_percentage=40.0)])
        if "employment_type" in sql and "remote_label" in sql:
            return FakeResult([FakeRow(job_type="full_time", remote_label="remote", job_count=10, pct_of_total=33.3, avg_salary_min=60000, avg_salary_max=90000)])
        if "salary_midpoint is not null" in sql:
            return FakeResult([FakeRow(dimension_type="overall", dimension_value="all", p25_salary=60000, p50_salary=80000, p75_salary=100000, p90_salary=130000, avg_salary=85000, min_salary_floor=40000, max_salary_ceiling=150000, job_count=25)])
        return FakeResult([])


@dataclass(frozen=True)
class EndpointCase:
    path: str
    invalid_path: str
    cache_prefix: str
    cached_data: Any


ENDPOINTS = [
    EndpointCase("/api/v1/analytics/trending-skills", "/api/v1/analytics/trending-skills?limit=0", "analytics:trending_skills", [{"skill": "Python", "frequency": 1, "frequency_pct": 10.0, "avg_salary_min": None, "avg_salary_max": None, "trending_score_pct": 0.0, "trend": "stable"}]),
    EndpointCase("/api/v1/analytics/salary-insights", "/api/v1/analytics/salary-insights?location=" + "x" * 201, "analytics:salary_insights", []),
    EndpointCase("/api/v1/analytics/hiring-patterns", "/api/v1/analytics/hiring-patterns?days_back=1", "analytics:hiring_patterns", []),
    EndpointCase("/api/v1/analytics/company-insights", "/api/v1/analytics/company-insights?limit=0", "analytics:company_insights", []),
    EndpointCase("/api/v1/analytics/job-market-health", "/api/v1/analytics/job-market-health", "analytics:job_market_health", {"total_jobs": 0, "unique_companies": 0, "remote_percentage": 0, "avg_salary_midpoint": None, "senior_role_pct": 0, "junior_role_pct": 0, "management_role_pct": 0, "mid_role_pct": 100, "avg_skills_per_job": 0, "data_date_range_days": 0, "last_updated": None}),
    EndpointCase("/api/v1/analytics/skill-demand", "/api/v1/analytics/skill-demand?limit=0", "analytics:skill_demand", []),
    EndpointCase("/api/v1/analytics/location-trends", "/api/v1/analytics/location-trends", "analytics:location_trends", []),
    EndpointCase("/api/v1/analytics/industry-breakdown", "/api/v1/analytics/industry-breakdown", "analytics:industry_breakdown", []),
    EndpointCase("/api/v1/analytics/experience-levels", "/api/v1/analytics/experience-levels", "analytics:experience_levels", []),
    EndpointCase("/api/v1/analytics/job-type-mix", "/api/v1/analytics/job-type-mix", "analytics:job_type_mix", []),
    EndpointCase("/api/v1/analytics/salary-by-skill", "/api/v1/analytics/salary-by-skill?limit=0", "analytics:salary_by_skill", []),
    EndpointCase(f"/api/v1/analytics/comparison?resume_id={RESUME_ID}", "/api/v1/analytics/comparison?resume_id=bad", "analytics:comparison", {"resume_id": RESUME_ID, "resume_title": "Backend CV", "resume_skill_count": 0, "matched_skills": [], "missing_high_demand_skills": [], "skill_details": [], "market_salary_benchmark": None, "skills_market_coverage_pct": 0, "overall_market_alignment_score": 0}),
]


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def current_user_override() -> str:
    return USER_ID


async def request(path: str, db: FakeDb, redis_client: FakeRedis | None = None) -> httpx.Response:
    app.dependency_overrides[get_current_user_id] = current_user_override
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis_client] = lambda: redis_client or FakeRedis()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, headers={"Authorization": "Bearer invalid-test-token"})


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ENDPOINTS)
async def test_analytics_endpoint_happy_path(case: EndpointCase) -> None:
    response = await request(case.path, FakeDb())
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["metadata"]["sample_size"] == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ENDPOINTS)
async def test_analytics_endpoint_validation(case: EndpointCase) -> None:
    if case.invalid_path == case.path:
        pytest.skip("endpoint has no query params to validate")
    response = await request(case.invalid_path, FakeDb())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ENDPOINTS)
async def test_analytics_endpoint_empty_result(case: EndpointCase) -> None:
    response = await request(case.path, FakeDb(mode="empty"))
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ENDPOINTS)
async def test_analytics_endpoint_cache_hit(case: EndpointCase) -> None:
    redis_client = FakeRedis({f"{case.cache_prefix}:cached": json.dumps(case.cached_data)})
    original_get = redis_client.get
    redis_client.get = lambda key: original_get(f"{case.cache_prefix}:cached") if key.startswith(case.cache_prefix) else None  # type: ignore[method-assign]
    response = await request(case.path, FakeDb(), redis_client)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert redis_client.set_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ENDPOINTS)
async def test_analytics_endpoint_db_error(case: EndpointCase) -> None:
    response = await request(case.path, FakeDb(mode="error"))
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
