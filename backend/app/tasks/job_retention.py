"""Daily retention for scraped job postings, so they don't fill the database.

1. Archive: postings whose application deadline has passed, or that were
   scraped more than ARCHIVE_AFTER_DAYS ago, get ``archived_at`` and drop out
   of every user-facing job surface (see ``crud.job._is_live_deadline_clause``).
2. Slim: archived postings nobody saved or applied to lose their bulky
   description/raw_data and their extracted keywords and match scores, which
   is where nearly all of a posting's storage goes.
3. Purge: archived postings are deleted outright PURGE_AFTER_ARCHIVED_DAYS
   later. The slim row is kept until then because the scrapers insert with
   ON CONFLICT (source, job_id_external) DO NOTHING — deleting an ad that is
   still listed at its source would let the next scrape re-insert it as a
   brand-new job (and re-alert on it).

Postings a user saved or linked to an application are archived like any
other, but keep their content and are never purged while still referenced.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, Select, exists, or_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting, SavedJob
from app.tasks.celery_app import celery_app

ARCHIVE_AFTER_DAYS = 30
PURGE_AFTER_ARCHIVED_DAYS = 90

# Work in small committed batches. Postgres writes a new version of every
# updated row (plus WAL) before the old one can be reclaimed, so a single
# transaction touching thousands of postings needs a lot of free disk at once;
# the first production run did exactly that and filled the 1 GB volume.
# Committing per batch keeps the extra space small and lets WAL be recycled,
# and the per-run cap spreads a large backlog over several nights.
BATCH_SIZE = 500
MAX_BATCHES_PER_RUN = 40

_SLIM_VALUES: dict[Any, Any] = {
    RawJobPosting.description: "",
    RawJobPosting.raw_data: {},
    RawJobPosting.extracted_skills: None,
}


def _is_referenced() -> ColumnElement[bool]:
    """Correlated: a user saved this posting or tracks an application for it."""
    return or_(
        exists().where(SavedJob.raw_job_posting_id == RawJobPosting.id),
        exists().where(Application.raw_job_posting_id == RawJobPosting.id),
    )


def _next_batch(db: Session, query: Select[Any]) -> list[Any]:
    return [row[0] for row in db.execute(query.limit(BATCH_SIZE)).all()]


def _drop_derived_rows(db: Session, ids: list[Any]) -> None:
    """Keywords and match scores are only needed while a posting is live."""
    for model in (JobMatchingScore, ExtractedKeyword):
        db.query(model).filter(model.raw_job_posting_id.in_(ids)).delete(
            synchronize_session=False
        )


def _purge(db: Session, now: datetime) -> int:
    """Delete long-archived, unreferenced postings. Runs first: it frees space."""
    query = select(RawJobPosting.id).where(
        RawJobPosting.archived_at < now - timedelta(days=PURGE_AFTER_ARCHIVED_DAYS),
        ~_is_referenced(),
    )
    purged = 0
    for _ in range(MAX_BATCHES_PER_RUN):
        ids = _next_batch(db, query)
        if not ids:
            break
        purged += db.query(RawJobPosting).filter(RawJobPosting.id.in_(ids)).delete(
            synchronize_session=False
        )
        db.commit()
    return purged


def _archive(db: Session, now: datetime) -> tuple[int, int]:
    """Archive expired/old postings; slim the unreferenced ones in the same write."""
    query = select(RawJobPosting.id).where(
        RawJobPosting.archived_at.is_(None),
        or_(
            RawJobPosting.application_deadline < now,
            RawJobPosting.scraped_at < now - timedelta(days=ARCHIVE_AFTER_DAYS),
        ),
    )
    archived = slimmed = 0
    for _ in range(MAX_BATCHES_PER_RUN):
        ids = _next_batch(db, query)
        if not ids:
            break
        unreferenced = [
            row[0]
            for row in db.execute(
                select(RawJobPosting.id).where(RawJobPosting.id.in_(ids), ~_is_referenced())
            ).all()
        ]
        if unreferenced:
            _drop_derived_rows(db, unreferenced)
            slimmed += db.query(RawJobPosting).filter(
                RawJobPosting.id.in_(unreferenced)
            ).update({RawJobPosting.archived_at: now, **_SLIM_VALUES}, synchronize_session=False)
        unreferenced_set = set(unreferenced)
        referenced = [i for i in ids if i not in unreferenced_set]
        if referenced:
            db.query(RawJobPosting).filter(RawJobPosting.id.in_(referenced)).update(
                {RawJobPosting.archived_at: now}, synchronize_session=False
            )
        archived += len(ids)
        db.commit()
    return archived, slimmed


def _slim_released(db: Session) -> int:
    """Slim archived postings whose last save/application was removed since."""
    query = select(RawJobPosting.id).where(
        RawJobPosting.archived_at.isnot(None),
        RawJobPosting.description != "",
        ~_is_referenced(),
    )
    slimmed = 0
    for _ in range(MAX_BATCHES_PER_RUN):
        ids = _next_batch(db, query)
        if not ids:
            break
        _drop_derived_rows(db, ids)
        slimmed += db.query(RawJobPosting).filter(RawJobPosting.id.in_(ids)).update(
            _SLIM_VALUES, synchronize_session=False
        )
        db.commit()
    return slimmed


@celery_app.task(name="app.tasks.job_retention.archive_and_purge_job_postings")
def archive_and_purge_job_postings() -> dict[str, int]:
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        purged = _purge(db, now)
        archived, slimmed = _archive(db, now)
        slimmed += _slim_released(db)
        return {"archived": archived, "slimmed": slimmed, "purged": purged}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
