import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import notification as crud_notification
from app.models.user import User
from app.schemas.notification import NotificationList, NotificationPublic

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
def list_notifications(
    skip: int = 0,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationList:
    items, total, unread_count = crud_notification.get_for_user(db, current_user.id, skip, limit)
    return NotificationList(
        items=items,
        total=total,
        unread_count=unread_count,
        skip=skip,
        limit=limit,
    )


@router.patch("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPublic:
    notification = crud_notification.mark_read(db, notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/mark-all-read")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    updated = crud_notification.mark_all_read(db, current_user.id)
    return {"updated": updated}
