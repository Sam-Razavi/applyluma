"""Persistence for inbound email ingestion."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.inbound_email import SNIPPET_MAX_CHARS, InboundEmail
from app.services.inbound_email.matcher import MatchCandidate, MatchResult

# Ceiling on how many applications are scored for one message. A user with
# thousands of tracked applications should not turn one email into an unbounded
# scan; the newest are also the ones a reply is plausibly about.
MAX_CANDIDATES = 500


def truncate_snippet(text: str | None) -> str | None:
    """Cut a body down to the excerpt that may be stored.

    Called before the message reaches the queue, not after: the Celery broker
    is durable storage, so a full body handed to ``.delay()`` would outlive the
    request regardless of what the database holds.
    """
    if not text:
        return None
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    return collapsed[:SNIPPET_MAX_CHARS]


def exists_for_dedupe_key(db: Session, *, user_id: uuid.UUID, dedupe_key: str) -> bool:
    return (
        db.query(InboundEmail)
        .filter(InboundEmail.user_id == user_id, InboundEmail.dedupe_key == dedupe_key)
        .first()
        is not None
    )


def list_match_candidates(
    db: Session, user_id: uuid.UUID, limit: int = MAX_CANDIDATES
) -> list[MatchCandidate]:
    """Load the user's applications as plain matcher inputs.

    Selects columns rather than entities: the matcher takes dataclasses, and
    hydrating full ORM objects for a scoring pass would be wasted work.
    """
    rows = db.execute(
        select(Application.id, Application.company_name, Application.job_url)
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
        .limit(limit)
    ).all()
    return [
        MatchCandidate(application_id=row[0], company_name=row[1], job_url=row[2]) for row in rows
    ]


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    dedupe_key: str,
    message_id: str | None,
    from_address: str,
    from_domain: str,
    subject: str | None,
    snippet: str | None,
    received_at: datetime | None,
    vendor: str,
    match: MatchResult,
) -> InboundEmail:
    row = InboundEmail(
        user_id=user_id,
        dedupe_key=dedupe_key,
        message_id=message_id,
        from_address=from_address,
        from_domain=from_domain,
        subject=subject,
        snippet=truncate_snippet(snippet),
        received_at=received_at,
        vendor=vendor,
        matched_application_id=match.application_id,
        match_confidence=match.confidence,
        match_method=match.method,
        match_reason=match.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_for_admin(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    matched: bool | None = None,
) -> tuple[list[tuple[InboundEmail, str | None, str | None]], int]:
    """Return ``(rows, total)`` for the admin view.

    Each row is the email plus the matched application's company and title, so
    the page can show what it matched *to* rather than a bare UUID.
    """
    query = (
        db.query(InboundEmail, Application.company_name, Application.job_title)
        .outerjoin(Application, InboundEmail.matched_application_id == Application.id)
    )
    if matched is True:
        query = query.filter(InboundEmail.matched_application_id.isnot(None))
    elif matched is False:
        query = query.filter(InboundEmail.matched_application_id.is_(None))

    total = query.count()
    rows = query.order_by(InboundEmail.created_at.desc()).offset(skip).limit(limit).all()
    return [(row[0], row[1], row[2]) for row in rows], total
