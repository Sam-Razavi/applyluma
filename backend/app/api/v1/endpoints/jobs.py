"""Phase 10A: job discovery endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job as crud_job
from app.models.user import User
from app.schemas.job import JobDetailSchema, JobWithScoreSchema, KeywordsByTypeSchema

router = APIRouter(prefix="/jobs", tags=["jobs-discovery"])


@router.get("", response_model=list[JobWithScoreSchema])
def list_jobs(
    location: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    keywords: Annotated[str | None, Query(description="Comma-separated keywords")] = None,
    source: str | None = None,
    match_score_min: float | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern="^(score_desc|salary_desc|date_posted)$")] = "score_desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None
    return crud_job.list_jobs(
        db,
        user_id=current_user.id,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        keywords=keyword_list,
        source=source,
        match_score_min=match_score_min,
        page=page,
        limit=limit,
        sort=sort,
    )


@router.get("/{job_id}", response_model=JobDetailSchema)
def get_job_detail(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    job = crud_job.get_job_with_score(db, job_id=job_id, user_id=current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}/keywords", response_model=KeywordsByTypeSchema)
def get_job_keywords(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    return crud_job.get_job_keywords(db, job_id=job_id)
