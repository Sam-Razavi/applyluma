"""Tests for HTML-escaping in transactional emails.

template_email/send_welcome_verification_email interpolate user-controlled
text (notification body/title, full_name) directly into raw HTML f-strings
with no templating-engine autoescape — these tests guard against that
regressing into an HTML/script injection vector in real emails.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import email_service

_PAYLOAD = '<img src=x onerror=alert(1)>'
_ESCAPED = '&lt;img src=x onerror=alert(1)&gt;'


def test_escape_html_escapes_angle_brackets_and_ampersand() -> None:
    assert email_service.escape_html("<b>Tom & Jerry</b>") == "&lt;b&gt;Tom &amp; Jerry&lt;/b&gt;"


def test_escape_html_leaves_plain_text_untouched() -> None:
    assert email_service.escape_html("Backend Engineer at Acme") == "Backend Engineer at Acme"


def test_template_email_escapes_body_for_known_type() -> None:
    _subject, html_body = email_service.template_email("deadline_reminder", "ignored", _PAYLOAD)
    assert _PAYLOAD not in html_body
    assert _ESCAPED in html_body


def test_template_email_escapes_body_for_unknown_type_fallback() -> None:
    _subject, html_body = email_service.template_email("not_a_real_type", "Title", _PAYLOAD)
    assert _PAYLOAD not in html_body
    assert _ESCAPED in html_body


def test_send_welcome_verification_email_escapes_full_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # send_welcome_verification_email greets by first name only
    # (full_name.split()[0]) — use a space-free payload so it survives that.
    name_payload = "<script>alert(1)</script>"
    escaped_payload = "&lt;script&gt;alert(1)&lt;/script&gt;"
    captured: dict[str, str] = {}

    def fake_send_email(to_email: str, subject: str, html_body: str) -> None:
        captured["html_body"] = html_body

    monkeypatch.setattr(email_service, "send_email", fake_send_email)

    email_service.send_welcome_verification_email(
        "user@example.com", "tok123", full_name=name_payload
    )

    assert name_payload not in captured["html_body"]
    assert escaped_payload in captured["html_body"]


def test_send_welcome_verification_email_handles_empty_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        email_service, "send_email", lambda to, subj, body: captured.update(html_body=body)
    )

    email_service.send_welcome_verification_email("user@example.com", "tok123", full_name="")

    assert "Welcome to ApplyLuma!" in captured["html_body"]
