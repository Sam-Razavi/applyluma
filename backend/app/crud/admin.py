from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.cover_letter_job import CoverLetterJob
from app.models.cv import CV
from app.models.job_description import JobDescription
from app.models.tailor_job import TailorJob, TailorStatus
from app.models.user import User, UserRole


def get_overview_stats(db: Session) -> dict:
    one_week_ago = datetime.now(UTC) - timedelta(days=7)

    user_stats = db.execute(
        select(
            func.count().label("total"),
            func.sum(case((User.role == UserRole.premium, 1), else_=0)).label("premium"),
            func.sum(case((User.role == UserRole.admin, 1), else_=0)).label("admin"),
            func.sum(case((User.created_at >= one_week_ago, 1), else_=0)).label("new_this_week"),
        ).select_from(User)
    ).one()

    tailor_stats = db.execute(
        select(
            func.count().label("total"),
            func.sum(case((TailorJob.status == TailorStatus.complete, 1), else_=0)).label("complete"),
            func.sum(case((TailorJob.status == TailorStatus.failed, 1), else_=0)).label("failed"),
            func.sum(case((TailorJob.status == TailorStatus.pending, 1), else_=0)).label("pending"),
        ).select_from(TailorJob)
    ).one()

    total_cvs = db.scalar(select(func.count()).select_from(CV)) or 0
    total_jds = db.scalar(select(func.count()).select_from(JobDescription)) or 0
    total_applications = db.scalar(select(func.count()).select_from(Application)) or 0
    total_cover_letters = db.scalar(select(func.count()).select_from(CoverLetterJob)) or 0

    return {
        "total_users": user_stats.total or 0,
        "premium_users": int(user_stats.premium or 0),
        "admin_users": int(user_stats.admin or 0),
        "new_users_this_week": int(user_stats.new_this_week or 0),
        "total_cvs": total_cvs,
        "total_job_descriptions": total_jds,
        "total_applications": total_applications,
        "total_tailor_jobs": tailor_stats.total or 0,
        "tailor_jobs_complete": int(tailor_stats.complete or 0),
        "tailor_jobs_failed": int(tailor_stats.failed or 0),
        "tailor_jobs_pending": int(tailor_stats.pending or 0),
        "total_cover_letters": total_cover_letters,
    }


def list_users(
    db: Session,
    *,
    search: str | None = None,
    role: UserRole | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[User], int]:
    q = select(User)
    if search:
        pattern = f"%{search}%"
        q = q.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    if role is not None:
        q = q.where(User.role == role)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(q.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return list(items), total


def get_user_by_id_admin(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def set_user_role(db: Session, user: User, role: UserRole) -> User:
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, user: User, is_active: bool) -> User:
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


_HEALTH_WINDOW = timedelta(hours=25)


def _is_healthy(last_run: datetime | None) -> bool:
    return last_run is not None and (datetime.now(UTC) - last_run) <= _HEALTH_WINDOW


def get_pipeline_health(db: Session) -> dict[str, Any]:
    rjp = db.execute(text("SELECT COUNT(*) AS c, MAX(scraped_at) AS m FROM raw_job_postings")).one()
    ek = db.execute(text("SELECT COUNT(*) AS c, MAX(created_at) AS m FROM extracted_keywords")).one()
    jmm = db.execute(text("SELECT COUNT(*) AS c, MAX(created_at) AS m FROM job_market_metrics")).one()
    src = db.execute(
        text(
            "SELECT source, COUNT(*) AS c, MAX(scraped_at) AS m "
            "FROM raw_job_postings GROUP BY source ORDER BY c DESC"
        )
    ).all()

    def stage(name: str, row: Any) -> dict[str, Any]:
        return {"name": name, "count": int(row.c or 0), "last_run": row.m, "healthy": _is_healthy(row.m)}

    return {
        "raw_job_postings": stage("raw_job_postings", rjp),
        "extracted_keywords": stage("extracted_keywords", ek),
        "job_market_metrics": stage("job_market_metrics", jmm),
        "sources": [
            {"source": r.source, "count": int(r.c or 0), "last_run": r.m, "healthy": _is_healthy(r.m)}
            for r in src
        ],
    }


def get_jobs_over_time(db: Session, days: int = 14) -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        text(
            "SELECT DATE(scraped_at) AS d, COUNT(*) AS c FROM raw_job_postings "
            "WHERE scraped_at >= :cutoff GROUP BY DATE(scraped_at)"
        ),
        {"cutoff": cutoff},
    ).all()
    counts = {r.d.isoformat(): int(r.c) for r in rows}
    today = datetime.now(UTC).date()
    return [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "count": counts.get((today - timedelta(days=i)).isoformat(), 0),
        }
        for i in range(days - 1, -1, -1)
    ]


def get_jobs_by_source(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text("SELECT source, COUNT(*) AS c FROM raw_job_postings GROUP BY source ORDER BY c DESC")
    ).all()
    return [{"source": r.source, "count": int(r.c)} for r in rows]


def get_latest_market_metrics(db: Session) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT metric_date, total_jobs_scraped, top_skills, top_companies, remote_percentage "
            "FROM job_market_metrics ORDER BY metric_date DESC, created_at DESC LIMIT 1"
        )
    ).first()
    if row is None:
        return None
    top_skills = [
        {"skill": s.get("skill", ""), "count": int(s.get("count", 0))}
        for s in (row.top_skills or [])
        if isinstance(s, dict)
    ]
    top_companies = [
        {"company": c.get("company", ""), "count": int(c.get("count", 0))}
        for c in (row.top_companies or [])
        if isinstance(c, dict)
    ]
    return {
        "metric_date": row.metric_date,
        "total_jobs_scraped": row.total_jobs_scraped,
        "remote_percentage": float(row.remote_percentage) if row.remote_percentage is not None else None,
        "top_skills": top_skills,
        "top_companies": top_companies,
    }
