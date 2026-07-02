import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import job_description as crud_jd
from app.models.user import User
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionPublic,
    JobDescriptionSummary,
    JobDescriptionUpdate,
    SaveFromRawJobRequest,
)
from app.services.keyword_extractor import KeywordExtractor
from app.services.url_scraper import scrape_job_url

_extractor = KeywordExtractor()

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


class ScrapeUrlRequest(BaseModel):
    url: HttpUrl


class ScrapeUrlResult(BaseModel):
    company_name: str
    job_title: str
    description: str
    url: str


@router.post("/scrape-url", response_model=ScrapeUrlResult)
async def scrape_url(
    body: ScrapeUrlRequest,
    current_user: User = Depends(get_current_user),
) -> ScrapeUrlResult:
    url_str = str(body.url)
    try:
        result = await scrape_job_url(url_str)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to fetch URL (HTTP {exc.response.status_code})",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not scrape the provided URL. Check that the URL is publicly accessible and try again.",
        ) from exc
    return ScrapeUrlResult(**result)


@router.post("", response_model=JobDescriptionPublic, status_code=status.HTTP_201_CREATED)
def create_job_description(
    body: JobDescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDescriptionPublic:
    extracted = _extractor.extract_keywords(body.description)
    keywords = _extractor.keywords_as_flat_list(extracted, min_confidence=0.6)
    return crud_jd.create(db, user_id=current_user.id, body=body, keywords=keywords)


@router.post("/from-discover", response_model=JobDescriptionPublic, status_code=status.HTTP_201_CREATED)
def save_from_discover(
    body: SaveFromRawJobRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDescriptionPublic:
    jd = crud_jd.get_or_create_from_raw_job(
        db,
        user_id=current_user.id,
        raw_job_posting_id=body.raw_job_posting_id,
        list_name=body.list_name,
        notes=body.notes,
    )
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")
    return jd


@router.get("", response_model=list[JobDescriptionSummary])
def list_job_descriptions(
    list_name: str | None = None,
    sort: str = "newest",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobDescriptionSummary]:
    return crud_jd.list_for_user(db, current_user.id, list_name=list_name, sort=sort)


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


@router.patch("/{jd_id}", response_model=JobDescriptionPublic)
def update_job_description(
    jd_id: uuid.UUID,
    body: JobDescriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobDescriptionPublic:
    jd = crud_jd.get_by_id(db, jd_id, current_user.id)
    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")
    return crud_jd.update(db, jd, body)


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
