"""Persistence for inbound email ingestion."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Query, Session

from app.models.application import Application
from app.models.inbound_email import SNIPPET_MAX_CHARS, InboundEmail
from app.services.inbound_email.classifier import SUGGEST_THRESHOLD, Classification
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
    classification: Classification | None = None,
) -> InboundEmail:
    # A suggestion is only raised when the email was both matched to an
    # application and confidently classified. Either one alone leaves the row
    # visible in the admin view without ever prompting the user.
    suggest = (
        classification is not None
        and classification.should_suggest
        and match.application_id is not None
    )
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
        classification=classification.kind if classification else None,
        classification_confidence=classification.confidence if classification else 0,
        suggested_status=classification.suggested_status if classification else None,
        evidence=classification.evidence if classification else None,
        suggestion_state="pending" if suggest else "none",
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


def list_pending_suggestions(
    db: Session, user_id: uuid.UUID, limit: int = 20
) -> list[tuple[InboundEmail, str, str]]:
    """Pending suggestions for a user, newest first.

    Each entry is the email plus the matched application's company and title,
    so the prompt can name what it is proposing to change.
    """
    rows = (
        db.query(InboundEmail, Application.company_name, Application.job_title)
        .join(Application, InboundEmail.matched_application_id == Application.id)
        .filter(
            InboundEmail.user_id == user_id,
            InboundEmail.suggestion_state == "pending",
        )
        .order_by(InboundEmail.created_at.desc())
        .limit(limit)
        .all()
    )
    return [(row[0], row[1], row[2]) for row in rows]


def get_pending_suggestion(
    db: Session, suggestion_id: uuid.UUID, user_id: uuid.UUID
) -> InboundEmail | None:
    """Fetch one pending suggestion, scoped to its owner.

    Scoped by user_id so a guessed id from another account resolves to nothing
    rather than to someone else's mail.
    """
    return (
        db.query(InboundEmail)
        .filter(
            InboundEmail.id == suggestion_id,
            InboundEmail.user_id == user_id,
            InboundEmail.suggestion_state == "pending",
        )
        .first()
    )


def forwarding_stats(db: Session, user_id: uuid.UUID) -> tuple[int, datetime | None]:
    """How many emails the user has forwarded, and when the latest arrived."""
    count, latest = (
        db.query(func.count(InboundEmail.id), func.max(InboundEmail.created_at))
        .filter(InboundEmail.user_id == user_id)
        .one()
    )
    return int(count or 0), latest


def latest_from_sender(
    db: Session, user_id: uuid.UUID, from_address: str, since: datetime
) -> InboundEmail | None:
    return (
        db.query(InboundEmail)
        .filter(
            InboundEmail.user_id == user_id,
            InboundEmail.from_address == from_address,
            InboundEmail.created_at >= since,
        )
        .order_by(InboundEmail.created_at.desc())
        .first()
    )


def _unmatched_query(db: Session, user_id: uuid.UUID) -> Query[InboundEmail]:
    # Only mail that clearly says something (a rejection, an interview) is
    # worth asking about; unmatched newsletters and job alerts are not.
    return db.query(InboundEmail).filter(
        InboundEmail.user_id == user_id,
        InboundEmail.matched_application_id.is_(None),
        InboundEmail.suggestion_state == "none",
        InboundEmail.suggested_status.isnot(None),
        InboundEmail.classification_confidence >= SUGGEST_THRESHOLD,
    )


def list_unmatched(
    db: Session, user_id: uuid.UUID, since: datetime, limit: int = 10
) -> list[InboundEmail]:
    """Confidently classified emails that matched no application."""
    return list(
        _unmatched_query(db, user_id)
        .filter(InboundEmail.created_at >= since)
        .order_by(InboundEmail.created_at.desc())
        .limit(limit)
        .all()
    )


def get_unmatched(db: Session, email_id: uuid.UUID, user_id: uuid.UUID) -> InboundEmail | None:
    return _unmatched_query(db, user_id).filter(InboundEmail.id == email_id).first()


def assign_to_application(
    db: Session, row: InboundEmail, application_id: uuid.UUID
) -> InboundEmail:
    """Record the user's own answer to "which application is this about?"."""
    row.matched_application_id = application_id
    row.match_confidence = 100
    row.match_method = "user"
    row.match_reason = "Chosen by the user."
    db.commit()
    db.refresh(row)
    return row


def set_suggestion_state(db: Session, row: InboundEmail, state: str) -> InboundEmail:
    row.suggestion_state = state
    db.commit()
    db.refresh(row)
    return row
