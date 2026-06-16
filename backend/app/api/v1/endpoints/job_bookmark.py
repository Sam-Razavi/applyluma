"""Browser-extension job bookmark endpoint."""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job as crud_job
from app.models.user import User
from app.schemas.job import ExternalJobBookmarkRequest, SavedJobSchema, SaveJobRequest
from app.services.matching_service import MatchingService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs/bookmark", tags=["job-bookmark"])


@router.post("", response_model=SavedJobSchema, status_code=status.HTTP_201_CREATED)
def bookmark_external_job(
    body: ExternalJobBookmarkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedJobSchema:
    """Save a job submitted from the browser extension.

    Creates a RawJobPosting if the URL hasn't been seen before, then
    creates (or returns the existing) SavedJob for the current user.
    Triggers an instant match score computation if none exists yet.
    Idempotent: re-bookmarking the same URL returns the existing record.
    """
    posting = crud_job.get_raw_job_by_url(db, body.url)
    if posting is None:
        posting = crud_job.create_raw_job_from_external(db, body)

    saved = crud_job.get_saved_job_by_raw_id(db, current_user.id, posting.id)
    if saved is None:
        saved = crud_job.save_job(
            db,
            user_id=current_user.id,
            body=SaveJobRequest(job_id=posting.id, list_name="Extension"),
        )

    # Persist user's note if provided — wrapped so a DB hiccup never blocks the save.
    if body.notes:
        try:
            crud_job.update_saved_job_notes(db, saved.id, body.notes)
        except Exception:
            log.exception("Failed to persist notes for saved job %s — skipping", saved.id)

    # Compute match score synchronously if not already cached.
    if crud_job.get_job_matching_score(db, current_user.id, posting.id) is None:
        try:
            svc = MatchingService(db)
            scores = svc.calculate_match_score(
                current_user.id,
                posting.id,
                {
                    "title": body.title,
                    "description": body.description,
                    "salary_min": None,
                    "salary_max": None,
                    "location": None,
                    "remote_allowed": False,
                },
            )
            crud_job.upsert_job_matching_score(db, current_user.id, posting.id, scores)
        except Exception:
            log.exception("Instant scoring failed for posting %s — skipping", posting.id)

    return saved


@router.get("/saved-urls")
def get_saved_urls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return all job URLs the current user has bookmarked via the extension.

    Used by the extension background worker to populate the badge cache.
    """
    urls = crud_job.list_saved_job_urls(db, current_user.id)
    return {"urls": urls}
