"""GET /analytics/job-type-mix - employment and remote mix."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id, get_db, get_redis_client
from app.db.queries.analytics_queries import (
    ANALYTICS_CACHE_TTL_SECONDS,
    build_cache_key,
    build_metadata,
    get_or_cache,
    ok_response,
    rows_to_dicts,
    safe_execute,
)
from app.schemas.analytics import AnalyticsResponse, JobTypeMixItem

router = APIRouter()


@router.get("/job-type-mix", response_model=AnalyticsResponse[list[JobTypeMixItem]])
def get_job_type_mix(
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[JobTypeMixItem]] | JSONResponse:
    def fetch() -> AnalyticsResponse[list[JobTypeMixItem]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_postings)
                    SELECT
                        COALESCE(employment_type, 'unknown') AS job_type,
                        CASE WHEN remote_allowed THEN 'remote' ELSE 'on-site' END AS remote_label,
                        COUNT(*) AS job_count,
                        ROUND(COUNT(*) * 100.0 / NULLIF((SELECT n FROM total), 0), 2) AS pct_of_total,
                        ROUND(AVG(salary_min) FILTER (WHERE salary_min IS NOT NULL)) AS avg_salary_min,
                        ROUND(AVG(salary_max) FILTER (WHERE salary_max IS NOT NULL)) AS avg_salary_max
                    FROM analytics.fct_job_postings
                    GROUP BY employment_type, remote_allowed
                    ORDER BY job_count DESC
                """)
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(redis_client, build_cache_key("job_type_mix"), ANALYTICS_CACHE_TTL_SECONDS, query)
        metadata = build_metadata(db, "analytics.fct_job_postings", {})
        return ok_response(data, metadata)

    return safe_execute(fetch)
