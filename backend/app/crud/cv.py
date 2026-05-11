import uuid

from sqlalchemy.orm import Session

from app.models.cv import CV


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
