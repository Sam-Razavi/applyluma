"""Unit tests for app/services/notification_service.py."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import notification_service

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class _FakeDb:
    pass


def test_create_notification_sends_email_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[dict] = []

    def mock_crud_create(db, **kwargs):
        created.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4(), **kwargs)

    emails_sent: list[tuple] = []

    def mock_send_email(to, subject, body):
        emails_sent.append((to, subject, body))

    def mock_template_email(type_, title, body):
        return f"Subject: {title}", f"<p>{body}</p>"

    monkeypatch.setattr(notification_service.crud_notification, "create", mock_crud_create)
    monkeypatch.setattr(notification_service.email_service, "send_email", mock_send_email)
    monkeypatch.setattr(notification_service.email_service, "template_email", mock_template_email)

    notification_service.create_notification(
        _FakeDb(),
        user_id=USER_ID,
        type="tailor_complete",
        title="CV Ready",
        body="Your CV is ready.",
        send_email=True,
        email="sam@example.com",
    )

    assert len(created) == 1
    assert len(emails_sent) == 1
    assert emails_sent[0][0] == "sam@example.com"


def test_create_notification_skips_email_when_send_email_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        notification_service.crud_notification,
        "create",
        lambda db, **kw: SimpleNamespace(id=uuid.uuid4()),
    )
    emails_sent: list = []
    monkeypatch.setattr(
        notification_service.email_service,
        "send_email",
        lambda *a: emails_sent.append(a),
    )

    notification_service.create_notification(
        _FakeDb(),
        user_id=USER_ID,
        type="test",
        title="Title",
        body="Body",
        send_email=False,
        email="sam@example.com",
    )

    assert len(emails_sent) == 0
