"""GET /analytics/salary-by-skill - salary percentiles for top skills."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_redis_client
from app.db.queries.analytics_queries import (
    ANALYTICS_CACHE_TTL_SECONDS,
    build_cache_key,
    build_metadata,
    get_or_cache,
    ok_response,
    rows_to_dicts,
    safe_execute,
    validate_int,
)
from app.schemas.analytics import AnalyticsResponse, SalaryBySkill

router = APIRouter()


@router.get("/salary-by-skill", response_model=AnalyticsResponse[list[SalaryBySkill]])
def get_salary_by_skill(
    limit: int = Query(20),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[SalaryBySkill]] | JSONResponse:
    if error := validate_int(limit, "limit", 1, 100):
        return error

    def fetch() -> AnalyticsResponse[list[SalaryBySkill]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    SELECT
                        breakdown_value AS skill,
                        avg_salary,
                        p25_salary,
                        p50_salary,
                        p75_salary,
                        p90_salary,
                        min_salary_floor,
                        max_salary_ceiling,
                        job_count
                    FROM analytics.agg_salary_insights
                    WHERE breakdown_type = 'skill'
                    ORDER BY job_count DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(redis_client, build_cache_key("salary_by_skill", limit=limit), ANALYTICS_CACHE_TTL_SECONDS, query)
        metadata = build_metadata(db, "analytics.agg_salary_insights", {"limit": limit})
        return ok_response(data, metadata)

    return safe_execute(fetch)
