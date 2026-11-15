"""Which forwarded emails are about a job application (pure, no database).

The first block is the mail that actually filled a user's inbox in production.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.inbound_email.classifier import classify
from app.services.inbound_email.relevance import is_job_related, looks_bulk


def judge(
    *, sender: str, subject: str, body: str = "", headers: dict[str, str] | None = None, matched: bool = False
) -> bool:
    keep, _ = is_job_related(
        subject=subject,
        snippet=body,
        from_domain=sender.rpartition("@")[2],
        classification=classify(subject, body),
        matched=matched,
        bulk=looks_bulk(headers=headers or {}, from_address=sender, snippet=body),
    )
    return keep


UNSUB = {"List-Unsubscribe": "<https://example.com/u>"}


@pytest.mark.parametrize(
    "mail",
    [
        dict(sender="noreply@glassdoor.com", subject="At 30 years old, with $600,000 in saving an annual...", headers=UNSUB),
        dict(sender="dan@tldrnewsletter.com", subject="Gemini Hydrogen arrives, Resend moves to ...", body="Sponsor: we are hiring engineers."),
        dict(sender="team@cs.resumeworded.com", subject="CS#376: Terrible cooks, the two-skip rule, and how to interview", headers=UNSUB),
        dict(sender="dan@tldrnewsletter.com", subject="Nvidia's CEO search, AWS emulator", headers=UNSUB),
        dict(sender="info@lagenhetsbyte.se", subject="Du har nya bytesförslag att ta ställning till"),
        # A parcel notice from a company the user applied to must not pass as
        # mail about that application.
        dict(sender="shipment-tracking@amazon.se", subject='Skickade: "Amazon Basics HDMI Splitter..." och 1 till', matched=True),
        dict(sender="orders@spotify.com", subject="Your receipt from Spotify", matched=True),
        dict(sender="jobs-noreply@linkedin.com", subject="30 new jobs for Backend Developer", body="Apply now. Unsubscribe"),
        dict(sender="friend@example.com", subject="Dinner on Friday?", body="Are you free?"),
    ],
)
def test_noise_is_not_kept(mail: dict[str, Any]) -> None:
    assert judge(**mail) is False


@pytest.mark.parametrize(
    "mail",
    [
        dict(sender="no-reply@teamtailor.com", subject="Thank you for your application to Klarna", body="We have received your application."),
        dict(sender="rekrytering@kommun.se", subject="Tack för din ansökan", body="Vi har tagit emot din ansökan till tjänsten."),
        dict(sender="anna@klarna.com", subject="Quick question", body="Hi Sam, are you free on Tuesday at 10?", matched=True),
        dict(sender="hr@company.se", subject="Regarding the position", body="Unfortunately we have decided to move forward with other candidates."),
        dict(sender="talent@startup.io", subject="Interview invitation", body="We would like to invite you to an interview."),
        dict(sender="no-reply@greenhouse.io", subject="An update from Acme", body="Please see the message below."),
        # A status mail sent through a mailing system is still kept when it is
        # tied to something the user applied for.
        dict(sender="careers@klarna.com", subject="Your application at Klarna", body="Thanks for applying.", headers=UNSUB, matched=True),
        dict(sender="noreply@varbi.com", subject="Bekräftelse på din ansökan", body="Din ansökan är mottagen.", headers=UNSUB),
    ],
)
def test_job_mail_is_kept(mail: dict[str, Any]) -> None:
    assert judge(**mail) is True


@pytest.mark.parametrize(
    "subject",
    ["Thank you for applying to Acme", "Your application was sent to Acme", "Tack för din ansökan"],
)
def test_an_automated_confirmation_is_kept_though_it_is_bulk_mail(subject: str) -> None:
    keep, _ = is_job_related(
        subject=subject, snippet="We will be in touch. Unsubscribe", from_domain="acme.com",
        classification=None, matched=False, bulk=True,
    )
    assert keep


@pytest.mark.parametrize(
    "subject", ["30 new jobs for Python developer", "5 interview tips from our recruiters", "Jobs you may like"]
)
def test_job_alert_digests_are_still_dropped(subject: str) -> None:
    keep, _ = is_job_related(
        subject=subject, snippet="Apply now. Unsubscribe", from_domain="jobsite.com",
        classification=None, matched=False, bulk=True,
    )
    assert not keep


def test_a_clear_decision_is_kept_even_from_a_bulk_sender() -> None:
    assert judge(
        sender="newsletter@bigcorp.com",
        subject="Your application",
        body="Unfortunately we will not be moving forward with your application.",
        headers=UNSUB,
    )


@pytest.mark.parametrize(
    ("headers", "sender", "body", "expected"),
    [
        ({"List-Unsubscribe": "<mailto:x>"}, "a@b.com", "", True),
        ({"Precedence": "bulk"}, "a@b.com", "", True),
        ({}, "dan@tldrnewsletter.com", "", True),
        ({}, "a@b.com", "Click here to unsubscribe.", True),
        ({}, "a@b.com", "Klicka här för att avregistrera dig.", True),
        ({}, "anna@klarna.com", "Hi Sam, are you free on Tuesday?", False),
    ],
)
def test_bulk_detection(headers: dict[str, str], sender: str, body: str, expected: bool) -> None:
    assert looks_bulk(headers=headers, from_address=sender, snippet=body) is expected
