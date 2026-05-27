"""GET /analytics/comparison - compare a resume to market trends."""
from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id, get_db, get_redis_client
from app.db.queries.analytics_queries import (
    COMPARISON_CACHE_TTL_SECONDS,
    build_cache_key,
    build_metadata,
    error_response,
    get_or_cache,
    ok_response,
    rows_to_dicts,
    safe_execute,
)
from app.schemas.analytics import AnalyticsResponse, ResumeComparison

router = APIRouter()


@router.get("/comparison", response_model=AnalyticsResponse[ResumeComparison])
def get_comparison(
    resume_id: str = Query(...),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client=Depends(get_redis_client),
) -> AnalyticsResponse[ResumeComparison] | JSONResponse:
    try:
        resume_uuid = uuid.UUID(resume_id)
    except ValueError:
        return error_response(400, "INVALID_PARAMS", "resume_id must be a valid UUID", {"resume_id": resume_id})

    def fetch() -> AnalyticsResponse[ResumeComparison] | JSONResponse:
        resume = db.execute(
            text("SELECT id, title, content, user_id FROM public.cvs WHERE id = :resume_id"),
            {"resume_id": str(resume_uuid)},
        ).fetchone()
        if resume is None:
            return error_response(404, "NOT_FOUND", "Resume not found", {"resume_id": str(resume_uuid)})
        resume_data = dict(resume._mapping)
        if str(resume_data["user_id"]) != str(current_user_id):
            return error_response(403, "FORBIDDEN", "Resume belongs to a different user")

        def query() -> dict[str, Any]:
            skills = rows_to_dicts(db.execute(
                text("""
                    SELECT
                        skill_name,
                        total_job_mentions,
                        mentions_this_week,
                        mentions_last_week,
                        COALESCE(trending_score_pct, 0) AS trending_score_pct,
                        avg_salary_min,
                        avg_salary_max,
                        CASE
                            WHEN trending_score_pct > 5 THEN 'up'
                            WHEN trending_score_pct < -5 THEN 'down'
                            ELSE 'stable'
                        END AS trend,
                        RANK() OVER (ORDER BY total_job_mentions DESC) AS market_demand_rank
                    FROM analytics.dim_skills
                    ORDER BY total_job_mentions DESC
                """)
            ).fetchall())
            content = (resume_data.get("content") or "").lower()
            matched_skill_rows = [
                skill for skill in skills
                if re.search(rf"(?<!\w){re.escape(str(skill['skill_name']).lower())}(?!\w)", content)
            ]
            matched_names = [str(skill["skill_name"]) for skill in matched_skill_rows]
            matched_name_set = {name.lower() for name in matched_names}
            missing = [
                str(skill["skill_name"])
                for skill in skills[:20]
                if str(skill["skill_name"]).lower() not in matched_name_set
            ]
            salary_benchmark = _salary_benchmark(db, matched_names)
            total_skills = max(len(skills), 1)
            demand_scores = [
                1 - (int(skill["market_demand_rank"]) - 1) / total_skills
                for skill in matched_skill_rows
            ]
            demand_score = sum(demand_scores) / len(demand_scores) if demand_scores else 0.0
            coverage = len(matched_skill_rows) / max(len(matched_names), 1)
            return {
                "resume_id": str(resume_uuid),
                "resume_title": resume_data.get("title") or "Resume",
                "resume_skill_count": len(matched_names),
                "matched_skills": matched_names,
                "missing_high_demand_skills": missing,
                "skill_details": [
                    {
                        "skill": row["skill_name"],
                        "in_resume": True,
                        "market_demand_rank": row["market_demand_rank"],
                        "total_market_mentions": row["total_job_mentions"],
                        "trending_score_pct": row["trending_score_pct"],
                        "avg_salary_min": row["avg_salary_min"],
                        "avg_salary_max": row["avg_salary_max"],
                        "trend": row["trend"],
                    }
                    for row in matched_skill_rows
                ],
                "market_salary_benchmark": salary_benchmark,
                "skills_market_coverage_pct": round(coverage * 100, 1),
                "overall_market_alignment_score": round((coverage * 0.4 + demand_score * 0.6) * 100, 1),
            }

        data = get_or_cache(
            redis_client,
            build_cache_key("comparison", user_id=current_user_id, resume_id=str(resume_uuid)),
            COMPARISON_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(db, "analytics.dim_skills", {"resume_id": str(resume_uuid)})
        return ok_response(data, metadata)

    return safe_execute(fetch)


def _salary_benchmark(db: Session, skills: list[str]) -> dict[str, Any] | None:
    if not skills:
        return None
    rows = rows_to_dicts(db.execute(
        text("""
            SELECT
                p25_salary,
                p50_salary,
                p75_salary,
                p90_salary,
                avg_salary,
                min_salary_floor,
                max_salary_ceiling,
                job_count
            FROM analytics.agg_salary_insights
            WHERE breakdown_type = 'skill'
              AND lower(breakdown_value) = ANY(CAST(:skills AS text[]))
        """),
        {"skills": [skill.lower() for skill in skills]},
    ).fetchall())
    if not rows:
        return None
    total_weight = sum(int(row.get("job_count") or 0) for row in rows) or len(rows)

    def weighted(field: str) -> int | None:
        values = [(row.get(field), int(row.get("job_count") or 1)) for row in rows if row.get(field) is not None]
        if not values:
            return None
        return round(sum(float(value) * weight for value, weight in values) / sum(weight for _, weight in values))

    return {
        "dimension_type": "skills_blend",
        "dimension_value": "resume_skills",
        "p25_salary": weighted("p25_salary"),
        "p50_salary": weighted("p50_salary"),
        "p75_salary": weighted("p75_salary"),
        "p90_salary": weighted("p90_salary"),
        "avg_salary": weighted("avg_salary"),
        "min_salary_floor": min((row["min_salary_floor"] for row in rows if row.get("min_salary_floor") is not None), default=None),
        "max_salary_ceiling": max((row["max_salary_ceiling"] for row in rows if row.get("max_salary_ceiling") is not None), default=None),
        "job_count": total_weight,
    }
