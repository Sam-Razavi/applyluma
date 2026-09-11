"""Mailgun adapter and forwarding-address tests.

The adapter is the only place that understands Mailgun's wire format, so these
cover both encodings it can send and the ways a forged request should fail.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.inbound_email.address import build_inbox_address, parse_inbox_token
from app.services.inbound_email.base import InboundParseError
from app.services.inbound_email.mailgun import MailgunAdapter, compute_signature
from app.services.inbound_email.registry import available_vendors, get_adapter

SECRET = "key-mailgun-signing-secret"
TIMESTAMP = "1756300000"
TOKEN = "mailgun-token-value"
BOUNDARY = "----WebKitFormBoundaryTest"

MESSAGE_HEADERS = json.dumps(
    [
        ["From", "Spotify Careers <careers@spotify.com>"],
        ["Subject", "Your application to Spotify"],
        ["Date", "Wed, 26 Aug 2026 10:00:00 +0000"],
        ["Message-Id", "<m-1@spotify.com>"],
    ]
)


def signed_fields(**overrides: str) -> dict[str, str]:
    fields = {
        "timestamp": TIMESTAMP,
        "token": TOKEN,
        "signature": compute_signature(TIMESTAMP, TOKEN, SECRET),
        "recipient": "u-a1b2c3d4e5f60718@in.applyluma.com",
        # The envelope sender is the forwarding user, and must never be what
        # matching keys on.
        "sender": "sam@hotmail.com",
        "from": "Spotify Careers <careers@spotify.com>",
        "subject": "Your application to Spotify",
        "body-plain": "Thanks for applying.\n\nOn Tue, someone wrote:\n> older thread",
        "stripped-text": "Thanks for applying.",
        "Message-Id": "<m-1@spotify.com>",
        "message-headers": MESSAGE_HEADERS,
    }
    fields.update(overrides)
    return fields


def multipart(fields: dict[str, str], *, with_attachment: bool = False) -> bytes:
    chunks = [
        f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields.items()
    ]
    if with_attachment:
        chunks.append(
            f'--{BOUNDARY}\r\nContent-Disposition: form-data; name="attachment-1"; '
            f'filename="cv.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()
            + b"%PDF-1.4 binary bytes\r\n"
        )
    chunks.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(chunks)


MULTIPART_HEADERS = {"content-type": f"multipart/form-data; boundary={BOUNDARY}"}
URLENCODED_HEADERS = {"content-type": "application/x-www-form-urlencoded"}


@pytest.fixture
def adapter() -> MailgunAdapter:
    return MailgunAdapter()


def test_mailgun_is_registered() -> None:
    assert "mailgun" in available_vendors()
    assert get_adapter("mailgun").name == "mailgun"


def test_valid_signature_accepted(adapter: MailgunAdapter) -> None:
    body = multipart(signed_fields())
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret=SECRET) is True


def test_wrong_secret_rejected(adapter: MailgunAdapter) -> None:
    body = multipart(signed_fields())
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret="wrong") is False


def test_empty_secret_rejected(adapter: MailgunAdapter) -> None:
    """An HMAC with an empty key is still computable, so it must fail closed."""
    body = multipart(signed_fields())
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret="") is False


def test_tampered_token_rejected(adapter: MailgunAdapter) -> None:
    body = multipart(signed_fields(token="different-token"))
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret=SECRET) is False


def test_missing_signature_fields_rejected(adapter: MailgunAdapter) -> None:
    fields = signed_fields()
    del fields["signature"]
    body = multipart(fields)
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret=SECRET) is False


def test_non_hex_signature_rejected(adapter: MailgunAdapter) -> None:
    body = multipart(signed_fields(signature="not-hexadecimal"))
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret=SECRET) is False


def test_unparseable_body_rejected(adapter: MailgunAdapter) -> None:
    assert adapter.verify(raw_body=b"junk", headers=MULTIPART_HEADERS, secret=SECRET) is False


def test_parses_header_sender_not_envelope_sender(adapter: MailgunAdapter) -> None:
    """The whole feature breaks if matching keys on the forwarding mailbox."""
    email = adapter.parse(raw_body=multipart(signed_fields()), headers=MULTIPART_HEADERS)
    assert email.from_address == "careers@spotify.com"
    assert email.from_display == "Spotify Careers"


def test_parses_recipient_subject_and_message_id(adapter: MailgunAdapter) -> None:
    email = adapter.parse(raw_body=multipart(signed_fields()), headers=MULTIPART_HEADERS)
    assert email.recipient == "u-a1b2c3d4e5f60718@in.applyluma.com"
    assert email.subject == "Your application to Spotify"
    assert email.message_id == "<m-1@spotify.com>"
    assert email.received_at is not None
    assert email.received_at.year == 2026


def test_prefers_stripped_text_over_full_body(adapter: MailgunAdapter) -> None:
    """Quoted history pollutes company matching, so the stripped body wins."""
    email = adapter.parse(raw_body=multipart(signed_fields()), headers=MULTIPART_HEADERS)
    assert email.text_body == "Thanks for applying."
    assert "older thread" not in (email.text_body or "")


def test_falls_back_to_body_plain_when_not_stripped(adapter: MailgunAdapter) -> None:
    email = adapter.parse(
        raw_body=multipart(signed_fields(**{"stripped-text": ""})), headers=MULTIPART_HEADERS
    )
    assert email.text_body is not None
    assert email.text_body.startswith("Thanks for applying.")


def test_attachments_are_skipped(adapter: MailgunAdapter) -> None:
    body = multipart(signed_fields(), with_attachment=True)
    assert adapter.verify(raw_body=body, headers=MULTIPART_HEADERS, secret=SECRET) is True
    email = adapter.parse(raw_body=body, headers=MULTIPART_HEADERS)
    assert email.from_address == "careers@spotify.com"
    assert "attachment-1" not in email.headers


def test_urlencoded_bodies_are_supported(adapter: MailgunAdapter) -> None:
    """Mailgun drops to urlencoded when a message carries no attachments."""
    body = urlencode(signed_fields()).encode()
    assert adapter.verify(raw_body=body, headers=URLENCODED_HEADERS, secret=SECRET) is True
    email = adapter.parse(raw_body=body, headers=URLENCODED_HEADERS)
    assert email.from_address == "careers@spotify.com"


def test_missing_recipient_raises(adapter: MailgunAdapter) -> None:
    body = multipart(signed_fields(recipient=""))
    with pytest.raises(InboundParseError):
        adapter.parse(raw_body=body, headers=MULTIPART_HEADERS)


def test_missing_from_raises(adapter: MailgunAdapter) -> None:
    fields = signed_fields(**{"from": "", "message-headers": "[]"})
    with pytest.raises(InboundParseError):
        adapter.parse(raw_body=multipart(fields), headers=MULTIPART_HEADERS)


def test_signature_matches_mailgun_documented_scheme() -> None:
    """timestamp + token, signed with the webhook key — not the API key."""
    expected = hmac.new(
        SECRET.encode(), f"{TIMESTAMP}{TOKEN}".encode(), hashlib.sha256
    ).hexdigest()
    assert compute_signature(TIMESTAMP, TOKEN, SECRET) == expected


# --- forwarding address ---------------------------------------------------


def test_build_and_parse_address_round_trip() -> None:
    user = SimpleNamespace(inbox_token="a1b2c3d4e5f60718")
    address = build_inbox_address(user, "in.applyluma.com")
    assert address == "u-a1b2c3d4e5f60718@in.applyluma.com"
    assert parse_inbox_token(address, "in.applyluma.com") == "a1b2c3d4e5f60718"


def test_build_address_returns_none_without_domain() -> None:
    """A half-built address someone might try to use is worse than none."""
    user = SimpleNamespace(inbox_token="a1b2c3d4e5f60718")
    assert build_inbox_address(user, "") is None


def test_build_address_returns_none_without_token() -> None:
    assert build_inbox_address(SimpleNamespace(inbox_token=None), "in.applyluma.com") is None
