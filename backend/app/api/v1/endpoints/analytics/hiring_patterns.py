"""GET /analytics/hiring-patterns - hiring trend time series."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id, get_db, get_redis_client
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
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[HiringPatternPoint]] | JSONResponse:
    if error := validate_int(days_back, "days_back", 7, 365):
        return error
    if granularity not in {item.value for item in Granularity}:
        return invalid_params("granularity must be daily, weekly, or monthly", {"granularity": granularity})

    def fetch() -> AnalyticsResponse[list[HiringPatternPoint]]:
        def query() -> list[dict]:
            if granularity == "daily":
                sql = """
                    SELECT metric_date::text AS period, total_jobs AS job_count,
                           remote_jobs AS remote_count, remote_percentage,
                           avg_salary_midpoint AS avg_salary
                    FROM analytics.fct_daily_metrics
                    WHERE metric_date >= CURRENT_DATE - (:days_back * INTERVAL '1 day')
                    ORDER BY metric_date
                """
            elif granularity == "weekly":
                sql = """
                    SELECT TO_CHAR(DATE_TRUNC('week', metric_date), 'IYYY-"W"IW') AS period,
                           SUM(total_jobs) AS job_count, SUM(remote_jobs) AS remote_count,
                           ROUND(AVG(remote_percentage), 1) AS remote_percentage,
                           ROUND(AVG(avg_salary_midpoint)) AS avg_salary
                    FROM analytics.fct_daily_metrics
                    WHERE metric_date >= CURRENT_DATE - (:days_back * INTERVAL '1 day')
                    GROUP BY DATE_TRUNC('week', metric_date)
                    ORDER BY DATE_TRUNC('week', metric_date)
                """
            else:
                sql = """
                    SELECT TO_CHAR(DATE_TRUNC('month', metric_date), 'YYYY-MM') AS period,
                           SUM(total_jobs) AS job_count, SUM(remote_jobs) AS remote_count,
                           ROUND(AVG(remote_percentage), 1) AS remote_percentage,
                           ROUND(AVG(avg_salary_midpoint)) AS avg_salary
                    FROM analytics.fct_daily_metrics
                    WHERE metric_date >= CURRENT_DATE - (:days_back * INTERVAL '1 day')
                    GROUP BY DATE_TRUNC('month', metric_date)
                    ORDER BY DATE_TRUNC('month', metric_date)
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
            "analytics.fct_daily_metrics",
            {"days_back": days_back, "granularity": granularity},
        )
        return ok_response(data, metadata)

    return safe_execute(fetch)
