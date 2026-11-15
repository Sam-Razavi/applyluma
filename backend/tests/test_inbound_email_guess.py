"""Guessing the employer and job title from an email (pure, no DB)."""
from __future__ import annotations

import pytest

from app.services.inbound_email.guess import guess_application


@pytest.mark.parametrize(
    ("domain", "subject", "expected"),
    [
        ("greenhouse.io", "Your application for Backend Engineer at Spotify", ("Spotify", "Backend Engineer")),
        ("klarna.com", "Thank you for applying to Klarna", ("Klarna", "")),
        ("mail.teamtailor.com", "Tack för din ansökan till tjänsten Systemutvecklare hos Hemnet",
         ("Hemnet", "Systemutvecklare")),
        ("linkedin.com", "Your application was sent to Northvolt", ("Northvolt", "")),
        ("tibber.com", "Update on your application for Frontend Developer", ("Tibber", "Frontend Developer")),
        ("gmail.com", "FW: Application received - Data Analyst", ("", "Data Analyst")),
        ("hm.com", "Ansökan mottagen: Junior utvecklare", ("HM", "Junior utvecklare")),
    ],
)
def test_reads_company_and_title_from_common_subjects(
    domain: str, subject: str, expected: tuple[str, str]
) -> None:
    assert guess_application(from_domain=domain, subject=subject) == expected


def test_a_recruiting_system_or_mail_provider_is_never_the_employer() -> None:
    for domain in ("greenhouse.io", "gmail.com", "linkedin.com", "outlook.com"):
        assert guess_application(from_domain=domain, subject="Hello") == ("", "")


def test_nothing_to_go_on_gives_empty_fields_not_an_error() -> None:
    assert guess_application(from_domain=None, subject=None) == ("", "")
    assert guess_application(from_domain="", subject="Bekräftelse på din ansökan") == ("", "")
