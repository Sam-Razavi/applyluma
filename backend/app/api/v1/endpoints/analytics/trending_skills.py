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
            rows = db.execute(
                text("""
                    SELECT
                        skill_name AS skill,
                        total_job_mentions AS frequency,
                        ROUND(total_job_mentions * 100.0 / NULLIF(
                            (SELECT SUM(total_job_mentions) FROM analytics.dim_skills), 0
                        ), 2) AS frequency_pct,
                        avg_salary_min,
                        avg_salary_max,
                        COALESCE(trending_score_pct, 0) AS trending_score_pct,
                        CASE
                            WHEN trending_score_pct > 5 THEN 'up'
                            WHEN trending_score_pct < -5 THEN 'down'
                            ELSE 'stable'
                        END AS trend
                    FROM analytics.dim_skills
                    WHERE total_job_mentions >= :min_jobs
                    ORDER BY total_job_mentions DESC
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
            "analytics.dim_skills",
            {"limit": limit, "min_jobs": min_jobs},
        )
        return ok_response(data, metadata)

    return safe_execute(fetch)
