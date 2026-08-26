"""Match a forwarded email against the recipient's tracked applications.

The webhook has already verified the vendor signature, resolved the recipient
token to a user, and truncated the body to a snippet. Everything this task
receives is already safe to persist.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.crud import inbound_email as crud_inbound_email
from app.db.session import SessionLocal
from app.services.inbound_email.matcher import score_email
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _parse_received_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@celery_app.task(name="app.tasks.inbound_email.process_inbound_email")
def process_inbound_email(payload: dict[str, Any]) -> dict[str, str]:
    """Score one inbound email and persist the result.

    ``payload`` carries only primitives — UUIDs as strings, the timestamp as
    ISO-8601 — because it crosses the Celery broker.
    """
    user_id = uuid.UUID(str(payload["user_id"]))
    dedupe_key = str(payload["dedupe_key"])

    db = SessionLocal()
    try:
        # First of two dedupe layers. This one catches a vendor redelivering
        # the same message; the unique constraint below catches two deliveries
        # racing each other.
        if crud_inbound_email.exists_for_dedupe_key(db, user_id=user_id, dedupe_key=dedupe_key):
            return {"status": "duplicate"}

        subject = str(payload.get("subject") or "")
        snippet = str(payload.get("snippet") or "")
        from_domain = str(payload.get("from_domain") or "")

        candidates = crud_inbound_email.list_match_candidates(db, user_id)
        match = score_email(
            from_domain=from_domain,
            subject=subject,
            snippet=snippet,
            candidates=candidates,
        )

        try:
            crud_inbound_email.create(
                db,
                user_id=user_id,
                dedupe_key=dedupe_key,
                message_id=payload.get("message_id"),
                from_address=str(payload.get("from_address") or ""),
                from_domain=from_domain,
                subject=subject or None,
                snippet=snippet or None,
                received_at=_parse_received_at(payload.get("received_at")),
                vendor=str(payload.get("vendor") or "unknown"),
                match=match,
            )
        except IntegrityError:
            # Concurrent duplicate delivery won the race; its row is equivalent.
            db.rollback()
            return {"status": "duplicate"}

        return {
            "status": "matched" if match.application_id else "unmatched",
            "confidence": str(match.confidence),
            "method": match.method,
        }
    finally:
        db.close()
