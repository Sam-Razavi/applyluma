"""Unwrapping manually forwarded mail, and spotting Gmail's forwarding
confirmation (pure functions, no DB or HTTP)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.inbound_email.forwarded import (
    is_gmail_confirmation,
    looks_forwarded,
    parse_gmail_confirmation,
    strip_forward_prefix,
    unwrap_forward,
)

GMAIL_FORWARD = """FYI

---------- Forwarded message ---------
From: Jane Recruiter <jane@acme.com>
Date: Mon, 9 Nov 2026 at 10:12
Subject: Your application for Backend Engineer
To: <sam@gmail.com>


Hi Sam,

Unfortunately we have decided to move forward with other candidates.
"""

GMAIL_FORWARD_SWEDISH = """
---------- Vidarebefordrat meddelande ---------
Från: Svea Solar <rekrytering@sveasolar.com>
Date: mån 9 nov. 2026 kl 10:12
Subject: Din ansökan
To: <sam@gmail.com>


Tyvärr har vi valt att gå vidare med andra kandidater.
"""

OUTLOOK_FORWARD = """

________________________________
From: Talent Team <talent@spotify.com>
Sent: Monday, November 9, 2026 10:12 AM
To: Sam Razavi <sam@outlook.com>
Subject: Interview invitation

We would like to invite you to an interview.
"""

OUTLOOK_FORWARD_SWEDISH = """
________________________________
Från: Klarna Careers <careers@klarna.com>
Skickat: den 9 november 2026 10:12
Till: Sam Razavi <sam@outlook.com>
Ämne: Inbjudan till intervju

Vi vill gärna träffa dig för en intervju.
"""

APPLE_FORWARD = """Begin forwarded message:

From: "Jane Recruiter" <jane@acme.com>
Subject: Next steps
Date: 9 November 2026 at 10:12:00 CET
To: sam@icloud.com

Thanks for applying!
"""


def test_gmail_forward_recovers_the_original_sender_and_message() -> None:
    original = unwrap_forward("Fwd: Your application for Backend Engineer", GMAIL_FORWARD)

    assert original is not None
    assert original.from_address == "jane@acme.com"
    assert original.from_display == "Jane Recruiter"
    assert original.subject == "Your application for Backend Engineer"
    assert original.body.startswith("Hi Sam,")
    assert "Forwarded message" not in original.body


def test_swedish_gmail_forward() -> None:
    original = unwrap_forward("VB: Din ansökan", GMAIL_FORWARD_SWEDISH)

    assert original is not None
    assert original.from_address == "rekrytering@sveasolar.com"
    assert original.subject == "Din ansökan"
    assert original.body.startswith("Tyvärr")


def test_outlook_forward() -> None:
    original = unwrap_forward("FW: Interview invitation", OUTLOOK_FORWARD)

    assert original is not None
    assert original.from_address == "talent@spotify.com"
    assert original.subject == "Interview invitation"
    assert original.body.startswith("We would like")


def test_swedish_outlook_forward() -> None:
    original = unwrap_forward("VB: Inbjudan till intervju", OUTLOOK_FORWARD_SWEDISH)

    assert original is not None
    assert original.from_address == "careers@klarna.com"
    assert original.subject == "Inbjudan till intervju"
    assert original.body.startswith("Vi vill")


def test_apple_mail_forward() -> None:
    original = unwrap_forward("Fwd: Next steps", APPLE_FORWARD)

    assert original is not None
    assert original.from_address == "jane@acme.com"
    assert original.subject == "Next steps"
    assert original.body == "Thanks for applying!"


def test_gmail_html_to_text_bold_headers() -> None:
    body = (
        "---------- Forwarded message ---------\n"
        "*From:* Jane <jane@acme.com>\n"
        "*Subject:* Update\n\n"
        "Body text"
    )
    original = unwrap_forward("Fwd: Update", body)

    assert original is not None
    assert original.from_address == "jane@acme.com"
    assert original.subject == "Update"


def test_ordinary_email_is_left_alone() -> None:
    body = "Hi Sam,\n\nThanks for your application. We will be in touch.\n"
    assert unwrap_forward("Your application", body) is None


def test_quoted_reply_far_down_is_not_a_forward() -> None:
    """A recruiter quoting an older thread is not a forward: the subject says
    nothing and there is no marker, even though a From: line appears."""
    body = "Hi Sam,\n\nSee below.\n\nOn Monday Jane wrote:\nFrom: someone@else.com\n"
    assert unwrap_forward("Re: Interview", body) is None


def test_forward_without_a_readable_sender_is_not_unwrapped() -> None:
    body = "---------- Forwarded message ---------\nFrom: Jane Recruiter\n\nHello"
    assert unwrap_forward("Fwd: Hello", body) is None


def test_forward_subject_prefixes() -> None:
    assert strip_forward_prefix("Fwd: FW: VB: Din ansökan") == "Din ansökan"
    assert strip_forward_prefix("Interview") == "Interview"
    assert looks_forwarded("WG: Bewerbung", "") is True
    assert looks_forwarded("Forward thinking roles", "") is False


GMAIL_CONFIRMATION_SUBJECT = (
    "(#123456789) Gmail Forwarding Confirmation - Receive Mail from sam@gmail.com"
)
GMAIL_CONFIRMATION_BODY = """sam@gmail.com has requested to automatically forward mail to your email
address u-abc@in.applyluma.com.
Confirmation code: 123456789

To allow sam@gmail.com to automatically forward mail to your address,
please click the link below to confirm the request:

https://mail-settings.google.com/mail/vf-%5BANGjdJ_abc%5D-xyz

If you click the link and it appears to be broken, please copy and paste it
into a new browser window.
"""


def test_gmail_confirmation_code_and_link_are_extracted() -> None:
    parsed = parse_gmail_confirmation(GMAIL_CONFIRMATION_SUBJECT, GMAIL_CONFIRMATION_BODY)

    assert parsed is not None
    assert parsed.code == "123456789"
    assert parsed.link == "https://mail-settings.google.com/mail/vf-%5BANGjdJ_abc%5D-xyz"


def test_gmail_confirmation_from_subject_only() -> None:
    parsed = parse_gmail_confirmation(GMAIL_CONFIRMATION_SUBJECT, None)

    assert parsed is not None
    assert parsed.code == "123456789"
    assert parsed.link is None


def test_gmail_confirmation_sender() -> None:
    assert is_gmail_confirmation("Forwarding-Noreply@google.com")
    assert not is_gmail_confirmation("jobs@google.com")
    assert parse_gmail_confirmation("Your application", "Thanks for applying") is None
