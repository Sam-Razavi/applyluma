from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "applyluma",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.sample",
        "app.tasks.tailor",
        "app.tasks.notifications",
        "app.tasks.matching",
        "app.tasks.cover_letter",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-upcoming-deadlines-daily": {
            "task": "app.tasks.notifications.check_upcoming_deadlines",
            "schedule": crontab(hour=8, minute=0),
        },
        "check-stale-applications-daily": {
            "task": "app.tasks.notifications.check_stale_applications",
            "schedule": crontab(hour=8, minute=0),
        },
        "send-weekly-summary-monday": {
            "task": "app.tasks.notifications.send_weekly_summary",
            "schedule": crontab(hour=8, minute=0, day_of_week="monday"),
        },
        "notify-high-match-jobs-daily": {
            "task": "app.tasks.notifications.notify_high_match_jobs",
            "schedule": crontab(hour=3, minute=30),
        },
    },
)
