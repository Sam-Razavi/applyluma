"""GET /analytics/experience-levels - jobs by seniority."""
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
from app.schemas.analytics import AnalyticsResponse, ExperienceLevelBreakdown

router = APIRouter()


@router.get("/experience-levels", response_model=AnalyticsResponse[list[ExperienceLevelBreakdown]])
def get_experience_levels(
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[ExperienceLevelBreakdown]] | JSONResponse:
    def fetch() -> AnalyticsResponse[list[ExperienceLevelBreakdown]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    WITH total AS (SELECT COUNT(*) AS n FROM analytics.fct_job_postings),
                    classified AS (
                        SELECT
                            CASE
                                WHEN is_management_role THEN 'management'
                                WHEN is_senior_role THEN 'senior'
                                WHEN is_junior_role THEN 'junior'
                                ELSE 'mid'
                            END AS level,
                            salary_min,
                            salary_max,
                            remote_allowed
                        FROM analytics.fct_job_postings
                    )
                    SELECT
                        level,
                        COUNT(*) AS job_count,
                        ROUND(COUNT(*) * 100.0 / NULLIF((SELECT n FROM total), 0), 2) AS pct_of_total,
                        ROUND(AVG(salary_min) FILTER (WHERE salary_min IS NOT NULL)) AS avg_salary_min,
                        ROUND(AVG(salary_max) FILTER (WHERE salary_max IS NOT NULL)) AS avg_salary_max,
                        COALESCE(ROUND(COUNT(*) FILTER (WHERE remote_allowed) * 100.0 / NULLIF(COUNT(*), 0), 1), 0) AS remote_percentage
                    FROM classified
                    GROUP BY level
                    ORDER BY job_count DESC
                """)
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(redis_client, build_cache_key("experience_levels"), ANALYTICS_CACHE_TTL_SECONDS, query)
        metadata = build_metadata(db, "analytics.fct_job_postings", {})
        return ok_response(data, metadata)

    return safe_execute(fetch)
