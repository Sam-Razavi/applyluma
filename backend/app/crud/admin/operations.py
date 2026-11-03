"""Admin operations: the audit log, AI job list, notifications, billing users and contact/feedback submissions."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.contact_submission import ContactSubmission
from app.models.notification import Notification
from app.models.user import User, UserRole


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
