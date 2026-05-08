"""GET /analytics/skill-demand - fastest-growing skills."""
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
    _: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[list[SkillDemand]] | JSONResponse:
    if error := validate_int(limit, "limit", 1, 100):
        return error
    if error := validate_float(min_growth_pct, "min_growth_pct", -100.0, 10_000.0):
        return error

    def fetch() -> AnalyticsResponse[list[SkillDemand]]:
        def query() -> list[dict]:
            rows = db.execute(
                text("""
                    SELECT
                        skill_name AS skill,
                        total_job_mentions AS total_mentions,
                        mentions_this_week,
                        mentions_last_week,
                        COALESCE(trending_score_pct, 0) AS trending_score_pct,
                        avg_salary_min,
                        avg_salary_max,
                        CASE
                            WHEN trending_score_pct > 5 THEN 'up'
                            WHEN trending_score_pct < -5 THEN 'down'
                            ELSE 'stable'
                        END AS trend
                    FROM analytics.dim_skills
                    WHERE COALESCE(trending_score_pct, 0) >= :min_growth_pct
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
        metadata = build_metadata(db, "analytics.dim_skills", {"limit": limit, "min_growth_pct": min_growth_pct})
        return ok_response(data, metadata)

    return safe_execute(fetch)
