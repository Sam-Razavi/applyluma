import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.cv import CV
from app.schemas.cv import CVDiffResponse, CVDiffSection, CVVersionNode


def get_by_id(db: Session, cv_id: uuid.UUID, user_id: uuid.UUID) -> CV | None:
    return db.query(CV).filter(CV.id == cv_id, CV.user_id == user_id).first()


def list_for_user(db: Session, user_id: uuid.UUID) -> list[CV]:
    return db.query(CV).filter(CV.user_id == user_id).order_by(CV.created_at.desc()).all()


def count_for_user(db: Session, user_id: uuid.UUID) -> int:
    return db.query(CV).filter(CV.user_id == user_id).count()


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    title: str,
    filename: str,
    file_url: str,
    content: str,
    is_default: bool,
) -> CV:
    cv = CV(
        user_id=user_id,
        title=title,
        filename=filename,
        file_url=file_url,
        content=content,
        is_default=is_default,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


def set_default(db: Session, cv: CV) -> CV:
    # Unset all existing defaults for this user in one query, then set the new one.
    db.query(CV).filter(CV.user_id == cv.user_id, CV.is_default.is_(True)).update(
        {"is_default": False}, synchronize_session="fetch"
    )
    cv.is_default = True
    db.commit()
    db.refresh(cv)
    return cv


def delete(db: Session, cv: CV) -> None:
    was_default = cv.is_default
    user_id = cv.user_id
    db.delete(cv)
    db.commit()
    if was_default:
        _promote_next_default(db, user_id)


def get_version_tree(db: Session, root_cv_id: uuid.UUID) -> CVVersionNode | None:
    root = db.query(CV).filter(CV.id == root_cv_id).first()
    if not root:
        return None

    def build_node(cv: CV) -> CVVersionNode:
        children = (
            db.query(CV)
            .filter(CV.parent_cv_id == cv.id, CV.user_id == root.user_id)
            .order_by(CV.created_at.asc())
            .all()
        )
        return CVVersionNode(
            id=cv.id,
            title=cv.title,
            is_tailored=cv.is_tailored,
            created_at=cv.created_at,
            children=[build_node(child) for child in children],
        )

    return build_node(root)


def get_cv_diff(db: Session, cv_id: uuid.UUID, user_id: uuid.UUID) -> CVDiffResponse | None:
    cv = get_by_id(db, cv_id, user_id)
    if not cv or not cv.is_tailored or not cv.tailor_job:
        return None

    result_json = cv.tailor_job.result_json
    if not isinstance(result_json, dict):
        return None

    raw_sections = result_json.get("sections")
    if not isinstance(raw_sections, list):
        return None

    sections = [
        _parse_diff_section(section)
        for section in raw_sections
        if isinstance(section, dict)
    ]
    return CVDiffResponse(cv_id=cv.id, sections=sections)


def _parse_diff_section(section: dict[str, Any]) -> CVDiffSection:
    changes = section.get("changes", 0)
    if isinstance(changes, list):
        change_count = len(changes)
    elif isinstance(changes, int):
        change_count = changes
    elif changes:
        change_count = 1
    else:
        change_count = 0

    return CVDiffSection(
        name=str(section.get("name") or section.get("section_name") or ""),
        original=str(section.get("original") or ""),
        tailored=str(section.get("tailored") or ""),
        changes=change_count,
    )


def _promote_next_default(db: Session, user_id: uuid.UUID) -> None:
    """Make the oldest remaining CV the default after the previous default was deleted."""
    next_cv = (
        db.query(CV)
        .filter(CV.user_id == user_id)
        .order_by(CV.created_at.asc())
        .first()
    )
    if next_cv:
        next_cv.is_default = True
        db.commit()
