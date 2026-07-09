"""Authenticated in-app feedback.

Stores into the same contact_submissions table as the public contact form
(source='in_app'), so admins triage everything in one inbox at /admin/contact.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

# Reuse the contact form's admin-notification email template so both intake
# paths look identical in the admin's inbox email.
from app.api.v1.endpoints.contact import _admin_html
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import admin as crud_admin
from app.models.user import User
from app.schemas.contact import FeedbackRequest
from app.services import email_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    name = current_user.full_name or current_user.email
    subject = body.subject.strip() or f"In-app feedback ({body.category})"

    crud_admin.create_contact_submission(
        db,
        name=name,
        email=current_user.email,
        subject=subject,
        message=body.message,
        user_id=current_user.id,
        category=body.category,
        source="in_app",
    )

    email_service.send_email(
        to_email=settings.CONTACT_RECIPIENT_EMAIL,
        subject=f"[ApplyLuma Feedback] [{body.category}] {subject}",
        html_body=_admin_html(name, current_user.email, subject, body.message),
    )

    return {"ok": True}
