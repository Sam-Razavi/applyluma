import logging
from typing import Any
from uuid import uuid4

from celery import Celery
from celery.schedules import crontab
from kombu.transport import virtual

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Resilience: survive corrupted broker messages.
#
# A producer that pushes a raw payload onto the queue (e.g. a bare
# ``redis.lpush("celery", json.dumps(...))``) creates a message without the
# Kombu envelope. When the worker consumes it, ``virtual.Message.__init__``
# does ``payload["properties"]`` and raises ``KeyError('properties')``, which
# crashes the whole consumer loop. We wrap it so a single bad message is logged
# and discarded instead of bringing the worker down.
# ---------------------------------------------------------------------------
_original_virtual_message_init = virtual.Message.__init__


def _resilient_virtual_message_init(self: Any, payload: Any, *args: Any, **kwargs: Any) -> None:
    try:
        _original_virtual_message_init(self, payload, *args, **kwargs)
    except KeyError as exc:
        logger.error(
            "Discarding corrupted broker message missing %s envelope key; payload=%r",
            exc,
            payload,
        )
        # Fill a minimal, valid-but-empty envelope so the message can be
        # constructed. Celery then acks and drops it via its normal
        # unknown/undecodable-message handling (no requeue, so no poison-message
        # loop even with task_acks_late=True) rather than crashing the worker.
        if isinstance(payload, dict):
            payload.setdefault("properties", {})
            payload.setdefault("headers", {})
            payload.setdefault("content-type", "application/json")
            payload.setdefault("content-encoding", "utf-8")
            payload.setdefault("body", None)
            properties = payload["properties"]
            if isinstance(properties, dict):
                # Kombu reads properties["delivery_tag"] (and delivery_info)
                # directly; seed them so the empty-envelope message constructs.
                properties.setdefault("delivery_tag", str(uuid4()))
                properties.setdefault("delivery_info", {})
        _original_virtual_message_init(self, payload, *args, **kwargs)


virtual.Message.__init__ = _resilient_virtual_message_init


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
        "app.tasks.watchdog",
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
        "health-watchdog-every-15-min": {
            "task": "app.tasks.watchdog.run_health_watchdog",
            "schedule": crontab(minute="*/15"),
        },
    },
)
