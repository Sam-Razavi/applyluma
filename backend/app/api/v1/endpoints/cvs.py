import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import cv as crud_cv
from app.models.user import User
from app.schemas.cv import CVPublic, CVSummary, CVUpdate
from app.services.cv_parser import parse_cv
from app.services.pdf_generator import generate_cv_pdf

router = APIRouter(prefix="/cvs", tags=["cvs"])

# Maps accepted content-types → canonical extension.
# Extension fallback handles browsers that send application/octet-stream for DOCX.
_CONTENT_TYPE_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}
_PDF_MEDIA_TYPE = "application/pdf"


def _resolve_extension(content_type: str, original_filename: str) -> str | None:
    if content_type in _CONTENT_TYPE_EXT:
        return _CONTENT_TYPE_EXT[content_type]
    ext = Path(original_filename).suffix.lower()
    return ext if ext in _ALLOWED_EXTENSIONS else None


def _storage_path(relative_url: str) -> Path:
    storage_root = Path(settings.STORAGE_DIR).resolve()
    file_path = (storage_root / relative_url).resolve()
    if storage_root != file_path and storage_root not in file_path.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server",
        )
    return file_path


def _pdf_download_name(cv_title: str, cv_filename: str | None) -> str:
    stem = Path(cv_filename or cv_title or "cv").stem
    safe_stem = "".join(
        char if char.isalnum() or char in (" ", "-", "_", ".") else "_" for char in stem
    )
    return f"{safe_stem.strip() or 'cv'}.pdf"


def _sections_from_text(content: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_name = ""
    current_lines: list[str] = []

    def append_section() -> None:
        text = "\n".join(line for line in current_lines).strip()
        if text:
            sections.append({"section_name": current_name, "content": text})

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            append_section()
            current_name = stripped.removeprefix("## ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    append_section()
    return sections or [{"section_name": "", "content": content}]


def _generated_pdf_path(cv_id: uuid.UUID, user_id: uuid.UUID, file_url: str | None) -> Path:
    if file_url:
        existing_path = _storage_path(file_url)
        if existing_path.suffix.lower() == ".pdf":
            return existing_path
    return Path(settings.STORAGE_DIR).resolve() / "cvs" / str(user_id) / f"{cv_id}.pdf"


def _ensure_downloadable_pdf(cv, db: Session) -> Path:
    if cv.file_url:
        file_path = _storage_path(cv.file_url)
        if file_path.exists() and file_path.suffix.lower() == ".pdf":
            return file_path

    if not cv.content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF or extractable CV content is available for download",
        )

    output_path = _generated_pdf_path(cv.id, cv.user_id, cv.file_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        return output_path

    generate_cv_pdf(_sections_from_text(cv.content), output_path)

    if not cv.file_url:
        relative_url = output_path.relative_to(Path(settings.STORAGE_DIR).resolve()).as_posix()
        cv.file_url = relative_url
        cv.filename = _pdf_download_name(cv.title, cv.filename)
        db.commit()
        db.refresh(cv)

    return output_path


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


@router.get("/{cv_id}/download")
def download_cv(
    cv_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    cv = crud_cv.get_by_id(db, cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    file_path = _ensure_downloadable_pdf(cv, db)
    download_name = _pdf_download_name(cv.title, cv.filename)
    return FileResponse(path=str(file_path), media_type=_PDF_MEDIA_TYPE, filename=download_name)


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

    generated_pdf = (
        Path(settings.STORAGE_DIR).resolve() / "cvs" / str(current_user.id) / f"{cv.id}.pdf"
    )
    if not cv.file_url or generated_pdf != (Path(settings.STORAGE_DIR) / cv.file_url).resolve():
        generated_pdf.unlink(missing_ok=True)

    crud_cv.delete(db, cv)
