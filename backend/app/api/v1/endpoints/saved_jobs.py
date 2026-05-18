"""Phase 10A: saved-jobs collection endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job as crud_job
from app.models.user import User
from app.schemas.job import SavedJobSchema, SaveJobRequest, UpdateSavedJobRequest

router = APIRouter(prefix="/saved-jobs", tags=["saved-jobs"])


@router.post("", response_model=SavedJobSchema, status_code=status.HTTP_201_CREATED)
def save_job(
    body: SaveJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedJobSchema:
    return crud_job.save_job(db, user_id=current_user.id, body=body)


@router.get("", response_model=list[SavedJobSchema])
def list_saved_jobs(
    list_name: str | None = None,
    sort: str = "newest",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedJobSchema]:
    return crud_job.list_saved_jobs(db, user_id=current_user.id, list_name=list_name, sort=sort)


@router.patch("/{saved_job_id}", response_model=SavedJobSchema)
def update_saved_job(
    saved_job_id: uuid.UUID,
    body: UpdateSavedJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedJobSchema:
    saved = crud_job.get_saved_job(db, saved_job_id=saved_job_id, user_id=current_user.id)
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found")
    return crud_job.update_saved_job(db, saved=saved, updates=body)


@router.delete("/{saved_job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_job(
    saved_job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    saved = crud_job.get_saved_job(db, saved_job_id=saved_job_id, user_id=current_user.id)
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found")
    crud_job.delete_saved_job(db, saved=saved)
