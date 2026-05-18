import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    related_id: uuid.UUID | None = None,
    related_type: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        related_id=related_id,
        related_type=related_type,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_for_user(
    db: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Notification], int, int]:
    base_query = db.query(Notification).filter(Notification.user_id == user_id)
    total = base_query.count()
    unread_count = base_query.filter(Notification.is_read.is_(False)).count()
    items = (
        base_query.order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total, unread_count


def mark_read(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notification:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return int(updated or 0)
