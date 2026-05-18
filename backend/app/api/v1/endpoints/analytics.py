from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.analytics import (
    AnalyticsOverview,
    CompanyStat,
    DailyJobCount,
    RecentJob,
    SkillStat,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Auth guard re-used across all endpoints (verifies token, doesn't load the full User row)
_auth = Depends(get_current_user_id)


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/overview", response_model=AnalyticsOverview)
def get_overview(
    _: str = _auth,
    db: Session = Depends(get_db),
) -> AnalyticsOverview:
    row = db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE NOT is_duplicate)                         AS total_jobs,
                ROUND(
                    COUNT(*) FILTER (WHERE NOT is_duplicate AND remote_allowed)
                    * 100.0 / NULLIF(COUNT(*) FILTER (WHERE NOT is_duplicate), 0),
                    1
                )                                                                AS remote_percentage,
                ROUND(AVG(salary_min) FILTER (WHERE NOT is_duplicate AND salary_min IS NOT NULL)) AS avg_salary_min,
                ROUND(AVG(salary_max) FILTER (WHERE NOT is_duplicate AND salary_max IS NOT NULL)) AS avg_salary_max,
                MAX(scraped_at)                                                  AS last_updated
            FROM raw_job_postings
        """)
    ).fetchone()

    # Top skill — separate query since it needs LATERAL unnest
    skill_row = db.execute(
        text("""
            SELECT skill
            FROM raw_job_postings,
                 jsonb_array_elements_text(extracted_skills) AS skill
            WHERE NOT is_duplicate
              AND extracted_skills IS NOT NULL
              AND jsonb_typeof(extracted_skills) = 'array'
            GROUP BY skill
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """)
    ).fetchone()

    if row is None or row.total_jobs == 0:
        return AnalyticsOverview(total_jobs=0, remote_percentage=0.0)

    return AnalyticsOverview(
        total_jobs=int(row.total_jobs),
        remote_percentage=float(row.remote_percentage or 0),
        avg_salary_min=int(row.avg_salary_min) if row.avg_salary_min else None,
        avg_salary_max=int(row.avg_salary_max) if row.avg_salary_max else None,
        top_skill=skill_row.skill if skill_row else None,
        last_updated=row.last_updated,
    )


# ── Top companies ─────────────────────────────────────────────────────────────

@router.get("/top-companies", response_model=list[CompanyStat])
def get_top_companies(
    limit: int = Query(10, ge=1, le=50),
    _: str = _auth,
    db: Session = Depends(get_db),
) -> list[CompanyStat]:
    rows = db.execute(
        text("""
            SELECT company AS company, COUNT(*) AS job_count
            FROM raw_job_postings
            WHERE NOT is_duplicate
            GROUP BY company
            ORDER BY job_count DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).fetchall()

    return [CompanyStat(company=r.company, job_count=int(r.job_count)) for r in rows]


# ── Top skills ────────────────────────────────────────────────────────────────

@router.get("/top-skills", response_model=list[SkillStat])
def get_top_skills(
    limit: int = Query(10, ge=1, le=50),
    _: str = _auth,
    db: Session = Depends(get_db),
) -> list[SkillStat]:
    rows = db.execute(
        text("""
            WITH skill_counts AS (
                SELECT
                    skill,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (
                        WHERE scraped_at >= NOW() - INTERVAL '7 days'
                    )                                                          AS this_week,
                    COUNT(*) FILTER (
                        WHERE scraped_at >= NOW() - INTERVAL '14 days'
                          AND scraped_at <  NOW() - INTERVAL '7 days'
                    )                                                          AS last_week
                FROM raw_job_postings,
                     jsonb_array_elements_text(extracted_skills) AS skill
                WHERE NOT is_duplicate
                  AND extracted_skills IS NOT NULL
                  AND jsonb_typeof(extracted_skills) = 'array'
                GROUP BY skill
            )
            SELECT
                skill,
                total_count AS mention_count,
                CASE
                    WHEN last_week = 0        THEN 'up'
                    WHEN this_week > last_week * 1.1 THEN 'up'
                    WHEN this_week < last_week * 0.9 THEN 'down'
                    ELSE 'stable'
                END AS trend
            FROM skill_counts
            ORDER BY total_count DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).fetchall()

    return [
        SkillStat(skill=r.skill, mention_count=int(r.mention_count), trend=r.trend)
        for r in rows
    ]


# ── Jobs over time ────────────────────────────────────────────────────────────

@router.get("/jobs-over-time", response_model=list[DailyJobCount])
def get_jobs_over_time(
    days: int = Query(30, ge=1, le=90),
    _: str = _auth,
    db: Session = Depends(get_db),
) -> list[DailyJobCount]:
    rows = db.execute(
        text("""
            SELECT
                DATE(scraped_at)::text AS date,
                COUNT(*)               AS job_count
            FROM raw_job_postings
            WHERE NOT is_duplicate
              AND scraped_at >= NOW() - make_interval(days => :days)
            GROUP BY DATE(scraped_at)
            ORDER BY date ASC
        """),
        {"days": days},
    ).fetchall()

    return [DailyJobCount(date=r.date, job_count=int(r.job_count)) for r in rows]


# ── Recent jobs ───────────────────────────────────────────────────────────────

@router.get("/recent-jobs", response_model=list[RecentJob])
def get_recent_jobs(
    limit: int = Query(20, ge=1, le=100),
    _: str = _auth,
    db: Session = Depends(get_db),
) -> list[RecentJob]:
    rows = db.execute(
        text("""
            SELECT
                id::text,
                title,
                company,
                location,
                url,
                remote_allowed,
                employment_type,
                extracted_skills,
                scraped_at
            FROM raw_job_postings
            WHERE NOT is_duplicate
            ORDER BY scraped_at DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).fetchall()

    result = []
    for r in rows:
        skills = r.extracted_skills
        if skills is not None and not isinstance(skills, list):
            # sqlalchemy may return JSONB as dict or str depending on driver version
            import json
            try:
                skills = json.loads(skills) if isinstance(skills, str) else list(skills)
            except Exception:
                skills = None

        result.append(
            RecentJob(
                id=r.id,
                title=r.title,
                company=r.company,
                location=r.location,
                url=r.url,
                remote_allowed=r.remote_allowed,
                employment_type=r.employment_type,
                extracted_skills=skills,
                scraped_at=r.scraped_at,
            )
        )
    return result
