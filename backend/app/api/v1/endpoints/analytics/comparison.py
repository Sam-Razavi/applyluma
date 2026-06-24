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
from app.services.keyword_extractor import KeywordExtractor

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
            # Top market skills computed live from raw_job_postings.extracted_skills.
            # We cap at the top N so the radar plots the most in-demand skills and
            # surfaces GAPS (in-demand skills the CV lacks) rather than only the
            # skills already on the CV (which made the resume fill every axis).
            top_n = 15
            skills = rows_to_dicts(db.execute(
                text("""
                    WITH skill_counts AS (
                        SELECT
                            skill,
                            COUNT(*) AS total_job_mentions,
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
                    )
                    SELECT
                        skill AS skill_name,
                        total_job_mentions,
                        mentions_this_week,
                        mentions_last_week,
                        CASE
                            WHEN mentions_last_week = 0 THEN (CASE WHEN mentions_this_week > 0 THEN 100.0 ELSE 0.0 END)
                            ELSE ROUND((mentions_this_week - mentions_last_week) * 100.0 / mentions_last_week, 1)
                        END AS trending_score_pct,
                        CASE
                            WHEN mentions_last_week = 0 AND mentions_this_week > 0 THEN 'up'
                            WHEN mentions_this_week > mentions_last_week * 1.1 THEN 'up'
                            WHEN mentions_this_week < mentions_last_week * 0.9 THEN 'down'
                            ELSE 'stable'
                        END AS trend,
                        RANK() OVER (ORDER BY COUNT(*) DESC) AS market_demand_rank
                    FROM skill_counts
                    ORDER BY total_job_mentions DESC
                    LIMIT :top_n
                """),
                {"top_n": top_n},
            ).fetchall())

            content_text = resume_data.get("content") or ""
            content = content_text.lower()
            keyword_extractor = KeywordExtractor(enable_nlp=False)
            resume_skill_names = list(dict.fromkeys(
                keyword_extractor.keywords_as_flat_list(
                    keyword_extractor.extract_keywords(content_text)
                )
            ))

            def _in_resume(name: str) -> bool:
                return bool(re.search(rf"(?<!\w){re.escape(name.lower())}(?!\w)", content))

            # Every top market skill becomes a radar axis, flagged in/out of the CV.
            skill_details = [
                {
                    "skill": str(row["skill_name"]),
                    "in_resume": _in_resume(str(row["skill_name"])),
                    "market_demand_rank": row["market_demand_rank"],
                    "total_market_mentions": row["total_job_mentions"],
                    "trending_score_pct": row["trending_score_pct"],
                    "avg_salary_min": None,
                    "avg_salary_max": None,
                    "trend": row["trend"],
                }
                for row in skills
            ]
            matched_names = [d["skill"] for d in skill_details if d["in_resume"]]
            missing = [d["skill"] for d in skill_details if not d["in_resume"]]

            n = max(len(skills), 1)
            matched_in_top = [d for d in skill_details if d["in_resume"]]
            # Demand score normalised within the top-N set (not the full universe),
            # so high-demand matches aren't artificially suppressed.
            demand_scores = [
                1 - (int(d["market_demand_rank"]) - 1) / n for d in matched_in_top
            ]
            demand_score = sum(demand_scores) / len(demand_scores) if demand_scores else 0.0
            coverage = len(matched_in_top) / n
            return {
                "resume_id": str(resume_uuid),
                "resume_title": resume_data.get("title") or "Resume",
                "resume_skill_count": len(resume_skill_names),
                "matched_skills": matched_names,
                "missing_high_demand_skills": missing,
                "skill_details": skill_details,
                "market_salary_benchmark": None,
                "skills_market_coverage_pct": round(coverage * 100, 1),
                "overall_market_alignment_score": round((coverage * 0.4 + demand_score * 0.6) * 100, 1),
            }

        data = get_or_cache(
            redis_client,
            build_cache_key("comparison", user_id=current_user_id, resume_id=str(resume_uuid)),
            COMPARISON_CACHE_TTL_SECONDS,
            query,
        )
        metadata = build_metadata(db, "public.raw_job_postings", {"resume_id": str(resume_uuid)})
        return ok_response(data, metadata)

    return safe_execute(fetch)
