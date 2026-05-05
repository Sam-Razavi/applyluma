import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import cv as crud_cv
from app.crud import job_description as crud_jd
from app.models.user import User
from app.services.ai_service import analyze_cv_match

router = APIRouter(prefix="/ai", tags=["ai"])


class TailorCVRequest(BaseModel):
    cv_id: uuid.UUID
    job_description_id: uuid.UUID


class TailorCVResponse(BaseModel):
    match_score: int
    strengths: list[str]
    gaps: list[str]
    recommendations: list[str]
    full_analysis: str


@router.post("/tailor-cv", response_model=TailorCVResponse)
def tailor_cv(
    body: TailorCVRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TailorCVResponse:
    cv = crud_cv.get_by_id(db, body.cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")

    jd = crud_jd.get_by_id(db, body.job_description_id, current_user.id)
    if not jd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found"
        )

    if not cv.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CV has no parseable text content",
        )

    try:
        result = analyze_cv_match(
            cv_content=cv.content,
            jd_description=jd.description,
            jd_keywords=jd.keywords or [],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return TailorCVResponse(**result)
