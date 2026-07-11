from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.ai_usage_log import AIUsageLog
from app.models.application import Application
from app.models.contact_submission import ContactSubmission
from app.models.cover_letter_job import CoverLetterJob
from app.models.cv import CV
from app.models.job import SavedJob
from app.models.job_description import JobDescription
from app.models.notification import Notification
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


def log_admin_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID | None,
    action: str,
    target_user_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    entry = AdminAuditLog(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    try:
        db.add(entry)
        db.commit()
    except Exception:
        if hasattr(db, "rollback"):
            db.rollback()


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


def list_ai_jobs(
    db: Session,
    *,
    kind: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if kind:
        filters.append("kind = :kind")
        params["kind"] = kind
    if status:
        filters.append("status = :status")
        params["status"] = status
    if search:
        filters.append("(user_email ILIKE :search OR job_title ILIKE :search OR company_name ILIKE :search)")
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    base_sql = """
        SELECT
            tj.id, 'tailor' AS kind, tj.user_id, u.email AS user_email,
            tj.status::text AS status, tj.created_at, tj.updated_at, tj.celery_task_id,
            tj.error_message, jd.job_title, jd.company_name, tj.language,
            tj.intensity::text AS intensity, NULL::text AS tone, NULL::integer AS word_count
        FROM tailor_jobs tj
        LEFT JOIN users u ON u.id = tj.user_id
        LEFT JOIN job_descriptions jd ON jd.id = tj.job_description_id
        UNION ALL
        SELECT
            cj.id, 'cover_letter' AS kind, cj.user_id, u.email AS user_email,
            cj.status::text AS status, cj.created_at, cj.updated_at, cj.celery_task_id,
            cj.error_message, jd.job_title, jd.company_name, cj.language,
            NULL::text AS intensity, cj.tone::text AS tone, cj.word_count
        FROM cover_letter_jobs cj
        LEFT JOIN users u ON u.id = cj.user_id
        LEFT JOIN job_descriptions jd ON jd.id = cj.job_description_id
    """
    total = db.execute(text(f"SELECT COUNT(*) AS c FROM ({base_sql}) ai_jobs {where}"), params).scalar() or 0
    rows = db.execute(
        text(f"SELECT * FROM ({base_sql}) ai_jobs {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def list_pipeline_runs(
    db: Session,
    *,
    pipeline_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if pipeline_name:
        filters.append("pipeline_name ILIKE :pipeline_name")
        params["pipeline_name"] = f"%{pipeline_name}%"
    if status:
        filters.append("status = :status")
        params["status"] = status
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM pipeline_run_log {where}"), params).scalar() or 0
    rows = db.execute(
        text(
            "SELECT id, pipeline_name, ran_at, rows_affected, status, error_message "
            f"FROM pipeline_run_log {where} ORDER BY ran_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def list_raw_jobs_admin(
    db: Session,
    *,
    search: str | None = None,
    source: str | None = None,
    duplicate: bool | None = None,
    remote: bool | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if search:
        filters.append("(r.title ILIKE :search OR r.company ILIKE :search OR r.location ILIKE :search)")
        params["search"] = f"%{search}%"
    if source:
        filters.append("r.source = :source")
        params["source"] = source
    if duplicate is not None:
        filters.append("r.is_duplicate = :duplicate")
        params["duplicate"] = duplicate
    if remote is not None:
        filters.append("(r.is_remote = :remote OR r.remote_allowed = :remote)")
        params["remote"] = remote
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    count_sql = f"SELECT COUNT(*) FROM raw_job_postings r {where}"
    total = db.execute(text(count_sql), params).scalar() or 0
    rows = db.execute(
        text(
            "SELECT r.id, r.source, r.job_id_external, r.title, r.company, r.location, r.url, "
            "r.salary_min, r.salary_max, r.employment_type, r.remote_allowed, r.is_remote, "
            "r.is_duplicate, r.application_deadline, r.scraped_at, "
            "COUNT(DISTINCT ek.id)::int AS keyword_count, "
            "COUNT(DISTINCT sj.id)::int AS saved_count, "
            "COUNT(DISTINCT jms.id)::int AS matching_score_count "
            "FROM raw_job_postings r "
            "LEFT JOIN extracted_keywords ek ON ek.raw_job_posting_id = r.id "
            "LEFT JOIN saved_jobs sj ON sj.raw_job_posting_id = r.id "
            "LEFT JOIN job_matching_scores jms ON jms.raw_job_posting_id = r.id "
            f"{where} "
            "GROUP BY r.id ORDER BY r.scraped_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def get_raw_job_detail_admin(db: Session, job_id: uuid.UUID) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT r.*, "
            "COUNT(DISTINCT ek.id)::int AS keyword_count, "
            "COUNT(DISTINCT sj.id)::int AS saved_count, "
            "COUNT(DISTINCT jms.id)::int AS matching_score_count "
            "FROM raw_job_postings r "
            "LEFT JOIN extracted_keywords ek ON ek.raw_job_posting_id = r.id "
            "LEFT JOIN saved_jobs sj ON sj.raw_job_posting_id = r.id "
            "LEFT JOIN job_matching_scores jms ON jms.raw_job_posting_id = r.id "
            "WHERE r.id = :job_id GROUP BY r.id"
        ),
        {"job_id": job_id},
    ).mappings().first()
    if row is None:
        return None
    keywords = db.execute(
        text(
            "SELECT keyword AS skill, SUM(frequency)::int AS count "
            "FROM extracted_keywords WHERE raw_job_posting_id = :job_id "
            "GROUP BY keyword ORDER BY count DESC LIMIT 25"
        ),
        {"job_id": job_id},
    ).mappings().all()
    data = dict(row)
    data["keywords"] = [dict(k) for k in keywords]
    return data


def list_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    user_id: uuid.UUID | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if action:
        filters.append("l.action = :action")
        params["action"] = action
    if user_id:
        filters.append("(l.admin_user_id = :user_id OR l.target_user_id = :user_id)")
        params["user_id"] = user_id
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM admin_audit_log l {where}"), params).scalar() or 0
    rows = db.execute(
        text(
            "SELECT l.id, l.admin_user_id, au.email AS admin_email, "
            "l.target_user_id, tu.email AS target_email, l.action, l.details, "
            "l.ip_address, l.user_agent, l.created_at "
            "FROM admin_audit_log l "
            "LEFT JOIN users au ON au.id = l.admin_user_id "
            "LEFT JOIN users tu ON tu.id = l.target_user_id "
            f"{where} ORDER BY l.created_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def send_bulk_notification(
    db: Session,
    *,
    audience: str,
    title: str,
    body: str,
    notification_type: str = "admin_message",
    role: UserRole | None = None,
    user_id: uuid.UUID | None = None,
) -> int:
    q = select(User.id).where(User.is_active.is_(True))
    if audience == "role" and role is not None:
        q = q.where(User.role == role)
    elif audience == "user" and user_id is not None:
        q = q.where(User.id == user_id)
    elif audience not in {"all", "role", "user"}:
        return 0

    user_ids = list(db.scalars(q).all())
    if not user_ids:
        return 0

    db.add_all(
        [
            Notification(
                user_id=recipient_id,
                type=notification_type,
                title=title,
                body=body,
                related_type="admin",
            )
            for recipient_id in user_ids
        ]
    )
    db.commit()
    return len(user_ids)


def list_admin_notifications(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters = ["n.type = 'admin_message'"]
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if search:
        filters.append("(u.email ILIKE :search OR n.title ILIKE :search OR n.body ILIKE :search)")
        params["search"] = f"%{search}%"
    where = f"WHERE {' AND '.join(filters)}"
    total = db.execute(
        text(f"SELECT COUNT(*) FROM notifications n LEFT JOIN users u ON u.id = n.user_id {where}"),
        params,
    ).scalar() or 0
    rows = db.execute(
        text(
            "SELECT n.id, n.user_id, u.email AS user_email, n.type, n.title, n.body, "
            "n.is_read, n.created_at "
            "FROM notifications n LEFT JOIN users u ON u.id = n.user_id "
            f"{where} ORDER BY n.created_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def list_billing_users(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    summary_row = db.execute(
        select(
            func.count(User.id).label("total_users"),
            func.sum(case((User.role == UserRole.premium, 1), else_=0)).label("premium_users"),
            func.sum(case((User.subscription_status == "active", 1), else_=0)).label("active_subscriptions"),
            func.sum(case((User.subscription_status == "canceled", 1), else_=0)).label("canceled_subscriptions"),
            func.sum(case((User.subscription_status == "past_due", 1), else_=0)).label("past_due_subscriptions"),
        )
    ).one()
    summary = {
        "total_users": int(summary_row.total_users or 0),
        "premium_users": int(summary_row.premium_users or 0),
        "active_subscriptions": int(summary_row.active_subscriptions or 0),
        "canceled_subscriptions": int(summary_row.canceled_subscriptions or 0),
        "past_due_subscriptions": int(summary_row.past_due_subscriptions or 0),
    }

    q = select(User)
    if search:
        pattern = f"%{search}%"
        q = q.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    if status:
        q = q.where(User.subscription_status == status)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    users = db.scalars(q.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "subscription_status": user.subscription_status,
            "subscription_ends_at": user.subscription_ends_at,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "created_at": user.created_at,
        }
        for user in users
    ], int(total), summary


def create_contact_submission(
    db: Session,
    *,
    name: str,
    email: str,
    subject: str,
    message: str,
    remote_ip: str | None = None,
    user_agent: str | None = None,
    user_id: uuid.UUID | None = None,
    category: str = "contact",
    source: str = "contact",
) -> ContactSubmission | None:
    if db is None:
        return None
    submission = ContactSubmission(
        name=name,
        email=email,
        subject=subject,
        message=message,
        remote_ip=remote_ip,
        user_agent=user_agent,
        user_id=user_id,
        category=category,
        source=source,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def list_contact_submissions(
    db: Session,
    *,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[ContactSubmission], int]:
    q = select(ContactSubmission)
    if status:
        q = q.where(ContactSubmission.status == status)
    if category:
        q = q.where(ContactSubmission.category == category)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            or_(
                ContactSubmission.name.ilike(pattern),
                ContactSubmission.email.ilike(pattern),
                ContactSubmission.subject.ilike(pattern),
                ContactSubmission.message.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.scalars(
        q.order_by(ContactSubmission.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return list(items), int(total)


def set_contact_submission_status(
    db: Session,
    submission_id: uuid.UUID,
    status: str,
) -> ContactSubmission | None:
    submission = db.get(ContactSubmission, submission_id)
    if not submission:
        return None
    submission.status = status
    db.commit()
    db.refresh(submission)
    return submission


_HEALTH_WINDOW = timedelta(hours=25)

_STAGE_PIPELINES: dict[str, list[str]] = {
    "raw_job_postings": [
        "remotive", "the_muse", "remoteok",
        "adzuna_remote", "adzuna_nl", "adzuna_fr", "adzuna_de",
        "platsbanken",
    ],
    "extracted_keywords": ["extracted_keywords"],
    "job_market_metrics": ["transform_jobs"],
}


def _health_status(log_row: Any | None) -> str:
    """Return 'healthy', 'stale', or 'failed' based on the latest pipeline_run_log entry."""
    if log_row is None:
        return "unknown"
    if log_row.status == "failed":
        return "failed"
    if (datetime.now(UTC) - log_row.ran_at) <= _HEALTH_WINDOW:
        return "healthy"
    return "stale"


def _get_pipeline_log_map(db: Session) -> dict[str, Any]:
    rows = db.execute(
        text(
            "SELECT DISTINCT ON (pipeline_name) "
            "pipeline_name, ran_at, rows_affected, status "
            "FROM pipeline_run_log "
            "ORDER BY pipeline_name, ran_at DESC"
        )
    ).all()
    return {r.pipeline_name: r for r in rows}


def _resolve_stage_health(
    log_map: dict[str, Any],
    pipeline_names: list[str],
    fallback_last_run: datetime | None,
) -> tuple[datetime | None, str]:
    """Pick the most recent log entry across the given pipeline names.

    Falls back to *fallback_last_run* (legacy MAX query) when no log rows exist.
    """
    best = None
    for name in pipeline_names:
        entry = log_map.get(name)
        if entry is not None and (best is None or entry.ran_at > best.ran_at):
            best = entry

    if best is not None:
        return best.ran_at, _health_status(best)

    if fallback_last_run is not None and (datetime.now(UTC) - fallback_last_run) <= _HEALTH_WINDOW:
        return fallback_last_run, "healthy"
    if fallback_last_run is not None:
        return fallback_last_run, "stale"
    return None, "unknown"


def get_pipeline_health(db: Session) -> dict[str, Any]:
    log_map = _get_pipeline_log_map(db)

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
        pipelines = _STAGE_PIPELINES.get(name, [])
        last_run, status = _resolve_stage_health(log_map, pipelines, row.m)
        return {
            "name": name,
            "count": int(row.c or 0),
            "last_run": last_run,
            "healthy": status == "healthy",
            "status": status,
        }

    def source_health(row: Any) -> dict[str, Any]:
        entry = log_map.get(row.source)
        if entry is not None:
            status = _health_status(entry)
            return {
                "source": row.source,
                "count": int(row.c or 0),
                "last_run": entry.ran_at,
                "healthy": status == "healthy",
                "status": status,
            }
        fallback_healthy = row.m is not None and (datetime.now(UTC) - row.m) <= _HEALTH_WINDOW
        return {
            "source": row.source,
            "count": int(row.c or 0),
            "last_run": row.m,
            "healthy": fallback_healthy,
            "status": "healthy" if fallback_healthy else ("stale" if row.m else "unknown"),
        }

    return {
        "raw_job_postings": stage("raw_job_postings", rjp),
        "extracted_keywords": stage("extracted_keywords", ek),
        "job_market_metrics": stage("job_market_metrics", jmm),
        "sources": [source_health(r) for r in src],
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


# ── AI costs ─────────────────────────────────────────────────────────────────

def _ai_cost_window(db: Session, since: datetime | None) -> dict[str, Any]:
    q = select(
        func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
        func.count().label("calls"),
        func.coalesce(
            func.sum(AIUsageLog.prompt_tokens + AIUsageLog.completion_tokens), 0
        ).label("tokens"),
    )
    if since is not None:
        q = q.where(AIUsageLog.created_at >= since)
    row = db.execute(q).one()
    return {"cost_usd": float(row.cost), "calls": int(row.calls), "tokens": int(row.tokens)}


def get_ai_costs_summary(db: Session) -> dict[str, Any]:
    from app.services import ai_usage

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    budget_raw = ai_usage.get_setting(db, ai_usage.BUDGET_SETTING_KEY)
    monthly_budget = float(budget_raw) if budget_raw else None
    mtd = float(ai_usage.month_to_date_cost(db))

    return {
        "today": _ai_cost_window(db, today_start),
        "last_7_days": _ai_cost_window(db, now - timedelta(days=7)),
        "last_30_days": _ai_cost_window(db, now - timedelta(days=30)),
        "all_time": _ai_cost_window(db, None),
        "budget": {
            "monthly_usd": monthly_budget,
            "month_to_date_usd": mtd,
            "pct_used": round(mtd / monthly_budget * 100, 1) if monthly_budget else None,
        },
    }


def list_ai_costs_daily(db: Session, days: int = 30) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=days)
    day = func.date_trunc("day", AIUsageLog.created_at).label("day")
    rows = db.execute(
        select(
            day,
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
            func.count().label("calls"),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(day)
        .order_by(day)
    ).all()
    return [
        {"date": row.day.date().isoformat(), "cost_usd": float(row.cost), "calls": int(row.calls)}
        for row in rows
    ]


def get_ai_costs_breakdown(db: Session, days: int = 30) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)

    def grouped(column: Any) -> list[dict[str, Any]]:
        rows = db.execute(
            select(
                column.label("key"),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
                func.count().label("calls"),
                func.coalesce(
                    func.sum(AIUsageLog.prompt_tokens + AIUsageLog.completion_tokens), 0
                ).label("tokens"),
            )
            .where(AIUsageLog.created_at >= since)
            .group_by(column)
            .order_by(func.sum(AIUsageLog.cost_usd).desc())
        ).all()
        return [
            {
                "key": str(row.key),
                "cost_usd": float(row.cost),
                "calls": int(row.calls),
                "tokens": int(row.tokens),
            }
            for row in rows
        ]

    user_rows = db.execute(
        select(
            AIUsageLog.user_id,
            User.email,
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0).label("cost"),
            func.count().label("calls"),
        )
        .outerjoin(User, User.id == AIUsageLog.user_id)
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.user_id, User.email)
        .order_by(func.sum(AIUsageLog.cost_usd).desc())
        .limit(10)
    ).all()

    return {
        "by_purpose": grouped(AIUsageLog.purpose),
        "by_model": grouped(AIUsageLog.model),
        "top_users": [
            {
                "user_id": row.user_id,
                "email": row.email,
                "cost_usd": float(row.cost),
                "calls": int(row.calls),
            }
            for row in user_rows
        ],
    }


def set_ai_budget(db: Session, monthly_usd: float | None) -> None:
    from app.services import ai_usage

    value = "" if monthly_usd is None else str(monthly_usd)
    ai_usage.set_setting(db, ai_usage.BUDGET_SETTING_KEY, value)


# ── Database stats ───────────────────────────────────────────────────────────

# Fixed allowlist of tables whose growth can be measured via created_at.
# Never derived from client input — the stats endpoint takes no parameters.
_GROWTH_TABLES: dict[str, Any] = {}


def _growth_tables() -> dict[str, Any]:
    # Lazy import to avoid circulars at module import time.
    if not _GROWTH_TABLES:
        from app.models.job import RawJobPosting

        _GROWTH_TABLES.update(
            {
                "users": (User, User.created_at),
                "cvs": (CV, CV.created_at),
                "job_descriptions": (JobDescription, JobDescription.created_at),
                "tailor_jobs": (TailorJob, TailorJob.created_at),
                "cover_letter_jobs": (CoverLetterJob, CoverLetterJob.created_at),
                "applications": (Application, Application.created_at),
                "saved_jobs": (SavedJob, SavedJob.created_at),
                "notifications": (Notification, Notification.created_at),
                "raw_job_postings": (RawJobPosting, RawJobPosting.scraped_at),
                "ai_usage_logs": (AIUsageLog, AIUsageLog.created_at),
                "contact_submissions": (ContactSubmission, ContactSubmission.created_at),
                "admin_audit_log": (AdminAuditLog, AdminAuditLog.created_at),
            }
        )
    return _GROWTH_TABLES


def get_database_stats(db: Session) -> dict[str, Any]:
    db_size = int(db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0)
    rows = db.execute(
        text(
            "SELECT c.relname AS table_name, "
            "GREATEST(c.reltuples, 0)::bigint AS approx_row_count, "
            "pg_total_relation_size(c.oid) AS total_bytes "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' "
            "ORDER BY pg_total_relation_size(c.oid) DESC"
        )
    ).mappings().all()

    now = datetime.now(UTC)
    growth: dict[str, tuple[int, int]] = {}
    for table_name, (model, ts_column) in _growth_tables().items():
        rows_7d = db.scalar(
            select(func.count()).select_from(model).where(ts_column >= now - timedelta(days=7))
        ) or 0
        rows_30d = db.scalar(
            select(func.count()).select_from(model).where(ts_column >= now - timedelta(days=30))
        ) or 0
        growth[table_name] = (int(rows_7d), int(rows_30d))

    tables = []
    for r in rows:
        g = growth.get(r["table_name"])
        tables.append(
            {
                "table_name": r["table_name"],
                "approx_row_count": int(r["approx_row_count"]),
                "total_bytes": int(r["total_bytes"]),
                "rows_7d": g[0] if g else None,
                "rows_30d": g[1] if g else None,
            }
        )
    return {"database_size_bytes": db_size, "tables": tables, "generated_at": now}
