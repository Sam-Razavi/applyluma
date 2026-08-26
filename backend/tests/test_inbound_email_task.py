"""Celery task tests: dedupe, persistence, and unmatched handling."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import inbound_email as crud_inbound_email
from app.tasks import inbound_email as task_module
from app.tasks.celery_app import celery_app

USER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
APPLICATION_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


class FakeDb:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def rollback(self) -> None:
        pass


def payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "user_id": str(USER_ID),
        "dedupe_key": "key-1",
        "message_id": "<m@spotify.com>",
        "from_address": "careers@spotify.com",
        "from_domain": "spotify.com",
        "subject": "Your application to Spotify",
        "snippet": "Thanks for applying.",
        "received_at": "2026-08-26T10:00:00+00:00",
        "vendor": "generic",
    }
    data.update(overrides)
    return data


@pytest.fixture(autouse=True)
def fake_session(monkeypatch: pytest.MonkeyPatch) -> FakeDb:
    db = FakeDb()
    monkeypatch.setattr(task_module, "SessionLocal", lambda: db)
    return db


def test_task_is_registered_with_celery() -> None:
    assert "app.tasks.inbound_email" in celery_app.conf.include
    assert "app.tasks.inbound_email.process_inbound_email" in celery_app.tasks


def test_matching_email_is_persisted_with_its_match(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, Any] = {}
    monkeypatch.setattr(
        task_module.crud_inbound_email, "exists_for_dedupe_key", lambda db, **kw: False
    )
    monkeypatch.setattr(
        task_module.crud_inbound_email,
        "list_match_candidates",
        lambda db, user_id: [
            crud_inbound_email.MatchCandidate(APPLICATION_ID, "Spotify AB", None)
        ],
    )
    monkeypatch.setattr(
        task_module.crud_inbound_email, "create", lambda db, **kw: created.update(kw)
    )

    result = task_module.process_inbound_email(payload())

    assert result["status"] == "matched"
    assert created["match"].application_id == APPLICATION_ID
    assert created["user_id"] == USER_ID


def test_duplicate_delivery_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vendors retry, so the same message arrives more than once as a matter of course."""
    calls: list[str] = []
    monkeypatch.setattr(
        task_module.crud_inbound_email, "exists_for_dedupe_key", lambda db, **kw: True
    )
    monkeypatch.setattr(
        task_module.crud_inbound_email,
        "create",
        lambda db, **kw: calls.append("created"),
    )

    result = task_module.process_inbound_email(payload())

    assert result == {"status": "duplicate"}
    assert not calls


def test_concurrent_duplicate_loses_the_race_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The unique constraint is the second dedupe layer when two deliveries race."""
    monkeypatch.setattr(
        task_module.crud_inbound_email, "exists_for_dedupe_key", lambda db, **kw: False
    )
    monkeypatch.setattr(task_module.crud_inbound_email, "list_match_candidates", lambda db, u: [])

    def raise_integrity(db: Any, **kwargs: Any) -> None:
        raise IntegrityError("dup", None, Exception("dup"))

    monkeypatch.setattr(task_module.crud_inbound_email, "create", raise_integrity)

    assert task_module.process_inbound_email(payload()) == {"status": "duplicate"}


def test_unmatched_email_is_still_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unmatched row is the signal this whole slice exists to collect."""
    created: dict[str, Any] = {}
    monkeypatch.setattr(
        task_module.crud_inbound_email, "exists_for_dedupe_key", lambda db, **kw: False
    )
    monkeypatch.setattr(task_module.crud_inbound_email, "list_match_candidates", lambda db, u: [])
    monkeypatch.setattr(
        task_module.crud_inbound_email, "create", lambda db, **kw: created.update(kw)
    )

    result = task_module.process_inbound_email(payload())

    assert result["status"] == "unmatched"
    assert created["match"].application_id is None
    assert created["match"].reason


def test_session_is_always_closed(monkeypatch: pytest.MonkeyPatch, fake_session: FakeDb) -> None:
    monkeypatch.setattr(
        task_module.crud_inbound_email, "exists_for_dedupe_key", lambda db, **kw: True
    )
    task_module.process_inbound_email(payload())
    assert fake_session.closed is True


def test_snippet_is_truncated_to_the_column_ceiling() -> None:
    long_text = "word " * 5000
    truncated = crud_inbound_email.truncate_snippet(long_text)
    assert truncated is not None
    assert len(truncated) <= crud_inbound_email.SNIPPET_MAX_CHARS


def test_truncate_snippet_handles_empty_input() -> None:
    assert crud_inbound_email.truncate_snippet(None) is None
    assert crud_inbound_email.truncate_snippet("   ") is None
