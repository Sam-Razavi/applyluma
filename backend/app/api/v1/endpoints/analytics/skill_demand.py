"""GET /analytics/skill-demand - fastest-growing skills."""
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
    validate_float,
    validate_int,
)
from app.schemas.analytics import AnalyticsResponse, SkillDemand

router = APIRouter()


@router.get("/skill-demand", response_model=AnalyticsResponse[list[SkillDemand]])
def get_skill_demand(
    limit: int = Query(20),
    min_growth_pct: float = Query(5.0),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[SkillDemand]] | JSONResponse:
    if error := validate_int(limit, "limit", 1, 100):
        return error
    if error := validate_float(min_growth_pct, "min_growth_pct", -100.0, 10_000.0):
        return error

    def fetch() -> AnalyticsResponse[list[SkillDemand]]:
        def query() -> list[dict]:
            # Live skill growth from raw_job_postings.extracted_skills (week-over-week).
            rows = db.execute(
                text("""
                    WITH skill_counts AS (
                        SELECT
                            skill,
                            COUNT(*) AS total_mentions,
                            COUNT(*) FILTER (WHERE scraped_at >= NOW() - INTERVAL '7 days') AS mentions_this_week,
                            COUNT(*) FILTER (
                                WHERE scraped_at >= NOW() - INTERVAL '14 days'
                                  AND scraped_at <  NOW() - INTERVAL '7 days'
                            ) AS mentions_last_week
                        FROM raw_job_postings,
                             jsonb_array_elements_text(extracted_skills) AS skill
                        WHERE NOT is_duplicate
                          AND extracted_skills IS NOT NULL
                          AND jsonb_typeof(extracted_skills) = 'array'
                        GROUP BY skill
                    ),
                    scored AS (
                        SELECT
                            skill AS skill,
                            total_mentions,
                            mentions_this_week,
                            mentions_last_week,
                            CASE
                                WHEN mentions_last_week = 0 THEN (CASE WHEN mentions_this_week > 0 THEN 100.0 ELSE 0.0 END)
                                ELSE ROUND((mentions_this_week - mentions_last_week) * 100.0 / mentions_last_week, 1)
                            END AS trending_score_pct
                        FROM skill_counts
                    )
                    SELECT
                        skill,
                        total_mentions,
                        mentions_this_week,
                        mentions_last_week,
                        trending_score_pct,
                        NULL AS avg_salary_min,
                        NULL AS avg_salary_max,
                        CASE
                            WHEN trending_score_pct > 5 THEN 'up'
                            WHEN trending_score_pct < -5 THEN 'down'
                            ELSE 'stable'
                        END AS trend
                    FROM scored
                    WHERE trending_score_pct >= :min_growth_pct
                    ORDER BY trending_score_pct DESC
                    LIMIT :limit
                """),
                {"limit": limit, "min_growth_pct": min_growth_pct},
            ).fetchall()
            return rows_to_dicts(rows)

        data = get_or_cache(
            redis_client,
            build_cache_key("skill_demand", limit=limit, min_growth_pct=min_growth_pct),
            ANALYTICS_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(db, "public.raw_job_postings", {"limit": limit, "min_growth_pct": min_growth_pct})
        return ok_response(data, metadata)

    return safe_execute(fetch)
