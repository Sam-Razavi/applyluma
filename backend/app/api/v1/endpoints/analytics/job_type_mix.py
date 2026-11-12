"""GET /analytics/job-type-mix - employment and remote mix."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_redis_client
from app.db.queries.analytics_queries import (
    ANALYTICS_CACHE_TTL_SECONDS,
    LIVE_POSTINGS_SQL,
    build_cache_key,
    build_metadata,
    get_or_cache,
    ok_response,
    rows_to_dicts,
    safe_execute,
)
from app.schemas.analytics import AnalyticsResponse, JobTypeMixItem

router = APIRouter()

# Sources name the same thing differently (Platsbanken "Heltid", Remotive
# "full_time"); without this each spelling is its own slice of the chart.
_JOB_TYPE_SQL = """
    CASE
        WHEN employment_type IS NULL OR btrim(employment_type) = '' THEN 'unknown'
        WHEN lower(btrim(employment_type)) IN ('heltid', 'full_time', 'full-time', 'full time', 'fulltime')
            THEN 'full_time'
        WHEN lower(btrim(employment_type)) IN ('deltid', 'part_time', 'part-time', 'part time', 'parttime')
            THEN 'part_time'
        WHEN lower(btrim(employment_type)) IN ('contract', 'contractor', 'freelance', 'temporary')
            THEN 'contract'
        WHEN lower(btrim(employment_type)) IN ('internship', 'intern', 'praktik')
            THEN 'internship'
        ELSE 'other'
    END
"""


@router.get("/job-type-mix", response_model=AnalyticsResponse[list[JobTypeMixItem]])
def get_job_type_mix(
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[JobTypeMixItem]] | JSONResponse:
    def fetch() -> AnalyticsResponse[list[JobTypeMixItem]]:
        def query() -> list[dict]:
            rows = db.execute(
                text(f"""
                    WITH total AS (
                        SELECT COUNT(*) AS n FROM raw_job_postings WHERE {LIVE_POSTINGS_SQL}
                    )
                    SELECT
                        {_JOB_TYPE_SQL} AS job_type,
                        CASE WHEN remote_allowed THEN 'remote' ELSE 'on-site' END AS remote_label,
                        COUNT(*) AS job_count,
                        ROUND(COUNT(*) * 100.0 / NULLIF((SELECT n FROM total), 0), 2) AS pct_of_total,
                        NULL AS avg_salary_min,
                        NULL AS avg_salary_max
                    FROM raw_job_postings
                    WHERE {LIVE_POSTINGS_SQL}
                    GROUP BY 1, remote_allowed
                    ORDER BY job_count DESC
                """)
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(redis_client, build_cache_key("job_type_mix"), ANALYTICS_CACHE_TTL_SECONDS, query)
        metadata = build_metadata(db, "public.raw_job_postings", {})
        return ok_response(data, metadata)

    return safe_execute(fetch)
