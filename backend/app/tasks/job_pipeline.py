"""Nightly job pipeline (02:00 UTC): scrape every source, then dedupe, tag
skills, extract keywords, compute daily metrics, rebuild the salary analytics
tables, and queue match scoring for every active user.

Every step is isolated: a failure is logged (and written to pipeline_run_log,
which /admin/pipeline and the health watchdog read) and the rest still run.
A Redis lock keeps the scheduled run and a manual "run now" from overlapping.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.dependencies import get_redis_client
from app.db.session import SessionLocal
from app.services import job_pipeline as steps
from app.services.job_scrapers.base import redact
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

LOCK_KEY = "job_pipeline:lock"
LOCK_TTL_SECONDS = 3600
SOURCE_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 30


def pipeline_is_running() -> bool:
    return bool(get_redis_client().exists(LOCK_KEY))


def _log_run(db: Session, name: str, rows: int, status: str, error: str | None = None) -> None:
    try:
        db.execute(
            text(
                "INSERT INTO pipeline_run_log (pipeline_name, rows_affected, status, error_message) "
                "VALUES (:name, :rows, :status, :error)"
            ),
            {"name": name, "rows": rows, "status": status, "error": redact(error or "")[:2000] or None},
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not write pipeline_run_log for %s", name)


def _scrape(db: Session, source: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, SOURCE_ATTEMPTS + 1):
        try:
            inserted = steps.scrape_source(source)
        except Exception as exc:
            last_error = exc
            logger.warning("Scrape %s failed (attempt %d/%d): %s", source, attempt, SOURCE_ATTEMPTS, exc)
            if attempt < SOURCE_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)
            continue
        _log_run(db, source, inserted, "success")
        return {"status": "success", "inserted": inserted}
    _log_run(db, source, 0, "failed", repr(last_error))
    return {"status": "failed", "error": repr(last_error)}


def _step(db: Session, name: str, fn: Callable[[Session], int], log_as: str | None = None) -> dict[str, Any]:
    try:
        rows = fn(db)
    except Exception as exc:
        db.rollback()
        logger.exception("Pipeline step %s failed", name)
        if log_as:
            _log_run(db, log_as, 0, "failed", repr(exc))
        return {"status": "failed", "error": repr(exc)}
    if log_as:
        _log_run(db, log_as, rows, "success")
    return {"status": "success", "rows": rows}


def _queue_matching(db: Session) -> int:
    from app.tasks.matching import compute_job_matching_scores

    user_ids = steps.active_user_ids(db)
    for user_id in user_ids:
        compute_job_matching_scores.delay(user_id, chain=True)
    return len(user_ids)


@celery_app.task(name="app.tasks.job_pipeline.run_job_pipeline")
def run_job_pipeline() -> dict[str, Any]:
    redis_client = get_redis_client()
    token = uuid.uuid4().hex
    if not redis_client.set(LOCK_KEY, token, nx=True, ex=LOCK_TTL_SECONDS):
        logger.info("Job pipeline already running; skipping this run")
        return {"skipped": "already running"}

    db = SessionLocal()
    summary: dict[str, Any] = {}
    try:
        summary["sources"] = {source: _scrape(db, source) for source in steps.SOURCES}
        summary["text_repair"] = _step(db, "text_repair", steps.repair_garbled_text)
        summary["dedupe"] = _step(db, "dedupe", steps.mark_duplicates)
        summary["skills"] = _step(db, "skills", steps.tag_skills)
        summary["keywords"] = _step(db, "keywords", steps.extract_keywords, log_as="extracted_keywords")
        summary["metrics"] = _step(db, "metrics", steps.compute_daily_metrics, log_as="transform_jobs")
        summary["salary_analytics"] = _step(
            db, "salary_analytics", steps.refresh_salary_analytics, log_as="salary_analytics"
        )
        summary["matching"] = _step(db, "matching", _queue_matching)
        logger.info("Job pipeline finished: %s", summary)
        return summary
    finally:
        db.close()
        # Release only our own lock, in case it expired and another run took it.
        if redis_client.get(LOCK_KEY) in (token, token.encode()):
            redis_client.delete(LOCK_KEY)
