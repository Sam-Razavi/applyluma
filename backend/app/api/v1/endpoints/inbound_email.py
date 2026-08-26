"""Inbound email webhook.

An inbound-parse vendor accepts SMTP delivery for the addresses under
``INBOUND_EMAIL_DOMAIN`` and POSTs each parsed message here.

The handler stays deliberately thin: verify, parse, resolve the recipient,
reduce the body to a snippet, enqueue. Scoring touches every application the
user has, and vendors retry on slow responses, so that work belongs in Celery.

Status codes follow one rule: anything we consciously decline to act on answers
2xx, because a 4xx makes the vendor redeliver the same message forever. Only a
failed authenticity check is 4xx, and only missing configuration is 5xx.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.crud import user as crud_user
from app.db.session import SessionLocal
from app.services.inbound_email.base import InboundParseError, NormalizedEmail
from app.services.inbound_email.matcher import normalize_domain
from app.services.inbound_email.registry import UnknownVendorError, get_adapter
from app.tasks.inbound_email import process_inbound_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inbound", tags=["inbound-email"])

# Bounds the body we are willing to buffer and parse.
MAX_BODY_BYTES = 10 * 1024 * 1024

# Longest excerpt handed to the queue. Full bodies are discarded here, before
# anything durable — the broker included — sees them.
SNIPPET_CHARS = 2000

# u-<token>@domain, tolerating a +suffix so users can subaddress.
_RECIPIENT_RE = re.compile(r"^u-([0-9a-zA-Z]{8,64})(\+[^@]*)?$")

# Spelled numerically: starlette renamed the 413 constant, and the old name
# now emits a deprecation warning while the new one is not on every version.
_HTTP_413 = 413

_ACCEPTED = {"status": "accepted"}
_IGNORED = {"status": "ignored"}


def parse_inbox_token(recipient: str, domain: str) -> str | None:
    """Extract the inbox token from a recipient address, or None."""
    address = recipient.strip().lower()
    if "<" in address and ">" in address:
        address = address[address.rfind("<") + 1 : address.rfind(">")]
    if "@" not in address or not domain:
        return None
    local, _, host = address.rpartition("@")
    if host != domain.strip().lower():
        return None
    match = _RECIPIENT_RE.match(local)
    return match.group(1) if match else None


def build_dedupe_key(*, message_id: str | None, email: NormalizedEmail) -> str:
    """Stable per-message key.

    Prefers ``Message-ID``. Mail without one falls back to a fingerprint of the
    parts that identify it, so vendor retries still collapse to one row while a
    genuinely different message stays distinct.
    """
    if message_id:
        return hashlib.sha256(message_id.strip().strip("<>").lower().encode()).hexdigest()
    material = "|".join(
        [
            email.from_address,
            email.subject or "",
            email.received_at.isoformat() if email.received_at else "",
            (email.text_body or "")[:500],
        ]
    )
    return hashlib.sha256(material.encode("utf-8", "replace")).hexdigest()


@router.post("/email")
async def inbound_email_webhook(request: Request) -> Response:
    if not settings.INBOUND_EMAIL_WEBHOOK_SECRET or not settings.INBOUND_EMAIL_DOMAIN:
        # An empty secret makes signature verification forgeable (an HMAC with
        # an empty key is still a valid, guessable computation), so refuse to
        # process anything rather than trust the payload.
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Inbound email is not configured"},
        )

    try:
        adapter = get_adapter(settings.INBOUND_EMAIL_VENDOR)
    except UnknownVendorError:
        logger.exception("inbound_email_unknown_vendor")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Inbound email is not configured"},
        )

    declared_length = request.headers.get("content-length")
    if declared_length and declared_length.isdigit() and int(declared_length) > MAX_BODY_BYTES:
        # Refused before reading, so an oversized post is never buffered.
        return JSONResponse(
            status_code=_HTTP_413,
            content={"detail": "Payload too large"},
        )

    raw_body = await request.body()
    if len(raw_body) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=_HTTP_413,
            content={"detail": "Payload too large"},
        )

    headers = dict(request.headers)
    if not adapter.verify(
        raw_body=raw_body, headers=headers, secret=settings.INBOUND_EMAIL_WEBHOOK_SECRET
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Invalid signature"}
        )

    try:
        email = adapter.parse(raw_body=raw_body, headers=headers)
    except InboundParseError:
        # A malformed payload will not become valid on redelivery.
        logger.warning("inbound_email_unparseable", exc_info=True)
        return JSONResponse(status_code=status.HTTP_200_OK, content=_IGNORED)

    token = parse_inbox_token(email.recipient, settings.INBOUND_EMAIL_DOMAIN)
    if not token:
        return JSONResponse(status_code=status.HTTP_200_OK, content=_IGNORED)

    sender_domain = normalize_domain(email.from_address.rpartition("@")[2])
    if sender_domain and sender_domain == normalize_domain(settings.INBOUND_EMAIL_DOMAIN):
        # Loop guard: never ingest something we appear to have sent ourselves.
        return JSONResponse(status_code=status.HTTP_200_OK, content=_IGNORED)

    db = SessionLocal()
    try:
        user = crud_user.get_by_inbox_token(db, token)
    finally:
        db.close()

    if user is None:
        # Answering 200 keeps the vendor from retrying and does not reveal
        # which tokens exist.
        return JSONResponse(status_code=status.HTTP_200_OK, content=_IGNORED)

    payload: dict[str, Any] = {
        "user_id": str(user.id),
        "dedupe_key": build_dedupe_key(message_id=email.message_id, email=email),
        "message_id": email.message_id,
        "from_address": email.from_address,
        "from_domain": sender_domain,
        "subject": email.subject,
        # Truncated here, before the queue: a Celery message is durable
        # storage, so handing it a full body would keep the body at rest.
        "snippet": (email.text_body or "")[:SNIPPET_CHARS] or None,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "vendor": adapter.name,
    }

    try:
        process_inbound_email.delay(payload)
    except Exception:
        # The message is lost rather than mis-recorded; a 5xx would have the
        # vendor redeliver it, which is what we want.
        logger.exception("inbound_email_enqueue_failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Could not queue message"},
        )

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=_ACCEPTED)
