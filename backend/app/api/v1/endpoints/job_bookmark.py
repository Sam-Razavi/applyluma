"""Browser-extension job bookmark endpoint."""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job as crud_job
from app.crud import job_description as crud_jd
from app.models.user import User
from app.schemas.job import ExternalJobBookmarkRequest
from app.schemas.job_description import JobDescriptionPublic, JobDescriptionUpdate
from app.services.matching_service import MatchingService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs/bookmark", tags=["job-bookmark"])


@router.post("", response_model=JobDescriptionPublic, status_code=status.HTTP_201_CREATED)
def bookmark_external_job(
    body: ExternalJobBookmarkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDescriptionPublic:
    """Save a job submitted from the browser extension.

    Creates a RawJobPosting if the URL hasn't been seen before, then
    creates (or returns the existing) JobDescription for the current user.
    Triggers an instant match score computation if none exists yet.
    Idempotent: re-bookmarking the same URL returns the existing record.
    """
    posting = crud_job.get_raw_job_by_url(db, body.url)
    if posting is None:
        posting = crud_job.create_raw_job_from_external(db, body)

    jd = crud_jd.get_or_create_from_raw_job(
        db,
        user_id=current_user.id,
        raw_job_posting_id=posting.id,
        list_name="Extension",
    )

    # Persist user's note if provided — wrapped so a DB hiccup never blocks the save.
    if body.notes and jd:
        try:
            crud_jd.update(db, jd, JobDescriptionUpdate(notes=body.notes))
        except Exception:
            log.exception("Failed to persist notes for job description %s — skipping", jd.id)

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

    return JobDescriptionPublic.model_validate(jd)


@router.get("/saved-urls")
def get_saved_urls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[str]]:
    """Return all job URLs the current user has saved as job descriptions.

    Used by the extension background worker to populate the badge cache.
    """
    urls = crud_jd.list_saved_urls(db, current_user.id)
    return {"urls": urls}
