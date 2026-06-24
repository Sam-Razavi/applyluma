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
            # Live company aggregation from the scraping landing table.
            rows = db.execute(
                text("""
                    SELECT
                        company AS company_name,
                        COUNT(*) AS total_jobs,
                        COUNT(*) FILTER (WHERE remote_allowed) AS remote_jobs,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS remote_percentage,
                        NULL AS avg_salary_min,
                        NULL AS avg_salary_max,
                        MODE() WITHIN GROUP (ORDER BY employment_type) AS most_common_employment_type,
                        MIN(scraped_at)::date::text AS first_seen_date,
                        MAX(scraped_at)::date::text AS last_seen_date,
                        COALESCE(ROUND(
                            COUNT(*)::numeric
                            / NULLIF((MAX(scraped_at)::date - MIN(scraped_at)::date) / 7.0, 0),
                            2
                        ), COUNT(*)::numeric) AS hiring_velocity
                    FROM raw_job_postings
                    WHERE NOT is_duplicate
                      AND (:location IS NULL OR location ILIKE '%' || :location || '%')
                    GROUP BY company
                    ORDER BY total_jobs DESC
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
            "public.raw_job_postings",
            non_default_filters({"limit": limit, "location": location}, {"limit": 20, "location": None}),
        )
        return ok_response(data, metadata)

    return safe_execute(fetch)
