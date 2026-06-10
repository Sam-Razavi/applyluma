"""Unit tests for app/crud/alert_preferences.py."""
from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import alert_preferences as crud_alert_preferences
from app.schemas.alert_preferences import AlertPreferencesUpdate

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _make_pref(**overrides):
    base = {
        "user_id": USER_ID,
        "enabled": True,
        "score_threshold": 75.0,
        "frequency": "daily",
        "last_sent_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeQuery:
    def __init__(self, result=None, results=None):
        self._result = result
        self._results = results or ([] if result is None else [result])

    def filter(self, *args):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._results


class _FakeDb:
    def __init__(self, existing=None, prefs=None):
        self._existing = existing
        self._prefs = prefs or []
        self.committed = False
        self.added = None

    def query(self, model):
        from app.models.alert_preferences import UserAlertPreferences
        if model is UserAlertPreferences:
            if self._existing is not None:
                return _FakeQuery(result=self._existing, results=[self._existing])
            return _FakeQuery(result=None, results=self._prefs)
        return _FakeQuery()

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass


# ---------------------------------------------------------------------------
# get_or_create_for_user
# ---------------------------------------------------------------------------

def test_get_or_create_returns_existing_preferences() -> None:
    pref = _make_pref()
    db = _FakeDb(existing=pref)

    result = crud_alert_preferences.get_or_create_for_user(db, USER_ID)

    assert result is pref
    assert not db.committed


def test_get_or_create_creates_when_not_found() -> None:
    db = _FakeDb(existing=None)

    result = crud_alert_preferences.get_or_create_for_user(db, USER_ID)

    assert db.committed
    assert db.added is not None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

def test_update_sets_enabled_false() -> None:
    pref = _make_pref()
    db = _FakeDb()

    crud_alert_preferences.update(db, pref, AlertPreferencesUpdate(enabled=False))

    assert pref.enabled is False
    assert db.committed


def test_update_changes_threshold() -> None:
    pref = _make_pref()
    db = _FakeDb()

    crud_alert_preferences.update(db, pref, AlertPreferencesUpdate(score_threshold=90.0))

    assert pref.score_threshold == 90.0
    assert db.committed


# ---------------------------------------------------------------------------
# due_for_alert
# ---------------------------------------------------------------------------

def test_due_for_alert_returns_pref_never_sent() -> None:
    pref = _make_pref(last_sent_at=None)
    db = _FakeDb(prefs=[pref])

    result = crud_alert_preferences.due_for_alert(db)

    assert pref in result


def test_due_for_alert_filters_by_frequency() -> None:
    daily_pref = _make_pref(frequency="daily", last_sent_at=None)
    db = _FakeDb(prefs=[daily_pref])

    result = crud_alert_preferences.due_for_alert(db, frequency="daily")

    assert daily_pref in result


# ---------------------------------------------------------------------------
# _is_due
# ---------------------------------------------------------------------------

def test_is_due_no_last_sent_returns_true() -> None:
    pref = _make_pref(last_sent_at=None)
    assert crud_alert_preferences._is_due(pref, datetime.now(UTC))


def test_is_due_daily_overdue_returns_true() -> None:
    pref = _make_pref(
        frequency="daily",
        last_sent_at=datetime.now(UTC) - timedelta(days=2),
    )
    assert crud_alert_preferences._is_due(pref, datetime.now(UTC))


def test_is_due_weekly_not_yet_due_returns_false() -> None:
    pref = _make_pref(
        frequency="weekly",
        last_sent_at=datetime.now(UTC) - timedelta(hours=12),
    )
    assert not crud_alert_preferences._is_due(pref, datetime.now(UTC))


def test_is_due_weekly_overdue_returns_true() -> None:
    pref = _make_pref(
        frequency="weekly",
        last_sent_at=datetime.now(UTC) - timedelta(days=8),
    )
    assert crud_alert_preferences._is_due(pref, datetime.now(UTC))
