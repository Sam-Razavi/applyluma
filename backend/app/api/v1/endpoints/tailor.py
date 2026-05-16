import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import cv as crud_cv
from app.crud import job_description as crud_jd
from app.crud import tailor_job as crud_tailor
from app.models.tailor_job import TailorStatus
from app.models.user import User, UserRole
from app.schemas.tailor import (
    TailorJobPublic,
    TailorMeta,
    TailorPreviewResponse,
    TailorSaveRequest,
    TailorSaveResponse,
    TailorSection,
    TailorStatusResponse,
    TailorSubmitRequest,
    TailorUsageResponse,
)
from app.services.pdf_generator import generate_cv_pdf
from app.tasks.tailor import run_tailoring

router = APIRouter(prefix="/tailor", tags=["tailor"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]

_DAILY_LIMIT: dict[UserRole, int | None] = {
    UserRole.user: 1,
    UserRole.premium: 10,
    UserRole.admin: None,
}


def _check_rate_limit(db: Session, user: User) -> None:
    limit = _DAILY_LIMIT.get(user.role, 1)
    if limit is None:
        return
    used = crud_tailor.count_today(db, user.id)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily tailoring limit reached ({limit}/day). Upgrade to premium for more.",
        )


@router.get("/usage", response_model=TailorUsageResponse)
def get_usage(
    current_user: CurrentUser,
    db: DbSession,
) -> TailorUsageResponse:
    used = crud_tailor.count_today(db, current_user.id)
    limit = _DAILY_LIMIT.get(current_user.role, 1)
    now = datetime.now(UTC)
    next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return TailorUsageResponse(
        used_today=used,
        daily_limit=limit,
        resets_at=next_midnight,
    )


@router.get("/history", response_model=list[TailorJobPublic])
def list_history(
    current_user: CurrentUser,
    db: DbSession,
) -> list[TailorJobPublic]:
    return crud_tailor.list_for_user(db, current_user.id)


@router.post("/submit", response_model=TailorJobPublic, status_code=status.HTTP_202_ACCEPTED)
def submit_tailoring(
    body: TailorSubmitRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TailorJobPublic:
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found"
        )

    job = crud_tailor.create(
        db,
        user_id=current_user.id,
        cv_id=body.cv_id,
        job_description_id=jd.id,
        intensity=body.intensity,
    )

    task = run_tailoring.delay(str(job.id))
    job = crud_tailor.set_task_id(db, job, task.id)
    return job


@router.get("/{job_id}/status", response_model=TailorStatusResponse)
def get_status(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> TailorStatusResponse:
    job = crud_tailor.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailoring job not found")
    return TailorStatusResponse(
        id=job.id,
        status=job.status,
        error_message=job.error_message,
        language=job.language,
        output_cv_id=job.output_cv_id,
    )


@router.get("/{job_id}/preview", response_model=TailorPreviewResponse)
def get_preview(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> TailorPreviewResponse:
    job = crud_tailor.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailoring job not found")
    if job.status != TailorStatus.complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not complete (status: {job.status.value})",
        )

    result = job.result_json or {}
    sections = [
        TailorSection(
            section_id=s["section_id"],
            section_name=s["section_name"],
            original=s["original"],
            tailored=s["tailored"],
            changes=s.get("changes", []),
        )
        for s in result.get("sections", [])
    ]
    meta = TailorMeta(
        keywords_added=result.get("meta", {}).get("keywords_added", []),
        keywords_already_present=result.get("meta", {}).get("keywords_already_present", []),
        intensity_applied=result.get("meta", {}).get("intensity_applied", job.intensity.value),
    )

    return TailorPreviewResponse(
        job_id=job.id,
        language=job.language or result.get("language", "en"),
        sections=sections,
        meta=meta,
    )


@router.post("/{job_id}/save", response_model=TailorSaveResponse)
def save_tailored_cv(
    job_id: uuid.UUID,
    body: TailorSaveRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TailorSaveResponse:
    job = crud_tailor.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailoring job not found")
    if job.status != TailorStatus.complete:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tailoring job not complete",
        )
    if job.output_cv_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tailored CV already saved",
        )

    result = job.result_json or {}
    all_sections = result.get("sections", [])
    accepted_ids = set(body.accepted_section_ids) if body.accepted_section_ids is not None else None

    pdf_sections = []
    full_text_parts = []
    for section in all_sections:
        use_tailored = accepted_ids is None or section["section_id"] in accepted_ids
        content = section["tailored"] if use_tailored else section["original"]
        pdf_sections.append({"section_name": section["section_name"], "content": content})
        full_text_parts.append(f"## {section['section_name']}\n{content}")

    user_dir = Path(settings.STORAGE_DIR) / "cvs" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}_tailored.pdf"
    file_path = user_dir / stored_name
    generate_cv_pdf(pdf_sections, file_path)

    relative_url = f"cvs/{current_user.id}/{stored_name}"
    job_title = job.job_description.job_title if job.job_description else "target role"
    cv_title = body.cv_title or f"Tailored CV ({job_title})"
    full_text = "\n\n".join(full_text_parts)

    new_cv = crud_cv.create(
        db,
        user_id=current_user.id,
        title=cv_title,
        filename=stored_name,
        file_url=relative_url,
        content=full_text,
        is_default=False,
    )

    new_cv.is_tailored = True
    new_cv.parent_cv_id = job.cv_id
    new_cv.tailor_job_id = job.id
    db.commit()
    db.refresh(new_cv)

    crud_tailor.set_output_cv(db, job, new_cv.id)

    return TailorSaveResponse(
        cv_id=new_cv.id,
        title=new_cv.title,
        file_url=new_cv.file_url,
    )


@router.get("/{job_id}/download")
def download_tailored_cv(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> FileResponse:
    job = crud_tailor.get_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailoring job not found")
    if not job.output_cv_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tailored CV saved yet. Call /save first.",
        )
    cv = crud_cv.get_by_id(db, job.output_cv_id, current_user.id)
    if not cv or not cv.file_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailored CV file not found")
    file_path = Path(settings.STORAGE_DIR) / cv.file_url
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on server")
    download_name = cv.filename or f"{cv.title}.pdf"
    return FileResponse(path=str(file_path), media_type="application/pdf", filename=download_name)
