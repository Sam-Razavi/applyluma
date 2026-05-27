"""GET /analytics/job-market-health - overall market metrics."""
from __future__ import annotations

from fastapi import APIRouter, Depends
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
    safe_execute,
    to_jsonable,
)
from app.schemas.analytics import AnalyticsResponse, JobMarketHealth

router = APIRouter()


@router.get("/job-market-health", response_model=AnalyticsResponse[JobMarketHealth])
def get_job_market_health(
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[JobMarketHealth] | JSONResponse:
    def fetch() -> AnalyticsResponse[JobMarketHealth]:
        def query() -> dict:
            row = db.execute(
                text("""
                    SELECT
                        COUNT(DISTINCT job_id) AS total_jobs,
                        COUNT(DISTINCT company_name) AS unique_companies,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS remote_percentage,
                        ROUND(AVG(salary_midpoint) FILTER (WHERE salary_midpoint IS NOT NULL)) AS avg_salary_midpoint,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE is_senior_role) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS senior_role_pct,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE is_junior_role) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS junior_role_pct,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE is_management_role) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS management_role_pct,
                        COALESCE(ROUND(AVG(skill_count), 1), 0) AS avg_skills_per_job,
                        COALESCE((MAX(scrape_date) - MIN(scrape_date)), 0) AS data_date_range_days,
                        MAX(dbt_updated_at) AS last_updated
                    FROM analytics.fct_job_postings
                """)
            ).fetchone()
            data = to_jsonable(dict(row._mapping)) if row else {}
            data = {
                "total_jobs": int(data.get("total_jobs") or 0),
                "unique_companies": int(data.get("unique_companies") or 0),
                "remote_percentage": float(data.get("remote_percentage") or 0),
                "avg_salary_midpoint": data.get("avg_salary_midpoint"),
                "senior_role_pct": float(data.get("senior_role_pct") or 0),
                "junior_role_pct": float(data.get("junior_role_pct") or 0),
                "management_role_pct": float(data.get("management_role_pct") or 0),
                "avg_skills_per_job": float(data.get("avg_skills_per_job") or 0),
                "data_date_range_days": int(data.get("data_date_range_days") or 0),
                "last_updated": data.get("last_updated"),
            }
            senior = float(data.get("senior_role_pct") or 0)
            junior = float(data.get("junior_role_pct") or 0)
            management = float(data.get("management_role_pct") or 0)
            data["mid_role_pct"] = round(max(0.0, 100.0 - senior - junior - management), 1)
            return data

        data = get_or_cache(
            redis_client,
            build_cache_key("job_market_health"),
            ANALYTICS_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(db, "analytics.fct_job_postings", {})
        return ok_response(data, metadata)

    return safe_execute(fetch)
