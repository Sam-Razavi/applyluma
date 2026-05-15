import uuid

from sqlalchemy.orm import Session

from app.crud import notification as crud_notification
from app.services import email_service


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str,
    related_id: uuid.UUID | None = None,
    related_type: str | None = None,
    send_email: bool = False,
    email: str | None = None,
):
    notification = crud_notification.create(
        db,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        related_id=related_id,
        related_type=related_type,
    )
    if send_email and email:
        subject, html_body = email_service.template_email(type, title, body)
        email_service.send_email(email, subject, html_body)
    return notification
