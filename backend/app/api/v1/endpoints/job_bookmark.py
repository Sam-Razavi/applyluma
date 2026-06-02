"""Browser-extension job bookmark endpoint."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job as crud_job
from app.models.user import User
from app.schemas.job import ExternalJobBookmarkRequest, SaveJobRequest, SavedJobSchema

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

    return saved
