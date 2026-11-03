"""Admin views and controls for users: overview stats, the user list and profile, role/active/verified/limit changes, deletion, the activity timeline, signups and the funnel."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.ai_usage_log import AIUsageLog
from app.models.application import Application
from app.models.cover_letter_job import CoverLetterJob
from app.models.cv import CV
from app.models.job import SavedJob
from app.models.job_description import JobDescription
from app.models.notification import Notification
from app.models.tailor_job import TailorJob, TailorStatus
from app.models.user import User, UserRole
from app.services.inbound_email.address import build_inbox_address as inbound_address_for


def get_overview_stats(db: Session) -> dict:
    one_week_ago = datetime.now(UTC) - timedelta(days=7)

    user_stats = db.execute(
        select(
            func.count().label("total"),
            func.sum(case((User.role == UserRole.premium, 1), else_=0)).label("premium"),
            func.sum(case((User.role == UserRole.admin, 1), else_=0)).label("admin"),
            func.sum(case((User.created_at >= one_week_ago, 1), else_=0)).label("new_this_week"),
            func.sum(case((User.is_verified, 1), else_=0)).label("verified"),
        ).select_from(User)
    ).one()

    tailor_stats = db.execute(
        select(
            func.count().label("total"),
            func.sum(case((TailorJob.status == TailorStatus.complete, 1), else_=0)).label("complete"),
            func.sum(case((TailorJob.status == TailorStatus.failed, 1), else_=0)).label("failed"),
            func.sum(case((TailorJob.status == TailorStatus.pending, 1), else_=0)).label("pending"),
            func.sum(case((TailorJob.status == TailorStatus.processing, 1), else_=0)).label("processing"),
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
        "verified_users": int(user_stats.verified or 0),
        "total_cvs": total_cvs,
        "total_job_descriptions": total_jds,
        "total_applications": total_applications,
        "total_tailor_jobs": tailor_stats.total or 0,
        "tailor_jobs_complete": int(tailor_stats.complete or 0),
        "tailor_jobs_failed": int(tailor_stats.failed or 0),
        "tailor_jobs_pending": int(tailor_stats.pending or 0),
        "tailor_jobs_processing": int(tailor_stats.processing or 0),
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


def set_user_verified(db: Session, user: User) -> User:
    user.is_verified = True
    user.verification_token = None
    db.commit()
    db.refresh(user)
    return user


def set_user_tailor_limit_override(db: Session, user: User, value: int | None) -> User:
    user.daily_tailor_limit_override = value
    db.commit()
    db.refresh(user)
    return user


def delete_user_admin(db: Session, user_id: uuid.UUID) -> bool:
    """Hard-delete a user. All owned rows are removed by DB-level ON DELETE
    CASCADE; contact_submissions / ai_usage_logs / admin_audit_log keep their
    rows with user references set to NULL. A Core DELETE avoids the ORM
    loading every child collection just to delete it. On-disk CV/cover-letter
    files are erased afterward, same as self-service account deletion
    (GDPR right to erasure)."""
    from app.crud.user import _remove_user_files  # avoid a module-level cycle

    result = db.execute(delete(User).where(User.id == user_id))
    db.commit()
    if result.rowcount:
        _remove_user_files(str(user_id))
    return bool(result.rowcount)


def get_user_profile_admin(db: Session, user_id: uuid.UUID) -> dict[str, Any] | None:
    user = db.get(User, user_id)
    if not user:
        return None

    activity = {
        "cvs": db.scalar(select(func.count()).select_from(CV).where(CV.user_id == user_id)) or 0,
        "tailored_cvs": db.scalar(
            select(func.count()).select_from(CV).where(CV.user_id == user_id, CV.is_tailored.is_(True))
        ) or 0,
        "job_descriptions": db.scalar(
            select(func.count()).select_from(JobDescription).where(JobDescription.user_id == user_id)
        ) or 0,
        "applications": db.scalar(
            select(func.count()).select_from(Application).where(Application.user_id == user_id)
        ) or 0,
        "saved_jobs": db.scalar(
            select(func.count()).select_from(SavedJob).where(SavedJob.user_id == user_id)
        ) or 0,
        "tailor_jobs": db.scalar(
            select(func.count()).select_from(TailorJob).where(TailorJob.user_id == user_id)
        ) or 0,
        "tailor_jobs_failed": db.scalar(
            select(func.count()).select_from(TailorJob).where(
                TailorJob.user_id == user_id,
                TailorJob.status == TailorStatus.failed,
            )
        ) or 0,
        "cover_letters": db.scalar(
            select(func.count()).select_from(CoverLetterJob).where(CoverLetterJob.user_id == user_id)
        ) or 0,
        "cover_letters_failed": db.scalar(
            select(func.count()).select_from(CoverLetterJob).where(
                CoverLetterJob.user_id == user_id,
                CoverLetterJob.status == "failed",
            )
        ) or 0,
        "notifications": db.scalar(
            select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        ) or 0,
        "unread_notifications": db.scalar(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        ) or 0,
    }

    now = datetime.now(UTC)
    ai_cost_base = select(func.coalesce(func.sum(AIUsageLog.cost_usd), 0)).where(
        AIUsageLog.user_id == user_id
    )
    ai_costs = {
        "last_30_days_usd": float(
            db.scalar(ai_cost_base.where(AIUsageLog.created_at >= now - timedelta(days=30))) or 0
        ),
        "all_time_usd": float(db.scalar(ai_cost_base) or 0),
        "all_time_calls": int(
            db.scalar(
                select(func.count()).select_from(AIUsageLog).where(AIUsageLog.user_id == user_id)
            ) or 0
        ),
    }

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "login_count": user.login_count or 0,
        "auth_provider": user.auth_provider,
        "avatar_url": user.avatar_url,
        "stripe_customer_id": user.stripe_customer_id,
        "stripe_subscription_id": user.stripe_subscription_id,
        "subscription_ends_at": user.subscription_ends_at,
        "updated_at": user.updated_at,
        "daily_tailor_limit_override": user.daily_tailor_limit_override,
        "inbox_address": inbound_address_for(user),
        "activity": activity,
        "ai_costs": ai_costs,
    }


# One SELECT arm per user-owned table, all shaped (type, title, status, ts, ref_id)
# so they can be UNIONed into a single chronological feed. Notifications are
# deliberately excluded — they'd drown the real actions.
_ACTIVITY_UNION_SQL = """
    SELECT CASE WHEN c.is_tailored THEN 'cv_tailored' ELSE 'cv_uploaded' END AS type,
           COALESCE(c.title, c.filename, 'CV') AS title,
           NULL::text AS status, c.created_at AS ts, c.id AS ref_id
    FROM cvs c WHERE c.user_id = :user_id
    UNION ALL
    SELECT 'application_created', COALESCE(a.job_title, '?') || ' @ ' || COALESCE(a.company_name, '?'),
           a.status::text, a.created_at, a.id
    FROM applications a WHERE a.user_id = :user_id
    UNION ALL
    SELECT 'application_event',
           COALESCE(a.company_name, '?') || ': ' || ae.event_type
               || COALESCE(' → ' || ae.new_value, ''),
           NULL::text, ae.created_at, ae.id
    FROM application_events ae JOIN applications a ON a.id = ae.application_id
    WHERE a.user_id = :user_id
    UNION ALL
    SELECT 'tailor_job', COALESCE(jd.job_title || ' @ ' || jd.company_name, 'CV tailoring'),
           tj.status::text, tj.created_at, tj.id
    FROM tailor_jobs tj LEFT JOIN job_descriptions jd ON jd.id = tj.job_description_id
    WHERE tj.user_id = :user_id
    UNION ALL
    SELECT 'cover_letter', COALESCE(jd.job_title || ' @ ' || jd.company_name, 'Cover letter'),
           cj.status::text, cj.created_at, cj.id
    FROM cover_letter_jobs cj LEFT JOIN job_descriptions jd ON jd.id = cj.job_description_id
    WHERE cj.user_id = :user_id
    UNION ALL
    SELECT 'saved_job', COALESCE(r.title || ' @ ' || r.company, 'Saved job'),
           NULL::text, sj.created_at, sj.id
    FROM saved_jobs sj LEFT JOIN raw_job_postings r ON r.id = sj.raw_job_posting_id
    WHERE sj.user_id = :user_id
    UNION ALL
    SELECT 'job_description', COALESCE(jd.job_title, 'Job description')
               || COALESCE(' @ ' || jd.company_name, ''),
           NULL::text, jd.created_at, jd.id
    FROM job_descriptions jd WHERE jd.user_id = :user_id
    UNION ALL
    SELECT 'contact_submission', cs.subject, cs.category::text, cs.created_at, cs.id
    FROM contact_submissions cs WHERE cs.user_id = :user_id
"""


def get_user_activity(
    db: Session,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    params: dict[str, Any] = {"user_id": user_id, "limit": size, "offset": (page - 1) * size}
    total = db.execute(
        text(f"SELECT COUNT(*) FROM ({_ACTIVITY_UNION_SQL}) events"), params
    ).scalar() or 0
    rows = db.execute(
        text(
            f"SELECT type, title, status, ts, ref_id FROM ({_ACTIVITY_UNION_SQL}) events "
            "ORDER BY ts DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [
        {
            "type": r["type"],
            "title": r["title"],
            "status": r["status"],
            "timestamp": r["ts"],
            "ref_id": r["ref_id"],
        }
        for r in rows
    ], int(total)


def get_user_signups_daily(db: Session, days: int = 30) -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        text(
            "SELECT DATE(created_at) AS d, COUNT(*) AS c, "
            "SUM(CASE WHEN is_verified THEN 1 ELSE 0 END) AS vc "
            "FROM users WHERE created_at >= :cutoff GROUP BY DATE(created_at)"
        ),
        {"cutoff": cutoff},
    ).all()
    counts = {r.d.isoformat(): (int(r.c), int(r.vc or 0)) for r in rows}
    today = datetime.now(UTC).date()
    return [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "count": counts.get((today - timedelta(days=i)).isoformat(), (0, 0))[0],
            "verified_count": counts.get((today - timedelta(days=i)).isoformat(), (0, 0))[1],
        }
        for i in range(days - 1, -1, -1)
    ]


def get_user_funnel_stats(db: Session) -> dict[str, Any]:
    """Registration -> tailor-completion drop-off, one stage per query.

    Deliberately five independent COUNT(DISTINCT ...) queries rather than a
    single join/CTE: joining users to cvs/tailor_jobs directly would fan out
    and overcount any user with more than one CV or tailor job.
    """
    registered = db.scalar(select(func.count()).select_from(User)) or 0
    verified = db.scalar(select(func.count()).select_from(User).where(User.is_verified)) or 0
    has_cv = db.scalar(select(func.count(func.distinct(CV.user_id)))) or 0
    attempted_tailor = db.scalar(select(func.count(func.distinct(TailorJob.user_id)))) or 0
    completed_tailor = (
        db.scalar(
            select(func.count(func.distinct(TailorJob.user_id))).where(
                TailorJob.status == TailorStatus.complete
            )
        )
        or 0
    )
    return {
        "registered": registered,
        "verified": verified,
        "has_cv": has_cv,
        "attempted_tailor": attempted_tailor,
        "completed_tailor": completed_tailor,
    }
