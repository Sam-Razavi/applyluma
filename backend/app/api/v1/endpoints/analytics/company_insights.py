"""GET /analytics/company-insights - top companies by hiring volume."""
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
    non_default_filters,
    ok_response,
    rows_to_dicts,
    safe_execute,
    validate_int,
    validate_optional_text,
)
from app.schemas.analytics import AnalyticsResponse, CompanyInsight

router = APIRouter()


@router.get("/company-insights", response_model=AnalyticsResponse[list[CompanyInsight]])
def get_company_insights(
    limit: int = Query(20),
    location: str | None = Query(None),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[CompanyInsight]] | JSONResponse:
    if error := validate_int(limit, "limit", 1, 100):
        return error
    if error := validate_optional_text(location, "location"):
        return error

    def fetch() -> AnalyticsResponse[list[CompanyInsight]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    SELECT
                        dc.company_name,
                        dc.total_jobs_posted AS total_jobs,
                        dc.remote_jobs,
                        dc.remote_percentage,
                        dc.avg_salary_min,
                        dc.avg_salary_max,
                        dc.most_common_employment_type,
                        dc.first_seen_date::text,
                        dc.last_seen_date::text,
                        COALESCE(ROUND(
                            dc.total_jobs_posted::numeric
                            / NULLIF((dc.last_seen_date - dc.first_seen_date) / 7.0, 0),
                            2
                        ), dc.total_jobs_posted::numeric) AS hiring_velocity
                    FROM analytics.dim_companies dc
                    WHERE (:location IS NULL OR dc.company_name IN (
                        SELECT DISTINCT company_name
                        FROM analytics.fct_job_postings
                        WHERE location ILIKE '%' || :location || '%'
                    ))
                    ORDER BY dc.total_jobs_posted DESC
                    LIMIT :limit
                """),
                {"limit": limit, "location": location},
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(
            redis_client,
            build_cache_key("company_insights", limit=limit, location=location),
            ANALYTICS_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(
            db,
            "analytics.dim_companies",
            non_default_filters({"limit": limit, "location": location}, {"limit": 20, "location": None}),
        )
        return ok_response(data, metadata)

    return safe_execute(fetch)
