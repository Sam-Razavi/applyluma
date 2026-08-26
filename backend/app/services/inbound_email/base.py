"""Vendor-neutral shapes for inbound email.

Inbound-parse vendors (Postmark, Mailgun, SendGrid, a Cloudflare Email Worker)
each POST a different JSON body and authenticate differently — some sign the
body with HMAC, others rely on a shared secret in a header. Everything past the
adapter works on :class:`NormalizedEmail`, so swapping vendors never reaches the
matcher, the task, or the model.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


class InboundParseError(ValueError):
    """Raised when a payload cannot be understood as an email.

    The endpoint answers these with 200: a malformed body will not become valid
    on retry, and a 4xx would make the vendor redeliver it indefinitely.
    """


@dataclass(frozen=True)
class NormalizedEmail:
    """One inbound message, reduced to the fields ingestion needs.

    ``from_address`` is parsed from the message's ``From:`` header rather than
    the SMTP envelope sender. Forwarding rewrites the envelope to the
    forwarding user's own address, so envelope-based matching sees every
    message as self-sent.
    """

    recipient: str
    from_address: str
    from_display: str | None = None
    subject: str | None = None
    text_body: str | None = None
    message_id: str | None = None
    received_at: datetime | None = None
    headers: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class InboundAdapter(Protocol):
    """Translates one vendor's webhook into a :class:`NormalizedEmail`."""

    name: str

    def verify(self, *, raw_body: bytes, headers: Mapping[str, str], secret: str) -> bool:
        """Authenticate the request. Must be constant-time against ``secret``."""
        ...

    def parse(self, *, raw_body: bytes, headers: Mapping[str, str]) -> NormalizedEmail:
        """Parse the payload, or raise :class:`InboundParseError`."""
        ...
