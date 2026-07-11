"""Health watchdog: runs every 15 minutes and emails on state transitions.

Checks db/redis/celery (reusing the same probes as /health/detailed), pipeline
freshness (raw_job_postings scraping), and a spike in failed AI jobs in the
last hour. State ("ok" or "degraded:<checks>") is persisted in app_settings
so an email only fires on a transition — a new failing check, or recovery —
mirroring the AI budget alert throttle in app/services/ai_usage.py.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.api.v1.endpoints.health import _check_celery, _check_db, _check_redis
from app.core.config import settings
from app.core.dependencies import get_redis_client
from app.crud import admin as crud_admin
from app.db.session import SessionLocal
from app.models.cover_letter_job import CoverLetterJob
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

WATCHDOG_STATE_KEY = "health_watchdog_state"


def _failed_ai_jobs_last_hour(db) -> int:  # type: ignore[no-untyped-def]
    from sqlalchemy import func, select

    from app.models.tailor_job import TailorJob, TailorStatus

    since = datetime.now(UTC) - timedelta(hours=1)
    tailor_failed = db.scalar(
        select(func.count()).select_from(TailorJob).where(
            TailorJob.status == TailorStatus.failed, TailorJob.updated_at >= since
        )
    ) or 0
    cover_failed = db.scalar(
        select(func.count()).select_from(CoverLetterJob).where(
            CoverLetterJob.status == "failed", CoverLetterJob.updated_at >= since
        )
    ) or 0
    return int(tailor_failed) + int(cover_failed)


def _run_checks() -> list[str]:
    """Return the names of currently-failing checks."""
    db = SessionLocal()
    failing: list[str] = []
    try:
        if _check_db(db)["status"] != "ok":
            failing.append("db")
        try:
            redis_client = get_redis_client()
            if _check_redis(redis_client)["status"] != "ok":
                failing.append("redis")
        except Exception:
            failing.append("redis")
        if _check_celery()["status"] != "ok":
            failing.append("celery")

        pipeline = crud_admin.get_pipeline_health(db)
        if not pipeline["raw_job_postings"]["healthy"]:
            failing.append("pipeline")

        failed_count = _failed_ai_jobs_last_hour(db)
        if failed_count >= settings.WATCHDOG_FAILURE_SPIKE_THRESHOLD:
            failing.append("ai_job_failures")
    finally:
        db.close()
    return sorted(failing)


@celery_app.task(name="app.tasks.watchdog.run_health_watchdog")
def run_health_watchdog() -> dict[str, str]:
    from app.services import ai_usage, email_service  # late import to avoid cycles

    failing = _run_checks()
    new_state = "ok" if not failing else "degraded:" + ",".join(failing)

    db = SessionLocal()
    try:
        previous_state = ai_usage.get_setting(db, WATCHDOG_STATE_KEY) or "ok"
        if new_state == previous_state:
            return {"state": new_state, "emailed": "false"}

        ai_usage.set_setting(db, WATCHDOG_STATE_KEY, new_state)

        if new_state == "ok":
            subject = "[ApplyLuma] Health alert cleared — all checks passing"
            body = "<p>All health checks are back to normal.</p>"
        else:
            subject = f"[ApplyLuma] Health alert: {', '.join(failing)} degraded"
            body = (
                f"<p>The following health checks are failing: <strong>{', '.join(failing)}</strong>.</p>"
                f"<p>Review at applyluma.com/admin/system.</p>"
            )

        try:
            email_service.send_email(
                to_email=settings.CONTACT_RECIPIENT_EMAIL, subject=subject, html_body=body
            )
        except Exception:
            logger.exception("Failed to send health watchdog alert email")

        return {"state": new_state, "emailed": "true"}
    finally:
        db.close()
