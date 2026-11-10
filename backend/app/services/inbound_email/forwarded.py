"""Recover the original sender from a manually forwarded email.

Pressing "Forward" makes the user the ``From:`` of the message we receive, so
the matcher sees every hand-forwarded email as self-sent and nothing matches.
The original sender is still in the body, in the header block every mail
client writes above the forwarded message:

    ---------- Forwarded message ---------            (Gmail)
    ---------- Vidarebefordrat meddelande ---------   (Gmail, Swedish)
    Begin forwarded message:                          (Apple Mail)
    ________________________________                  (Outlook)
    From: Jane Recruiter <jane@acme.com>              (Från: in Swedish)
    Subject: Your application                         (Ämne: in Swedish)

Pure functions, no I/O. A body without such a block is left alone: a recruiter
quoting an internal thread is not a forward, so the block must sit near the
top of the message and the subject or a marker line must say it is a forward.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from email.utils import parseaddr

# Fwd:, Fw:, VB: (Swedish "vidarebefordrat"), WG: (German), TR: (French).
_FORWARD_SUBJECT = re.compile(r"^\s*(?:(?:fwd?|vb|wg|tr|enc)\s*:\s*)+", re.IGNORECASE)

_MARKER = re.compile(
    r"^[\s>*_-]*(?:"
    r"-{2,}\s*(?:forwarded message|original message|vidarebefordrat meddelande"
    r"|ursprungligt meddelande)\s*-{2,}"
    r"|begin forwarded message:?"
    r"|_{10,}"
    r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# "From:", "*From:*" (Gmail's HTML-to-text), "Från:" (Swedish), "Von:", "Fra:".
_HEADER_LINE = re.compile(
    r"^[ \t>]*\**(from|från|fran|von|fra|de|subject|ämne|amne|betreff|emne|objet)\**\s*:\**[ \t]*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)
_EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+")

_FROM_KEYS = {"from", "från", "fran", "von", "fra", "de"}
_SUBJECT_KEYS = {"subject", "ämne", "amne", "betreff", "emne", "objet"}

# The header block of a forward sits at the top. Anything further down is a
# quoted thread, whose sender says nothing about who wrote to the user.
_SEARCH_WINDOW = 3000


@dataclass(frozen=True)
class ForwardedOriginal:
    from_address: str
    from_display: str | None
    subject: str | None
    # The forwarded message itself, without the forward header block.
    body: str


def strip_forward_prefix(subject: str | None) -> str | None:
    if subject is None:
        return None
    return _FORWARD_SUBJECT.sub("", subject).strip() or None


def looks_forwarded(subject: str | None, body: str | None) -> bool:
    if subject and _FORWARD_SUBJECT.match(subject):
        return True
    return bool(body and _MARKER.search(body[:_SEARCH_WINDOW]))


def unwrap_forward(subject: str | None, body: str | None) -> ForwardedOriginal | None:
    """The original message inside a manual forward, or None if it is not one."""
    if not body or not looks_forwarded(subject, body):
        return None

    window = body[:_SEARCH_WINDOW]
    marker = _MARKER.search(window)
    start = marker.end() if marker else 0

    from_address: str | None = None
    from_display: str | None = None
    original_subject: str | None = None
    block_end = start
    for line in _HEADER_LINE.finditer(window, start):
        key = line.group(1).lower()
        value = line.group(2).strip().strip("*").strip()
        if key in _FROM_KEYS and from_address is None:
            from_display, from_address = _parse_sender(value)
            if from_address is None:
                return None
        elif key in _SUBJECT_KEYS and original_subject is None and from_address is not None:
            original_subject = value or None
        else:
            continue
        block_end = line.end()
        if from_address and original_subject:
            break

    if from_address is None:
        return None

    remainder = body[block_end:]
    # Skip the rest of the header block (Date:/To:/Sent:) up to the blank line.
    blank = re.search(r"\n[ \t]*\n", remainder)
    if blank and blank.start() < 600:
        remainder = remainder[blank.end():]

    return ForwardedOriginal(
        from_address=from_address,
        from_display=from_display,
        subject=strip_forward_prefix(original_subject) or strip_forward_prefix(subject),
        body=remainder.strip(),
    )


def _parse_sender(value: str) -> tuple[str | None, str | None]:
    # Outlook writes "Jane Doe <jane@acme.com>"; Gmail's text part sometimes
    # wraps the address in mailto-style brackets twice, so fall back to a scan.
    display, address = parseaddr(value)
    if not address or "@" not in address:
        found = _EMAIL.search(value)
        if not found:
            return None, None
        address = found.group(0)
        display = value[: found.start()].strip(" <\"'") or display
    return (display.strip() or None) if display else None, address.lower()


# --- Gmail forwarding confirmation -------------------------------------------
#
# Gmail refuses to auto-forward to a new address until the user confirms a code
# that Gmail emails *to that address*, so the confirmation lands here, where the
# user cannot read it. We spot it and show the code and link in Settings.

GMAIL_FORWARDING_SENDER = "forwarding-noreply@google.com"
_CODE = re.compile(r"(?:\(#|confirmation code:?\s*|bekräftelsekod:?\s*)(\d{6,12})", re.IGNORECASE)
_LINK = re.compile(r"https://(?:mail-settings\.google\.com|mail\.google\.com|isolated\.mail\.google\.com)/mail/[^\s<>\"')\]]+")


@dataclass(frozen=True)
class GmailConfirmation:
    code: str | None
    link: str | None


def is_gmail_confirmation(from_address: str | None) -> bool:
    return (from_address or "").strip().lower() == GMAIL_FORWARDING_SENDER


def parse_gmail_confirmation(subject: str | None, body: str | None) -> GmailConfirmation | None:
    text = f"{subject or ''}\n{body or ''}"
    code = _CODE.search(text)
    link = _LINK.search(body or "")
    if not code and not link:
        return None
    return GmailConfirmation(
        code=code.group(1) if code else None,
        link=link.group(0) if link else None,
    )
