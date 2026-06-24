"""GET /analytics/hiring-patterns - hiring trend time series."""
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
    invalid_params,
    ok_response,
    rows_to_dicts,
    safe_execute,
    validate_int,
)
from app.schemas.analytics import AnalyticsResponse, Granularity, HiringPatternPoint

router = APIRouter()


@router.get("/hiring-patterns", response_model=AnalyticsResponse[list[HiringPatternPoint]])
def get_hiring_patterns(
    days_back: int = Query(90),
    granularity: str = Query("daily"),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[HiringPatternPoint]] | JSONResponse:
    if error := validate_int(days_back, "days_back", 7, 365):
        return error
    if granularity not in {item.value for item in Granularity}:
        return invalid_params("granularity must be daily, weekly, or monthly", {"granularity": granularity})

    def fetch() -> AnalyticsResponse[list[HiringPatternPoint]]:
        def query() -> list[dict]:
            # Live time series from the scraping landing table (grouped by
            # scraped_at). avg_salary is null until a salary data source exists.
            if granularity == "daily":
                period_expr = "DATE(scraped_at)"
                period_select = "DATE(scraped_at)::text"
            elif granularity == "weekly":
                period_expr = "DATE_TRUNC('week', scraped_at)"
                period_select = "TO_CHAR(DATE_TRUNC('week', scraped_at), 'IYYY-\"W\"IW')"
            else:
                period_expr = "DATE_TRUNC('month', scraped_at)"
                period_select = "TO_CHAR(DATE_TRUNC('month', scraped_at), 'YYYY-MM')"

            sql = f"""
                SELECT
                    {period_select} AS period,
                    COUNT(*) AS job_count,
                    COUNT(*) FILTER (WHERE remote_allowed) AS remote_count,
                    COALESCE(ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS remote_percentage,
                    NULL AS avg_salary
                FROM raw_job_postings
                WHERE NOT is_duplicate
                  AND scraped_at >= CURRENT_DATE - (:days_back * INTERVAL '1 day')
                GROUP BY {period_expr}
                ORDER BY {period_expr}
            """
            return rows_to_dicts(db.execute(text(sql), {"days_back": days_back}).fetchall())

        data = get_or_cache(
            redis_client,
            build_cache_key("hiring_patterns", days_back=days_back, granularity=granularity),
            ANALYTICS_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(
            db,
            "public.raw_job_postings",
            {"days_back": days_back, "granularity": granularity},
        )
        return ok_response(data, metadata)

    return safe_execute(fetch)
