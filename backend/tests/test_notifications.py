from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import notifications as notifications_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.services import email_service
from app.tasks import notifications as notification_tasks

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NOTIFICATION_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
APPLICATION_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CREATED_AT = datetime(2026, 5, 14, tzinfo=UTC)


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, email="sam@example.com", is_active=True)


def notification_data(**overrides: Any) -> SimpleNamespace:
    data = {
        "id": NOTIFICATION_ID,
        "user_id": USER_ID,
        "type": "tailor_complete",
        "title": "Your tailored CV is ready",
        "body": "Your AI-tailored CV has finished processing.",
        "related_id": APPLICATION_ID,
        "related_type": "tailor_job",
        "is_read": False,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_list_notifications_returns_paginated_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get_for_user(db, user_id, skip, limit):
        assert user_id == USER_ID
        assert skip == 5
        assert limit == 10
        return [notification_data()], 25, 3

    monkeypatch.setattr(notifications_endpoint.crud_notification, "get_for_user", mock_get_for_user)

    response = await request(
        "GET",
        "/api/v1/notifications?skip=5&limit=10",
        current_user=user(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 25
    assert body["unread_count"] == 3
    assert body["skip"] == 5
    assert body["limit"] == 10
    assert body["items"][0]["id"] == str(NOTIFICATION_ID)


@pytest.mark.asyncio
async def test_mark_read_sets_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_mark_read(db, notification_id, user_id):
        assert notification_id == NOTIFICATION_ID
        assert user_id == USER_ID
        return notification_data(is_read=True)

    monkeypatch.setattr(notifications_endpoint.crud_notification, "mark_read", mock_mark_read)

    response = await request(
        "PATCH",
        f"/api/v1/notifications/{NOTIFICATION_ID}/read",
        current_user=user(),
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True


@pytest.mark.asyncio
async def test_mark_all_read_clears_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        notifications_endpoint.crud_notification,
        "mark_all_read",
        lambda db, user_id: 4,
    )

    response = await request(
        "POST",
        "/api/v1/notifications/mark-all-read",
        current_user=user(),
    )

    assert response.status_code == 200
    assert response.json() == {"updated": 4}


def test_stale_application_task_creates_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    stale_application = SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        company_name="Spotify",
        applied_date=datetime.now(UTC) - timedelta(days=8),
        user=SimpleNamespace(email="sam@example.com"),
    )

    class FakeQuery:
        def filter(self, *args):
            return self

        def all(self):
            return [stale_application]

    class TaskDb:
        def query(self, model):
            return FakeQuery()

        def close(self):
            pass

    created: list[dict[str, Any]] = []

    def mock_create_notification(db, **kwargs):
        created.append(kwargs)
        return notification_data()

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: TaskDb())
    monkeypatch.setattr(
        notification_tasks.notification_service,
        "create_notification",
        mock_create_notification,
    )

    result = notification_tasks.check_stale_applications.run()

    assert result == {"created": 1}
    assert created[0]["type"] == "application_stale"
    assert created[0]["user_id"] == USER_ID
    assert created[0]["related_id"] == APPLICATION_ID
    assert created[0]["send_email"] is True


def test_email_service_is_noop_when_resend_key_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    email_service.send_email("sam@example.com", "Subject", "<p>Body</p>")


# ---------------------------------------------------------------------------
# notify_high_match_jobs task
# ---------------------------------------------------------------------------

def test_notify_high_match_jobs_no_preferences(monkeypatch: pytest.MonkeyPatch) -> None:
    class _TaskDb:
        def close(self):
            pass

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())
    monkeypatch.setattr(
        notification_tasks.crud_alert_preferences,
        "due_for_alert",
        lambda db, now: [],
    )

    result = notification_tasks.notify_high_match_jobs.run()

    assert result == {"created": 0, "logged": 0}


def test_notify_high_match_jobs_creates_notification_and_log(monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid.uuid4()
    score = SimpleNamespace(
        user_id=USER_ID,
        raw_job_posting_id=job_id,
        overall_score=88.0,
        computed_at=datetime.now(UTC),
        job=SimpleNamespace(title="Senior Engineer", company="Spotify"),
    )

    class _FakeQuery:
        def __init__(self, results=None):
            self._results = results or []

        def options(self, *args):
            return self

        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def limit(self, n):
            return self

        def all(self):
            return self._results

    class _TaskDb:
        def __init__(self):
            self.added: list = []
            self.committed = False

        def query(self, model):
            from app.models.job import JobMatchingScore
            if model is JobMatchingScore:
                return _FakeQuery([score])
            return _FakeQuery()

        def get(self, model, pk):
            return SimpleNamespace(email="sam@example.com", is_verified=True)

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            self.committed = True

        def close(self):
            pass

    db = _TaskDb()
    pref = SimpleNamespace(user_id=USER_ID, score_threshold=80.0, last_sent_at=None)

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        notification_tasks.crud_alert_preferences,
        "due_for_alert",
        lambda db, now: [pref],
    )

    created: list[dict] = []

    def _mock_create(db, **kwargs):
        created.append(kwargs)
        return notification_data()

    monkeypatch.setattr(notification_tasks.notification_service, "create_notification", _mock_create)

    result = notification_tasks.notify_high_match_jobs.run()

    assert result["created"] == 1
    assert result["logged"] == 1
    assert len(created) == 1
    assert created[0]["type"] == "high_match_alert"
    assert len(db.added) == 1  # JobAlertSentLog entry
    assert pref.last_sent_at is not None


def test_notify_high_match_jobs_no_matches_updates_last_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeQuery:
        def options(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def limit(self, n): return self
        def all(self): return []

    class _TaskDb:
        def query(self, model): return _FakeQuery()
        def commit(self): pass
        def close(self): pass

    db = _TaskDb()
    pref = SimpleNamespace(user_id=USER_ID, score_threshold=80.0, last_sent_at=None)

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        notification_tasks.crud_alert_preferences,
        "due_for_alert",
        lambda db, now: [pref],
    )

    result = notification_tasks.notify_high_match_jobs.run()

    assert result == {"created": 0, "logged": 0}
    assert pref.last_sent_at is not None  # Updated even with no matches


def test_notify_high_match_jobs_with_last_sent_at_applies_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """pref.last_sent_at not None triggers extra computed_at filter (line 168)."""
    class _FakeQuery:
        def options(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def limit(self, n): return self
        def all(self): return []

    class _TaskDb:
        def query(self, model): return _FakeQuery()
        def commit(self): pass
        def close(self): pass

    db = _TaskDb()
    pref = SimpleNamespace(
        user_id=USER_ID,
        score_threshold=80.0,
        last_sent_at=datetime.now(UTC) - timedelta(hours=2),
    )

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        notification_tasks.crud_alert_preferences,
        "due_for_alert",
        lambda db, now: [pref],
    )

    result = notification_tasks.notify_high_match_jobs.run()
    assert result == {"created": 0, "logged": 0}


def test_notify_high_match_jobs_score_job_is_none_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """Matches found but score.job is None → empty lines list → continue (lines 182-184)."""
    job_id = uuid.uuid4()
    score = SimpleNamespace(
        user_id=USER_ID,
        raw_job_posting_id=job_id,
        overall_score=90.0,
        computed_at=datetime.now(UTC),
        job=None,  # No job reference
    )

    class _FakeQuery:
        def __init__(self, results=None):
            self._results = results or []
        def options(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def limit(self, n): return self
        def all(self): return self._results

    class _TaskDb:
        def __init__(self):
            self.committed = False
        def query(self, model):
            from app.models.job import JobMatchingScore
            if model is JobMatchingScore:
                return _FakeQuery([score])
            return _FakeQuery()
        def commit(self): self.committed = True
        def close(self): pass

    db = _TaskDb()
    pref = SimpleNamespace(user_id=USER_ID, score_threshold=80.0, last_sent_at=None)

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        notification_tasks.crud_alert_preferences,
        "due_for_alert",
        lambda db, now: [pref],
    )

    result = notification_tasks.notify_high_match_jobs.run()
    assert result == {"created": 0, "logged": 0}


# ---------------------------------------------------------------------------
# check_upcoming_deadlines task
# ---------------------------------------------------------------------------

def test_check_upcoming_deadlines_no_applications(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeQuery:
        def filter(self, *args): return self
        def all(self): return []

    class _TaskDb:
        def query(self, model): return _FakeQuery()
        def commit(self): pass
        def close(self): pass

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())

    result = notification_tasks.check_upcoming_deadlines.run()

    assert result == {"created": 0}


def test_check_upcoming_deadlines_creates_reminder_today(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    deadline_naive = (now + timedelta(hours=6)).replace(tzinfo=None)
    application = SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        company_name="Google",
        job_title="Engineer",
        deadline=deadline_naive,
        deadline_reminder_sent=False,
    )

    class _FakeQuery:
        def filter(self, *args): return self
        def all(self): return [application]

    class _TaskDb:
        def __init__(self):
            self.committed = False
        def query(self, model): return _FakeQuery()
        def get(self, model, pk): return SimpleNamespace(email="sam@example.com", is_verified=True)
        def commit(self): self.committed = True
        def close(self): pass

    created: list[dict[str, Any]] = []

    def mock_create_notification(db, **kwargs):
        created.append(kwargs)

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())
    monkeypatch.setattr(notification_tasks.notification_service, "create_notification", mock_create_notification)

    result = notification_tasks.check_upcoming_deadlines.run()

    assert result == {"created": 1}
    assert application.deadline_reminder_sent is True
    assert created[0]["type"] == "deadline_reminder"
    assert created[0]["user_id"] == USER_ID


def test_check_upcoming_deadlines_urgency_tomorrow(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    deadline_aware = now + timedelta(days=1, hours=1)
    application = SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        company_name="Spotify",
        job_title="Dev",
        deadline=deadline_aware,
        deadline_reminder_sent=False,
    )

    class _FakeQuery:
        def filter(self, *args): return self
        def all(self): return [application]

    class _TaskDb:
        def query(self, model): return _FakeQuery()
        def get(self, model, pk): return SimpleNamespace(email="a@b.com", is_verified=False)
        def commit(self): pass
        def close(self): pass

    messages: list[str] = []
    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())
    monkeypatch.setattr(
        notification_tasks.notification_service,
        "create_notification",
        lambda db, **kw: messages.append(kw["body"]),
    )

    result = notification_tasks.check_upcoming_deadlines.run()
    assert result == {"created": 1}
    assert "tomorrow" in messages[0]


def test_check_upcoming_deadlines_urgency_in_n_days(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deadline 2+ days away uses 'in N days' urgency (line 56 in notifications.py)."""
    now = datetime.now(UTC)
    deadline_aware = now + timedelta(days=3, hours=1)
    application = SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        company_name="Netflix",
        job_title="Engineer",
        deadline=deadline_aware,
        deadline_reminder_sent=False,
    )

    class _FakeQuery:
        def filter(self, *args): return self
        def all(self): return [application]

    class _TaskDb:
        def query(self, model): return _FakeQuery()
        def get(self, model, pk): return SimpleNamespace(email="x@y.com", is_verified=True)
        def commit(self): pass
        def close(self): pass

    messages: list[str] = []
    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())
    monkeypatch.setattr(
        notification_tasks.notification_service,
        "create_notification",
        lambda db, **kw: messages.append(kw["body"]),
    )

    result = notification_tasks.check_upcoming_deadlines.run()
    assert result == {"created": 1}
    assert "in" in messages[0] and "days" in messages[0]


# ---------------------------------------------------------------------------
# send_weekly_summary task
# ---------------------------------------------------------------------------

def test_send_weekly_summary_no_users(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeQuery:
        def filter(self, *args): return self
        def all(self): return []
        def group_by(self, *args): return self

    class _TaskDb:
        def query(self, *args): return _FakeQuery()
        def close(self): pass

    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())

    result = notification_tasks.send_weekly_summary.run()

    assert result == {"created": 0}


def test_send_weekly_summary_creates_notification_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    active_user = SimpleNamespace(id=USER_ID, email="sam@example.com", is_active=True)

    class _FakeQuery:
        def __init__(self, result=None):
            self._result = result
        def filter(self, *args): return self
        def group_by(self, *args): return self
        def all(self):
            return [self._result] if self._result else []

    class _TaskDb:
        def query(self, *args):
            from app.models.user import User
            from app.models.application import Application
            if args and args[0] is User:
                return _FakeQuery(active_user)
            return _FakeQuery(("applied", 3))
        def close(self): pass

    created: list[dict[str, Any]] = []
    monkeypatch.setattr(notification_tasks, "SessionLocal", lambda: _TaskDb())
    monkeypatch.setattr(
        notification_tasks.notification_service,
        "create_notification",
        lambda db, **kw: created.append(kw),
    )

    result = notification_tasks.send_weekly_summary.run()

    assert result["created"] == 1
    assert created[0]["type"] == "weekly_summary"
    assert created[0]["user_id"] == USER_ID
