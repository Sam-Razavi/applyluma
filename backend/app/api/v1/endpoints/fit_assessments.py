"""AI-assisted job-fit assessment (thesis component; thesis/DESIGN.md).

The assessment runs only when the user asks for it, on one job at a time,
against their default CV (the CV the rule-based match score uses).
"""

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import fit_assessment as crud_fit
from app.models.cv import CV
from app.models.fit_assessment import FitAssessment
from app.models.job import RawJobPosting
from app.models.user import User, UserRole
from app.schemas.fit_assessment import (
    FitAssessmentPublic,
    FitAssessmentRequest,
    FitAssessmentStatus,
)
from app.services import fit_advisor
from app.tasks.fit_assessment import ad_text_for, run_fit_assessment

router = APIRouter(prefix="/fit-assessments", tags=["fit-assessments"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]

_DAILY_LIMIT: dict[UserRole, int | None] = {
    UserRole.user: 5,
    UserRole.premium: 30,
    UserRole.admin: None,
}

_ROLES_BY_ACCESS: dict[str, set[UserRole]] = {
    "admin": {UserRole.admin},
    "premium": {UserRole.admin, UserRole.premium},
    "all": {UserRole.admin, UserRole.premium, UserRole.user},
}


def _enabled_for(user: User) -> bool:
    if not settings.OPENAI_API_KEY:
        return False
    return user.role in _ROLES_BY_ACCESS.get(settings.FIT_ASSESSMENT_ACCESS, set())


def _require_enabled(user: User) -> None:
    # 404, not 403: to everyone else the feature does not exist yet.
    if not _enabled_for(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available")


def _public(row: FitAssessment) -> FitAssessmentPublic:
    public = FitAssessmentPublic.model_validate(row)
    public.result = row.result_json
    return public


def _input_hash(cv_text: str, ad_text: str) -> str:
    parts = (fit_advisor.MODEL, fit_advisor.PROMPT_VERSION, fit_advisor.RULES_VERSION, cv_text, ad_text)
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


@router.get("/status", response_model=FitAssessmentStatus)
def get_status(current_user: CurrentUser, db: DbSession) -> FitAssessmentStatus:
    if not _enabled_for(current_user):
        return FitAssessmentStatus(enabled=False)
    return FitAssessmentStatus(
        enabled=True,
        daily_limit=_DAILY_LIMIT.get(current_user.role, 5),
        used_today=crud_fit.count_today(db, current_user.id),
    )


@router.get("/latest", response_model=FitAssessmentPublic | None)
def get_latest(
    current_user: CurrentUser,
    db: DbSession,
    raw_job_posting_id: uuid.UUID = Query(...),
) -> FitAssessmentPublic | None:
    """The user's newest assessment of this job, or null."""
    _require_enabled(current_user)
    row = crud_fit.get_latest_for_posting(db, current_user.id, raw_job_posting_id)
    return _public(row) if row else None


@router.post("", response_model=FitAssessmentPublic, status_code=status.HTTP_202_ACCEPTED)
def request_assessment(
    body: FitAssessmentRequest,
    response: Response,
    current_user: CurrentUser,
    db: DbSession,
) -> FitAssessmentPublic:
    _require_enabled(current_user)

    posting = db.query(RawJobPosting).filter(RawJobPosting.id == body.raw_job_posting_id).first()
    if not posting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not (posting.description or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This job ad has no text to assess",
        )

    cv = db.query(CV).filter(CV.user_id == current_user.id, CV.is_default.is_(True)).first()
    if not cv or not (cv.content or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload a CV and set it as default before assessing a job",
        )

    input_hash = _input_hash(cv.content or "", ad_text_for(posting))
    if not body.force:
        existing = crud_fit.get_reusable(db, current_user.id, input_hash)
        if existing:
            # Same CV, same ad, same versions: show the stored assessment.
            response.status_code = status.HTTP_200_OK
            return _public(existing)

    limit = _DAILY_LIMIT.get(current_user.role, 5)
    if limit is not None and crud_fit.count_today(db, current_user.id) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily assessment limit reached ({limit}/day).",
        )

    row = crud_fit.create(
        db,
        user_id=current_user.id,
        cv_id=cv.id,
        raw_job_posting_id=posting.id,
        job_title=posting.title,
        company=posting.company,
        model=fit_advisor.MODEL,
        prompt_version=fit_advisor.PROMPT_VERSION,
        rules_version=fit_advisor.RULES_VERSION,
        input_hash=input_hash,
    )
    task = run_fit_assessment.delay(str(row.id))
    row = crud_fit.set_task_id(db, row, task.id)
    return _public(row)


@router.get("/{assessment_id}", response_model=FitAssessmentPublic)
def get_assessment(
    assessment_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> FitAssessmentPublic:
    _require_enabled(current_user)
    row = crud_fit.get_by_id(db, assessment_id, current_user.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return _public(row)
