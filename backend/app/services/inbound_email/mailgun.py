"""Mailgun inbound Routes adapter.

Mailgun posts a form body (``multipart/form-data``, or urlencoded when there
are no attachments) rather than JSON, and carries its signature *inside* that
body instead of in a header — which is why ``InboundAdapter.verify`` takes the
raw bytes.

Signature scheme (Mailgun's documented one):

    signature == hexdigest(HMAC_SHA256(key=signing_key, msg=timestamp + token))

The key is Mailgun's **HTTP webhook signing key** (Sending → Webhooks in the
dashboard), which is not the same value as the sending API key. It goes in
``INBOUND_EMAIL_WEBHOOK_SECRET``.

No timestamp-freshness check is applied on purpose. Mailgun retries a failing
webhook on an escalating schedule for hours, and a narrow window would start
rejecting those legitimate retries. Replay is already harmless: a replayed
message carries the same ``Message-Id``, so the dedupe key collapses it onto
the row that already exists.

Form fields used: ``recipient`` (envelope recipient — the address the token is
parsed from), ``from`` (the original From header, which is what matching needs),
``subject``, ``body-plain`` / ``stripped-text``, ``Message-Id``, and
``message-headers``. Attachment parts are skipped without being read.
"""

from __future__ import annotations

import binascii
import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from email.parser import BytesParser
from email.policy import default as default_policy
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qs

from app.services.inbound_email.base import InboundParseError, NormalizedEmail


def _header(headers: Mapping[str, str], name: str) -> str:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


def parse_form(raw_body: bytes, content_type: str) -> dict[str, str]:
    """Decode a urlencoded or multipart form body into a flat mapping.

    Attachment parts (anything with a filename) are skipped rather than
    decoded — we never store attachments, and a large one should not cost us
    the memory to read it.
    """
    ctype = (content_type or "").lower()

    if "multipart/form-data" in ctype:
        # Re-attach the Content-Type header so the parser can find the
        # boundary, then let the stdlib do the MIME work.
        prologue = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
        message = BytesParser(policy=default_policy).parsebytes(prologue + raw_body)
        if not message.is_multipart():
            raise InboundParseError("Body is not a valid multipart form")
        fields: dict[str, str] = {}
        for part in message.iter_parts():
            if part.get_filename():
                continue
            name = part.get_param("name", header="content-disposition")
            if name is None:
                continue
            payload = part.get_payload(decode=True)
            if not isinstance(payload, bytes):
                continue
            fields[str(name)] = payload.decode("utf-8", "replace")
        return fields

    # Mailgun falls back to urlencoded when the message has no attachments.
    decoded = raw_body.decode("utf-8", "replace")
    return {key: values[0] for key, values in parse_qs(decoded, keep_blank_values=True).items()}


def compute_signature(timestamp: str, token: str, signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        f"{timestamp}{token}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _headers_from_field(value: str) -> dict[str, str]:
    """Decode Mailgun's ``message-headers`` JSON array of ``[name, value]``."""
    if not value.strip():
        return {}
    try:
        decoded: Any = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, list):
        return {}
    out: dict[str, str] = {}
    for entry in decoded:
        if isinstance(entry, list) and len(entry) == 2:
            out[str(entry[0])] = str(entry[1])
    return out


class MailgunAdapter:
    """Mailgun Routes: form-encoded body, signature carried in the body."""

    name = "mailgun"

    def verify(self, *, raw_body: bytes, headers: Mapping[str, str], secret: str) -> bool:
        if not secret:
            return False
        try:
            fields = parse_form(raw_body, _header(headers, "content-type"))
        except InboundParseError:
            return False

        # Whitespace-stripped: a stray newline from the multipart encoding
        # would otherwise change the signed string and fail every message.
        timestamp = fields.get("timestamp", "").strip()
        token = fields.get("token", "").strip()
        provided = fields.get("signature", "").strip()
        if not timestamp or not token or not provided:
            return False

        expected = compute_signature(timestamp, token, secret)
        try:
            return hmac.compare_digest(
                binascii.unhexlify(provided), binascii.unhexlify(expected)
            )
        except (binascii.Error, ValueError):
            return False

    def parse(self, *, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEmail:
        fields = parse_form(raw_body, _header(headers, "content-type"))

        # Envelope recipient, not the To header: a user who BCCs their
        # forwarding address never appears in To at all.
        recipient = fields.get("recipient", "").strip()
        if not recipient:
            raise InboundParseError("Missing 'recipient'")

        message_headers = _headers_from_field(fields.get("message-headers", ""))

        raw_from = fields.get("from", "").strip() or _header(message_headers, "from")
        display, address = parseaddr(raw_from)
        if not address:
            raise InboundParseError("Missing or unparseable 'from'")

        message_id = (
            fields.get("Message-Id", "").strip()
            or fields.get("message-id", "").strip()
            or _header(message_headers, "message-id")
        )
        received_at = _parse_date(_header(message_headers, "date"))
        # stripped-text drops the quoted history, so it matches better; the
        # full body is the fallback when Mailgun could not strip it.
        text_body = fields.get("stripped-text", "").strip() or fields.get("body-plain", "")
        subject = fields.get("subject", "").strip() or _header(message_headers, "subject")

        return NormalizedEmail(
            recipient=recipient,
            from_address=address.lower(),
            from_display=display or None,
            subject=subject or None,
            text_body=text_body or None,
            message_id=message_id or None,
            received_at=received_at,
            headers=message_headers,
        )
