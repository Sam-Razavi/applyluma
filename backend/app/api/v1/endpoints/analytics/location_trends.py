"""GET /analytics/location-trends - hiring distribution by location."""
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
    rows_to_dicts,
    safe_execute,
)
from app.schemas.analytics import AnalyticsResponse, LocationTrend

router = APIRouter()


@router.get("/location-trends", response_model=AnalyticsResponse[list[LocationTrend]])
def get_location_trends(
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[LocationTrend]] | JSONResponse:
    def fetch() -> AnalyticsResponse[list[LocationTrend]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    WITH totals AS (
                        SELECT COUNT(*) AS grand_total FROM analytics.fct_job_postings
                    ),
                    by_location AS (
                        SELECT
                            location,
                            COUNT(*) AS job_count,
                            ROUND(COUNT(*) * 100.0 / NULLIF((SELECT grand_total FROM totals), 0), 2) AS pct_of_total,
                            ROUND(AVG(salary_midpoint) FILTER (WHERE salary_midpoint IS NOT NULL)) AS avg_salary_midpoint,
                            ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / NULLIF(COUNT(*), 0), 1) AS remote_percentage
                        FROM analytics.fct_job_postings
                        WHERE location IS NOT NULL AND location != 'Unknown'
                        GROUP BY location
                    )
                    SELECT * FROM by_location ORDER BY job_count DESC LIMIT 30
                """)
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(redis_client, build_cache_key("location_trends"), ANALYTICS_CACHE_TTL_SECONDS, query)
        metadata = build_metadata(db, "analytics.fct_job_postings", {})
        return ok_response(data, metadata)

    return safe_execute(fetch)
