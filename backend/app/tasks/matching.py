"""Celery task: compute job matching scores for a user in the background."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from app.core.cache_service import CacheService
from app.crud import job as crud_job
from app.db.session import SessionLocal
from app.models.job import JobMatchingScore, RawJobPosting
from app.services.matching_service import MatchingService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Postings scored per task run. A forced rescore covers the whole live feed by
# chaining runs of this size, so a single-concurrency worker can still pick up
# other queued tasks (e.g. a user's CV tailoring) between batches.
BATCH_LIMIT = 200


@celery_app.task(
    bind=True,
    name="app.tasks.matching.compute_job_matching_scores",
    max_retries=2,
    default_retry_delay=30,
)
def compute_job_matching_scores(
    self, user_id: str, force: bool = False, rescore_before: str | None = None
) -> dict:
    """Compute or refresh matching scores for live jobs for one user, newest first.

    Normally skips jobs whose score was computed within the last 24 hours.
    ``force`` is used when the user's default CV changes: every existing score
    was computed against the old CV, so anything scored before now is redone.
    It runs as a chain of BATCH_LIMIT-sized tasks carrying the same
    ``rescore_before`` timestamp until no stale score is left.
    """
    db = SessionLocal()
    cache = CacheService()
    try:
        uid = uuid.UUID(user_id)
        if force and rescore_before is None:
            rescore_before = datetime.now(UTC).isoformat()
        cutoff = (
            datetime.fromisoformat(rescore_before)
            if rescore_before
            else datetime.now(UTC) - timedelta(hours=24)
        )

        # Find recent postings not yet (freshly) scored for this user
        already_scored_subq = (
            db.query(JobMatchingScore.raw_job_posting_id)
            .filter(
                JobMatchingScore.user_id == uid,
                JobMatchingScore.computed_at >= cutoff,
            )
            .subquery()
        )

        # Newest first, so freshly scraped jobs get a score (and can trigger a
        # high-match alert) before older ones are refreshed.
        postings = (
            db.query(RawJobPosting)
            .filter(
                RawJobPosting.is_duplicate.is_(False),
                crud_job._is_live_deadline_clause(),
                ~RawJobPosting.id.in_(already_scored_subq),
            )
            .order_by(RawJobPosting.scraped_at.desc())
            .limit(BATCH_LIMIT)
            .all()
        )

        if not postings:
            return {"status": "ok", "scored": 0}

        service = MatchingService(db)
        scored = 0

        # Bulk-load existing score rows once instead of one SELECT per posting.
        existing_scores = {
            row.raw_job_posting_id: row
            for row in db.query(JobMatchingScore)
            .filter(
                JobMatchingScore.user_id == uid,
                JobMatchingScore.raw_job_posting_id.in_([p.id for p in postings]),
            )
            .all()
        }

        for posting in postings:
            job_data = {
                "description": posting.description,
                "title": posting.title,
                "salary_min": posting.salary_min,
                "salary_max": posting.salary_max,
                "location": posting.location,
                "remote_allowed": posting.remote_allowed,
            }

            try:
                result = service.calculate_match_score(uid, posting.id, job_data)
            except Exception:
                logger.warning(
                    "match_score_failed",
                    exc_info=True,
                    extra={"user_id": str(uid), "job_id": str(posting.id)},
                )
                continue

            # Upsert into job_matching_scores
            existing = existing_scores.get(posting.id)
            now = datetime.now(UTC)

            if existing:
                existing.overall_score = result["overall_score"]
                existing.skills_match = result["skills_match"]
                existing.experience_match = result["experience_match"]
                existing.salary_match = result["salary_match"]
                existing.education_match = result["education_match"]
                existing.location_match = result["location_match"]
                existing.explanation = result["explanation"]
                existing.computed_at = now
                existing.cached_at = now
            else:
                score_row = JobMatchingScore(
                    user_id=uid,
                    raw_job_posting_id=posting.id,
                    overall_score=result["overall_score"],
                    skills_match=result["skills_match"],
                    experience_match=result["experience_match"],
                    salary_match=result["salary_match"],
                    education_match=result["education_match"],
                    location_match=result["location_match"],
                    explanation=result["explanation"],
                    computed_at=now,
                    cached_at=now,
                )
                db.add(score_row)

            cache.set_cached_score(uid, posting.id, result)
            scored += 1

        db.commit()
        # A full batch means more stale scores may remain. Stop if nothing could
        # be scored, so postings that always fail cannot loop forever.
        if rescore_before and len(postings) == BATCH_LIMIT and scored > 0:
            compute_job_matching_scores.delay(user_id, rescore_before=rescore_before)
        return {"status": "ok", "scored": scored}

    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            raise
    finally:
        db.close()
