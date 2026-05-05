import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import cv as crud_cv
from app.models.user import User
from app.schemas.cv import CVPublic, CVSummary, CVUpdate
from app.services.cv_parser import parse_cv

router = APIRouter(prefix="/cvs", tags=["cvs"])

# Maps accepted content-types → canonical extension.
# Extension fallback handles browsers that send application/octet-stream for DOCX.
_CONTENT_TYPE_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _resolve_extension(content_type: str, original_filename: str) -> str | None:
    if content_type in _CONTENT_TYPE_EXT:
        return _CONTENT_TYPE_EXT[content_type]
    ext = Path(original_filename).suffix.lower()
    return ext if ext in _ALLOWED_EXTENSIONS else None


@router.post("/upload", response_model=CVPublic, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile,
    title: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVPublic:
    original_name = file.filename or "upload"
    ext = _resolve_extension(file.content_type or "", original_name)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are accepted",
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )

    # Store file: {STORAGE_DIR}/cvs/{user_id}/{uuid}{ext}
    user_dir = Path(settings.STORAGE_DIR) / "cvs" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    file_path = user_dir / stored_name
    file_path.write_bytes(file_bytes)

    try:
        content = parse_cv(file_path, ext)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the file. Make sure it is not password-protected.",
        )

    is_first = crud_cv.count_for_user(db, current_user.id) == 0
    cv_title = title or Path(original_name).stem or "My CV"
    # Relative path from STORAGE_DIR — used to reconstruct the full path later
    relative_url = f"cvs/{current_user.id}/{stored_name}"

    cv = crud_cv.create(
        db,
        user_id=current_user.id,
        title=cv_title,
        filename=original_name,
        file_url=relative_url,
        content=content,
        is_default=is_first,
    )
    return cv


@router.get("", response_model=list[CVSummary])
def list_cvs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CVSummary]:
    return crud_cv.list_for_user(db, current_user.id)


@router.get("/{cv_id}", response_model=CVPublic)
def get_cv(
    cv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVPublic:
    cv = crud_cv.get_by_id(db, cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return cv


@router.patch("/{cv_id}", response_model=CVPublic)
def update_cv(
    cv_id: uuid.UUID,
    body: CVUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVPublic:
    cv = crud_cv.get_by_id(db, cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    if body.title is not None:
        cv.title = body.title
    db.commit()
    db.refresh(cv)
    return cv


@router.patch("/{cv_id}/set-default", response_model=CVPublic)
def set_default_cv(
    cv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVPublic:
    cv = crud_cv.get_by_id(db, cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return crud_cv.set_default(db, cv)


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cv(
    cv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    cv = crud_cv.get_by_id(db, cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")

    if cv.file_url:
        file_path = Path(settings.STORAGE_DIR) / cv.file_url
        file_path.unlink(missing_ok=True)

    crud_cv.delete(db, cv)
