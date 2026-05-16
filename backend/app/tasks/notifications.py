from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, exists, func, not_
from sqlalchemy.orm import joinedload

from app.crud import alert_preferences as crud_alert_preferences
from app.db.session import SessionLocal
from app.models.alert_preferences import JobAlertSentLog
from app.models.application import Application
from app.models.job import JobMatchingScore
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


@celery_app.task(name="app.tasks.notifications.notify_high_match_jobs")
def notify_high_match_jobs() -> dict[str, int]:
    db = SessionLocal()
    created = 0
    logged = 0
    try:
        now = datetime.now(UTC)
        preferences = crud_alert_preferences.due_for_alert(db, now=now)
        for pref in preferences:
            score_query = (
                db.query(JobMatchingScore)
                .options(joinedload(JobMatchingScore.job))
                .filter(
                    JobMatchingScore.user_id == pref.user_id,
                    JobMatchingScore.overall_score >= pref.score_threshold,
                    not_(
                        exists().where(
                            (JobAlertSentLog.user_id == pref.user_id)
                            & (
                                JobAlertSentLog.raw_job_posting_id
                                == JobMatchingScore.raw_job_posting_id
                            )
                        )
                    ),
                )
            )
            if pref.last_sent_at is not None:
                score_query = score_query.filter(JobMatchingScore.computed_at > pref.last_sent_at)

            matches = score_query.order_by(desc(JobMatchingScore.overall_score)).limit(10).all()
            if not matches:
                pref.last_sent_at = now
                db.commit()
                continue

            lines = [
                f"{score.job.title} at {score.job.company} ({round(score.overall_score)}%)"
                for score in matches
                if score.job
            ]
            if not lines:
                pref.last_sent_at = now
                db.commit()
                continue

            user = db.get(User, pref.user_id)
            notification_service.create_notification(
                db,
                user_id=pref.user_id,
                type="high_match_alert",
                title="New high-match jobs",
                body="\n".join(lines),
                related_type="jobs",
                send_email=True,
                email=getattr(user, "email", None),
            )
            created += 1

            for score in matches:
                db.add(
                    JobAlertSentLog(
                        user_id=pref.user_id,
                        raw_job_posting_id=score.raw_job_posting_id,
                    )
                )
                logged += 1
            pref.last_sent_at = now
            db.commit()

        return {"created": created, "logged": logged}
    finally:
        db.close()
