from datetime import UTC, datetime, timedelta

from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.user import User
from app.services import notification_service
from app.tasks.celery_app import celery_app

APPLICATION_STATUSES = (
    "wishlist",
    "applied",
    "phone_screen",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
)


@celery_app.task(name="app.tasks.notifications.check_stale_applications")
def check_stale_applications() -> dict[str, int]:
    db = SessionLocal()
    created = 0
    try:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        applications = (
            db.query(Application)
            .filter(Application.status == "applied", Application.applied_date < cutoff)
            .all()
        )
        for application in applications:
            notification_service.create_notification(
                db,
                user_id=application.user_id,
                type="application_stale",
                title="Follow up on your application",
                body=f"{application.company_name} has been in applied status for more than 7 days.",
                related_id=application.id,
                related_type="application",
                send_email=True,
                email=getattr(getattr(application, "user", None), "email", None),
            )
            created += 1
        return {"created": created}
    finally:
        db.close()


@celery_app.task(name="app.tasks.notifications.send_weekly_summary")
def send_weekly_summary() -> dict[str, int]:
    db = SessionLocal()
    created = 0
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        for user in users:
            stats = dict.fromkeys(APPLICATION_STATUSES, 0)
            rows = (
                db.query(Application.status, func.count(Application.id))
                .filter(Application.user_id == user.id)
                .group_by(Application.status)
                .all()
            )
            for status, count in rows:
                stats[status] = count

            body = ", ".join(f"{status.replace('_', ' ')}: {count}" for status, count in stats.items())
            notification_service.create_notification(
                db,
                user_id=user.id,
                type="weekly_summary",
                title="Weekly application summary",
                body=body,
                related_type="applications",
                send_email=True,
                email=user.email,
            )
            created += 1
        return {"created": created}
    finally:
        db.close()
