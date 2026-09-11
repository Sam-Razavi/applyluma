"""The per-user forwarding address: ``u-{inbox_token}@{INBOUND_EMAIL_DOMAIN}``.

Building and parsing live together so the format is defined exactly once — the
webhook resolves an incoming recipient back to a user with ``parse_inbox_token``
and the admin view shows the same address with ``build_inbox_address``, and the
two must never drift apart.

The token half is a bearer credential: anyone who knows the address can post
mail into that account. Do not surface it outside admin-only responses until
there is a user-facing flow (and a privacy policy) to go with it.
"""

from __future__ import annotations

import re
from typing import Protocol

from app.core.config import settings

# u-<token>@domain, tolerating a +suffix so a user can subaddress without
# breaking resolution.
_RECIPIENT_RE = re.compile(r"^u-([0-9a-zA-Z]{8,64})(\+[^@]*)?$")

ADDRESS_PREFIX = "u-"


class _HasInboxToken(Protocol):
    inbox_token: str | None


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


def build_inbox_address(user: _HasInboxToken, domain: str | None = None) -> str | None:
    """Return the user's full forwarding address.

    None when the user has no token yet, or while ``INBOUND_EMAIL_DOMAIN`` is
    unset — showing ``u-token@`` with no domain would just be a broken address
    someone might try to use.
    """
    token = getattr(user, "inbox_token", None)
    resolved_domain = (domain if domain is not None else settings.INBOUND_EMAIL_DOMAIN).strip()
    if not token or not resolved_domain:
        return None
    return f"{ADDRESS_PREFIX}{token}@{resolved_domain}"
