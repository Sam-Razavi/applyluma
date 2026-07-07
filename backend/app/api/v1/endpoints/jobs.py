"""Phase 10A: job discovery endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job as crud_job
from app.models.cv import CV
from app.models.user import User
from app.schemas.job import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    JobDetailSchema,
    JobSourceSchema,
    JobWithScoreSchema,
    KeywordsByTypeSchema,
)
from app.services.keyword_extractor import KeywordExtractor

router = APIRouter(prefix="/jobs", tags=["jobs-discovery"])


@router.get("", response_model=list[JobWithScoreSchema])
def list_jobs(
    location: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    keywords: Annotated[str | None, Query(description="Comma-separated keywords")] = None,
    source: str | None = None,
    is_remote: bool | None = None,
    match_score_min: float | None = None,
    search: Annotated[str | None, Query(description="Search job title or company")] = None,
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
        is_remote=is_remote,
        match_score_min=match_score_min,
        search=search,
        page=page,
        limit=limit,
        sort=sort,
    )


@router.post("/analyze-text", response_model=AnalyzeTextResponse)
def analyze_text(
    body: AnalyzeTextRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Extract keywords from arbitrary job text and compare against the user's CV."""
    if not body.description.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Description must not be empty",
        )

    extractor = KeywordExtractor()
    job_keywords = extractor.extract_keywords(body.description)

    all_job_skills: list[str] = []
    keywords_response: dict[str, list[str]] = {}
    for category, items in job_keywords.items():
        keywords_response[category] = [item["keyword"] for item in items]
        all_job_skills.extend(keywords_response[category])

    cv = (
        db.query(CV)
        .filter(CV.user_id == current_user.id, CV.is_default.is_(True))
        .first()
    )

    matched: list[str] = []
    missing: list[str] = []
    if cv and cv.content and all_job_skills:
        cv_extracted = extractor.extract_keywords(cv.content)
        cv_skills: set[str] = {
            item["keyword"].lower()
            for items in cv_extracted.values()
            for item in items
        }
        matched = [s for s in all_job_skills if s.lower() in cv_skills]
        missing = [s for s in all_job_skills if s.lower() not in cv_skills]

    return {
        "keywords": keywords_response,
        "matched_skills": matched,
        "missing_skills": missing,
    }


@router.get("/sources", response_model=list[JobSourceSchema])
def list_job_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Distinct job sources present in the database, with live posting counts."""
    return crud_job.list_sources(db)


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return crud_job.get_job_keywords(db, job_id=job_id)
