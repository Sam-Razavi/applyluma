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
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-stale-applications-daily": {
            "task": "app.tasks.notifications.check_stale_applications",
            "schedule": crontab(hour=8, minute=0),
        },
        "send-weekly-summary-monday": {
            "task": "app.tasks.notifications.send_weekly_summary",
            "schedule": crontab(hour=8, minute=0, day_of_week="monday"),
        },
    },
)
