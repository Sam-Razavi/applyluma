"""The signed-in user's own forwarding address, for the Settings page.

The address is a bearer credential (anyone who has it can post mail into the
account), so it is only ever returned to its owner, and the owner can replace
it at any time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.crud import inbound_email as crud_inbound_email
from app.crud import user as crud_user
from app.models.user import User, UserRole
from app.services.inbound_email.address import build_inbox_address
from app.services.inbound_email.forwarded import (
    GMAIL_FORWARDING_SENDER,
    parse_gmail_confirmation,
)

router = APIRouter(prefix="/email-forwarding", tags=["email-forwarding"])

# Gmail's confirmation link expires; an old code is only confusing.
_CONFIRMATION_MAX_AGE = timedelta(days=7)


class GmailConfirmation(BaseModel):
    code: str | None = None
    link: str | None = None
    received_at: datetime | None = None


class EmailForwardingStatus(BaseModel):
    enabled: bool
    address: str | None = None
    emails_received: int = 0
    last_received_at: datetime | None = None
    gmail_confirmation: GmailConfirmation | None = None


class ForwardedEmail(BaseModel):
    id: uuid.UUID
    from_address: str
    subject: str | None = None
    snippet: str | None = None
    received_at: datetime | None = None
    created_at: datetime
    classification: str | None = None
    suggested_status: str | None = None
    evidence: str | None = None
    # none / pending / accepted / dismissed
    suggestion_state: str
    application_id: uuid.UUID | None = None
    company_name: str | None = None
    job_title: str | None = None


class ForwardedEmailList(BaseModel):
    items: list[ForwardedEmail]
    total: int


def _configured() -> bool:
    return bool(settings.INBOUND_EMAIL_WEBHOOK_SECRET and settings.INBOUND_EMAIL_DOMAIN)


def _enabled_for(user: User) -> bool:
    return _configured() and (
        settings.INBOUND_EMAIL_USER_ENABLED or user.role == UserRole.admin
    )


def _status(db: Session, user: User) -> EmailForwardingStatus:
    crud_user.ensure_inbox_token(db, user)
    count, latest = crud_inbound_email.forwarding_stats(db, user.id)

    confirmation = None
    row = crud_inbound_email.latest_from_sender(
        db, user.id, GMAIL_FORWARDING_SENDER, datetime.now(UTC) - _CONFIRMATION_MAX_AGE
    )
    # Mail arriving after Gmail's confirmation means forwarding is set up, so
    # the prompt to confirm would only be noise.
    if row is not None and latest is not None and latest > row.created_at:
        row = None
    if row is not None:
        parsed = parse_gmail_confirmation(row.subject, row.snippet)
        if parsed is not None:
            confirmation = GmailConfirmation(
                code=parsed.code, link=parsed.link, received_at=row.created_at
            )

    return EmailForwardingStatus(
        enabled=True,
        address=build_inbox_address(user),
        emails_received=count,
        last_received_at=latest,
        gmail_confirmation=confirmation,
    )


@router.get("", response_model=EmailForwardingStatus)
def get_email_forwarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailForwardingStatus:
    if not _enabled_for(current_user):
        return EmailForwardingStatus(enabled=False)
    return _status(db, current_user)


@router.post("/rotate", response_model=EmailForwardingStatus)
def rotate_email_forwarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailForwardingStatus:
    """Replace the forwarding address. Mail sent to the old one is ignored."""
    if not _enabled_for(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available")
    crud_user.rotate_inbox_token(db, current_user)
    return _status(db, current_user)


@router.get("/messages", response_model=ForwardedEmailList)
def list_forwarded_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    matched: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForwardedEmailList:
    """The user's own forwarded emails and what ApplyLuma made of each."""
    rows, total = crud_inbound_email.list_for_user(
        db,
        current_user.id,
        skip=skip,
        limit=limit,
        matched=matched,
        # Gmail's confirmation is setup plumbing, shown on the Settings card.
        exclude_sender=GMAIL_FORWARDING_SENDER,
    )
    items = [
        ForwardedEmail(
            id=row.id,
            from_address=row.from_address,
            subject=row.subject,
            snippet=row.snippet,
            received_at=row.received_at,
            created_at=row.created_at,
            classification=row.classification,
            suggested_status=row.suggested_status,
            evidence=row.evidence,
            suggestion_state=row.suggestion_state,
            application_id=row.matched_application_id,
            company_name=company_name,
            job_title=job_title,
        )
        for row, company_name, job_title in rows
    ]
    return ForwardedEmailList(items=items, total=total)


@router.delete("/messages/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_forwarded_email(
    email_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not crud_inbound_email.delete_for_user(db, email_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
