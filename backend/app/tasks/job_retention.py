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

from sqlalchemy import ColumnElement, exists, or_, select

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting, SavedJob
from app.tasks.celery_app import celery_app

ARCHIVE_AFTER_DAYS = 30
PURGE_AFTER_ARCHIVED_DAYS = 90


def _is_referenced() -> ColumnElement[bool]:
    """Correlated: a user saved this posting or tracks an application for it."""
    return or_(
        exists().where(SavedJob.raw_job_posting_id == RawJobPosting.id),
        exists().where(Application.raw_job_posting_id == RawJobPosting.id),
    )


@celery_app.task(name="app.tasks.job_retention.archive_and_purge_job_postings")
def archive_and_purge_job_postings() -> dict[str, int]:
    db = SessionLocal()
    try:
        now = datetime.now(UTC)

        archived = (
            db.query(RawJobPosting)
            .filter(
                RawJobPosting.archived_at.is_(None),
                or_(
                    RawJobPosting.application_deadline < now,
                    RawJobPosting.scraped_at < now - timedelta(days=ARCHIVE_AFTER_DAYS),
                ),
            )
            .update({RawJobPosting.archived_at: now}, synchronize_session=False)
        )

        unreferenced_archived = select(RawJobPosting.id).where(
            RawJobPosting.archived_at.isnot(None), ~_is_referenced()
        )
        for model in (JobMatchingScore, ExtractedKeyword):
            db.query(model).filter(
                model.raw_job_posting_id.in_(unreferenced_archived)
            ).delete(synchronize_session=False)
        slimmed = (
            db.query(RawJobPosting)
            .filter(
                RawJobPosting.id.in_(unreferenced_archived),
                RawJobPosting.description != "",
            )
            .update(
                {
                    RawJobPosting.description: "",
                    RawJobPosting.raw_data: {},
                    RawJobPosting.extracted_skills: None,
                },
                synchronize_session=False,
            )
        )

        purged = (
            db.query(RawJobPosting)
            .filter(
                RawJobPosting.archived_at < now - timedelta(days=PURGE_AFTER_ARCHIVED_DAYS),
                ~_is_referenced(),
            )
            .delete(synchronize_session=False)
        )

        db.commit()
        return {"archived": archived, "slimmed": slimmed, "purged": purged}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
