"""Celery task: compute job matching scores for a user in the background."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.cache_service import CacheService
from app.db.session import SessionLocal
from app.models.job import JobMatchingScore, RawJobPosting
from app.services.matching_service import MatchingService
from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.matching.compute_job_matching_scores",
    max_retries=2,
    default_retry_delay=30,
)
def compute_job_matching_scores(self, user_id: str) -> dict:
    """Compute or refresh matching scores for all recent jobs for one user.

    Skips jobs whose score was computed within the last 24 hours.
    """
    db = SessionLocal()
    cache = CacheService()
    try:
        uid = uuid.UUID(user_id)
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        # Find recent postings not yet (freshly) scored for this user
        already_scored_subq = (
            db.query(JobMatchingScore.raw_job_posting_id)
            .filter(
                JobMatchingScore.user_id == uid,
                JobMatchingScore.computed_at >= cutoff,
            )
            .subquery()
        )

        postings = (
            db.query(RawJobPosting)
            .filter(
                RawJobPosting.is_duplicate.is_(False),
                ~RawJobPosting.id.in_(already_scored_subq),
            )
            .limit(200)
            .all()
        )

        if not postings:
            return {"status": "ok", "scored": 0}

        service = MatchingService(db)
        scored = 0

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
                continue

            # Upsert into job_matching_scores
            existing = (
                db.query(JobMatchingScore)
                .filter(
                    JobMatchingScore.user_id == uid,
                    JobMatchingScore.raw_job_posting_id == posting.id,
                )
                .first()
            )
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
        return {"status": "ok", "scored": scored}

    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            raise
    finally:
        db.close()
