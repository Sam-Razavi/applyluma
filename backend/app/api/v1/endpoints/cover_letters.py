import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import cover_letter_job as crud_cl
from app.crud import cv as crud_cv
from app.crud import job_description as crud_jd
from app.models.cover_letter_job import CoverLetterStatus
from app.models.user import User, UserRole
from app.schemas.cover_letter import (
    CoverLetterJobPublic,
    CoverLetterPreviewResponse,
    CoverLetterSaveRequest,
    CoverLetterStatusResponse,
    CoverLetterSubmitRequest,
    CoverLetterUsageResponse,
)
from app.services.pdf_generator import generate_cover_letter_pdf
from app.tasks.cover_letter import run_cover_letter

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]

_DAILY_LIMIT: dict[UserRole, int | None] = {
    UserRole.user: 2,
    UserRole.premium: 10,
    UserRole.admin: None,
}


def _check_rate_limit(db: Session, user: User) -> None:
    limit = _DAILY_LIMIT.get(user.role, 2)
    if limit is None:
        return
    used = crud_cl.count_today(db, user.id)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily cover letter limit reached ({limit}/day). Upgrade to premium for more.",
        )


@router.post("/generate", response_model=CoverLetterJobPublic, status_code=status.HTTP_202_ACCEPTED)
def generate(
    body: CoverLetterSubmitRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CoverLetterJobPublic:
    _check_rate_limit(db, current_user)

    cv = crud_cv.get_by_id(db, body.cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if not cv.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CV has no extractable text content",
        )

    if body.raw_job_posting_id:
        jd = crud_jd.get_or_create_from_raw_job(
            db,
            user_id=current_user.id,
            raw_job_posting_id=body.raw_job_posting_id,
        )
    else:
        jd = crud_jd.get_by_id(db, body.job_description_id, current_user.id)  # type: ignore[arg-type]

    if not jd:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")

    job = crud_cl.create(
        db,
        user_id=current_user.id,
        cv_id=body.cv_id,
        job_description_id=jd.id,
        tone=body.tone,
    )

    task = run_cover_letter.delay(str(job.id))
    job = crud_cl.set_task_id(db, job, task.id)
    return job


@router.get("/usage", response_model=CoverLetterUsageResponse)
def get_usage(
    current_user: CurrentUser,
    db: DbSession,
) -> CoverLetterUsageResponse:
    used = crud_cl.count_today(db, current_user.id)
    limit = _DAILY_LIMIT.get(current_user.role, 2)
    now = datetime.now(UTC)
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return CoverLetterUsageResponse(
        used_today=used,
        daily_limit=limit,
        resets_at=next_midnight,
    )


@router.get("/history", response_model=list[CoverLetterJobPublic])
def list_history(
    current_user: CurrentUser,
    db: DbSession,
) -> list[CoverLetterJobPublic]:
    return crud_cl.list_for_user(db, current_user.id)


@router.get("/{job_id}/status", response_model=CoverLetterStatusResponse)
def get_status(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> CoverLetterStatusResponse:
    job = crud_cl.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter job not found")
    return CoverLetterStatusResponse(
        id=job.id,
        status=job.status,
        error_message=job.error_message,
    )


@router.get("/{job_id}", response_model=CoverLetterPreviewResponse)
def get_cover_letter(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> CoverLetterPreviewResponse:
    job = crud_cl.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter job not found")
    if job.status != CoverLetterStatus.complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not complete (status: {job.status.value})",
        )
    return CoverLetterPreviewResponse(
        id=job.id,
        generated_text=job.generated_text or "",
        language=job.language or "en",
        word_count=job.word_count,
        tone=job.tone,
    )


@router.post("/{job_id}/save", response_model=CoverLetterJobPublic)
def save_cover_letter(
    job_id: uuid.UUID,
    body: CoverLetterSaveRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CoverLetterJobPublic:
    job = crud_cl.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter job not found")
    if job.status != CoverLetterStatus.complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cover letter job not complete",
        )
    return crud_cl.save(db, job, saved_text=body.saved_text, title=body.title)


@router.get("/{job_id}/download")
def download_cover_letter(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> FileResponse:
    job = crud_cl.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter job not found")
    if job.status != CoverLetterStatus.complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not complete (status: {job.status.value})",
        )
    text = job.saved_text or job.generated_text
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter has no content"
        )

    user_dir = Path(settings.STORAGE_DIR) / "cover_letters" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / f"{uuid.uuid4()}_cover_letter.pdf"
    generate_cover_letter_pdf(text, file_path, title=job.title)

    download_name = f"{job.title or 'cover-letter'}.pdf"
    return FileResponse(path=str(file_path), media_type="application/pdf", filename=download_name)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover_letter(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    job = crud_cl.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter job not found")
    crud_cl.delete(db, job)
