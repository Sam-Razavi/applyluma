"""GET /analytics/trending-skills - most demanded skills."""
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
    ok_response,
    rows_to_dicts,
    safe_execute,
    validate_int,
)
from app.schemas.analytics import AnalyticsResponse, SkillTrend

router = APIRouter()


@router.get("/trending-skills", response_model=AnalyticsResponse[list[SkillTrend]])
def get_trending_skills(
    limit: int = Query(20),
    min_jobs: int = Query(10),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[SkillTrend]] | JSONResponse:
    if error := validate_int(limit, "limit", 1, 100):
        return error
    if error := validate_int(min_jobs, "min_jobs", 1, 10_000):
        return error

    def fetch() -> AnalyticsResponse[list[SkillTrend]]:
        def query() -> list[dict]:
            # Live skill demand from raw_job_postings.extracted_skills with a
            # week-over-week trend (mirrors the legacy /top-skills query).
            rows = db.execute(
                text("""
                    WITH skill_counts AS (
                        SELECT
                            skill,
                            COUNT(*) AS total_count,
                            COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '7 days') AS this_week,
                            COUNT(*) FILTER (
                                WHERE scraped_at >= NOW() - INTERVAL '14 days'
                                  AND scraped_at <  NOW() - INTERVAL '7 days'
                            ) AS last_week
                        FROM raw_job_postings,
                             jsonb_array_elements_text(extracted_skills) AS skill
                        WHERE NOT is_duplicate
                          AND extracted_skills IS NOT NULL
                          AND jsonb_typeof(extracted_skills) = 'array'
                        GROUP BY skill
                    )
                    SELECT
                        skill,
                        total_count AS frequency,
                        ROUND(total_count * 100.0 / NULLIF(
                            (SELECT SUM(total_count) FROM skill_counts), 0
                        ), 2) AS frequency_pct,
                        NULL AS avg_salary_min,
                        NULL AS avg_salary_max,
                        CASE
                            WHEN last_week = 0 THEN (CASE WHEN this_week > 0 THEN 100.0 ELSE 0.0 END)
                            ELSE ROUND((this_week - last_week) * 100.0 / last_week, 1)
                        END AS trending_score_pct,
                        CASE
                            WHEN last_week = 0 AND this_week > 0 THEN 'up'
                            WHEN this_week > last_week * 1.1 THEN 'up'
                            WHEN this_week < last_week * 0.9 THEN 'down'
                            ELSE 'stable'
                        END AS trend
                    FROM skill_counts
                    WHERE total_count >= :min_jobs
                    ORDER BY total_count DESC
                    LIMIT :limit
                """),
                {"limit": limit, "min_jobs": min_jobs},
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(
            redis_client,
            build_cache_key("trending_skills", limit=limit, min_jobs=min_jobs),
            ANALYTICS_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(
            db,
            "public.raw_job_postings",
            {"limit": limit, "min_jobs": min_jobs},
        )
        return ok_response(data, metadata)

    return safe_execute(fetch)
