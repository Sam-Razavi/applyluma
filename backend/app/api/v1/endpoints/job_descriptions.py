import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job_description as crud_jd
from app.models.user import User
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionPublic,
    JobDescriptionSummary,
)
from app.services.keyword_extractor import extract_keywords

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


@router.post("", response_model=JobDescriptionPublic, status_code=status.HTTP_201_CREATED)
def create_job_description(
    body: JobDescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDescriptionPublic:
    keywords = extract_keywords(body.description)
    return crud_jd.create(db, user_id=current_user.id, body=body, keywords=keywords)


@router.get("", response_model=list[JobDescriptionSummary])
def list_job_descriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobDescriptionSummary]:
    return crud_jd.list_for_user(db, current_user.id)


@router.get("/{jd_id}", response_model=JobDescriptionPublic)
def get_job_description(
    jd_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDescriptionPublic:
    jd = crud_jd.get_by_id(db, jd_id, current_user.id)
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")
    return jd


@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_description(
    jd_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    jd = crud_jd.get_by_id(db, jd_id, current_user.id)
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")
    crud_jd.delete(db, jd)
