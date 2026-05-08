"""GET /analytics/salary-insights - salary percentiles by filters."""
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
    non_default_filters,
    ok_response,
    rows_to_dicts,
    safe_execute,
    validate_optional_text,
)
from app.schemas.analytics import AnalyticsResponse, ExperienceLevel, SalaryInsightItem

router = APIRouter()


@router.get("/salary-insights", response_model=AnalyticsResponse[list[SalaryInsightItem]])
def get_salary_insights(
    location: str | None = Query(None),
    job_title: str | None = Query(None),
    experience_level: str | None = Query(None),
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[SalaryInsightItem]] | JSONResponse:
    for value, field in ((location, "location"), (job_title, "job_title")):
        if error := validate_optional_text(value, field):
            return error
    if experience_level is not None and experience_level not in {level.value for level in ExperienceLevel}:
        return invalid_params(
            "experience_level must be one of junior, mid, senior, management",
            {"experience_level": f"received {experience_level}"},
        )

    filters = non_default_filters(
        {"location": location, "job_title": job_title, "experience_level": experience_level},
        {"location": None, "job_title": None, "experience_level": None},
    )

    def fetch() -> AnalyticsResponse[list[SalaryInsightItem]]:
        def query() -> list[dict]:
            if experience_level is None and job_title is None:
                rows = db.execute(
                    text("""
                        SELECT
                            'location' AS dimension_type,
                            breakdown_value AS dimension_value,
                            p25_salary,
                            p50_salary,
                            p75_salary,
                            p90_salary,
                            avg_salary,
                            min_salary_floor,
                            max_salary_ceiling,
                            job_count
                        FROM analytics.agg_salary_insights
                        WHERE breakdown_type = 'location'
                          AND (:location IS NULL OR breakdown_value ILIKE '%' || :location || '%')
                        ORDER BY job_count DESC
                        LIMIT 100
                    """),
                    {"location": location},
                ).fetchall()
                return rows_to_dicts(rows)

            dimension_type = (
                "experience_level" if experience_level else "job_title" if job_title else "location" if location else "overall"
            )
            dimension_value = experience_level or job_title or location or "all"
            rows = db.execute(
                text("""
                    SELECT
                        :dimension_type AS dimension_type,
                        :dimension_value AS dimension_value,
                        ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY salary_midpoint)) AS p25_salary,
                        ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY salary_midpoint)) AS p50_salary,
                        ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY salary_midpoint)) AS p75_salary,
                        ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY salary_midpoint)) AS p90_salary,
                        ROUND(AVG(salary_midpoint)) AS avg_salary,
                        ROUND(MIN(salary_min)) AS min_salary_floor,
                        ROUND(MAX(salary_max)) AS max_salary_ceiling,
                        COUNT(DISTINCT job_id) AS job_count
                    FROM analytics.fct_job_postings
                    WHERE salary_midpoint IS NOT NULL
                      AND (:location IS NULL OR location ILIKE '%' || :location || '%')
                      AND (:job_title IS NULL OR normalised_title ILIKE '%' || :job_title || '%')
                      AND (
                            :experience_level IS NULL
                            OR (:experience_level = 'senior' AND is_senior_role)
                            OR (:experience_level = 'junior' AND is_junior_role)
                            OR (:experience_level = 'management' AND is_management_role)
                            OR (:experience_level = 'mid'
                                AND NOT is_senior_role
                                AND NOT is_junior_role
                                AND NOT is_management_role)
                      )
                """),
                {
                    "dimension_type": dimension_type,
                    "dimension_value": dimension_value,
                    "location": location,
                    "job_title": job_title,
                    "experience_level": experience_level,
                },
            ).fetchall()
            data = rows_to_dicts(rows)
            return [] if not data or data[0].get("job_count", 0) == 0 else data

        data = get_or_cache(
            redis_client,
            build_cache_key("salary_insights", location=location, job_title=job_title, experience_level=experience_level),
            ANALYTICS_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(db, "analytics.agg_salary_insights", filters)
        return ok_response(data, metadata)

    return safe_execute(fetch)
