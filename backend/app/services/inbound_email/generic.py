"""Generic HMAC-signed JSON adapter.

The default adapter, and the one to point a Cloudflare Email Worker at — there
you author the POST yourself, so you can emit this shape directly. It is also
what the test suite and `curl` use, which means ingestion can be exercised
end to end before committing to a vendor.

Expected request:

    POST /api/v1/inbound/email
    X-ApplyLuma-Signature: hex(hmac_sha256(secret, raw_body))
    {
      "to": "u-<token>@in.applyluma.com",
      "from": "Careers <careers@spotify.com>",
      "subject": "Your application",
      "text": "...",
      "message_id": "<abc@spotify.com>",
      "date": "2026-08-26T13:00:00Z",
      "headers": {"Message-ID": "<abc@spotify.com>"}
    }

Adding a real vendor means writing a sibling module with its payload shape and
signature scheme, then registering it in ``registry.py``.
"""

from __future__ import annotations

import binascii
import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from app.services.inbound_email.base import InboundParseError, NormalizedEmail

SIGNATURE_HEADER = "x-applyluma-signature"


def _header(headers: Mapping[str, str], name: str) -> str:
    """Case-insensitive header lookup."""
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return ""


def compute_signature(raw_body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def _parse_date(value: str) -> datetime | None:
    """Accept an RFC 2822 ``Date:`` header or an ISO-8601 timestamp."""
    value = value.strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


class GenericAdapter:
    """Vendor-neutral adapter: HMAC-SHA256 over the raw body."""

    name = "generic"

    def verify(self, *, raw_body: bytes, headers: Mapping[str, str], secret: str) -> bool:
        provided = _header(headers, SIGNATURE_HEADER).strip()
        if not provided or not secret:
            return False
        expected = compute_signature(raw_body, secret)
        try:
            # Compare decoded bytes so casing and stray whitespace in the
            # header do not decide authenticity.
            return hmac.compare_digest(
                binascii.unhexlify(provided), binascii.unhexlify(expected)
            )
        except (binascii.Error, ValueError):
            return False

    def parse(self, *, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEmail:
        try:
            payload: Any = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InboundParseError("Body is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise InboundParseError("Body must be a JSON object")

        recipient = str(payload.get("to") or "").strip()
        if not recipient:
            raise InboundParseError("Missing 'to'")

        raw_from = str(payload.get("from") or "").strip()
        display, address = parseaddr(raw_from)
        if not address:
            raise InboundParseError("Missing or unparseable 'from'")

        raw_headers = payload.get("headers")
        parsed_headers: dict[str, str] = {}
        if isinstance(raw_headers, dict):
            parsed_headers = {str(k): str(v) for k, v in raw_headers.items()}

        message_id = str(payload.get("message_id") or "").strip() or _header(
            parsed_headers, "message-id"
        )
        received_at = _parse_date(
            str(payload.get("date") or "") or _header(parsed_headers, "date")
        )

        subject = payload.get("subject")
        text_body = payload.get("text")

        return NormalizedEmail(
            recipient=recipient,
            from_address=address.lower(),
            from_display=display or None,
            subject=str(subject) if subject else None,
            text_body=str(text_body) if text_body else None,
            message_id=message_id or None,
            received_at=received_at,
            headers=parsed_headers,
        )
