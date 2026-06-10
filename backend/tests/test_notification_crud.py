"""Unit tests for app/crud/notification.py."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crud import notification as crud_notification

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NOTIF_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class _FakeQuery:
    def __init__(self, items=None, count_val=0, update_count=2):
        self._items = items or []
        self._count_val = count_val
        self._update_count = update_count

    def filter(self, *args):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def count(self):
        return self._count_val

    def order_by(self, *args):
        return self

    def offset(self, n):
        return self

    def limit(self, n):
        return self

    def all(self):
        return self._items

    def update(self, *args, **kwargs):
        return self._update_count


class _FakeDb:
    def __init__(self, notifications=None):
        self._notifications = notifications or []
        self.committed = False
        self.added = None

    def query(self, model):
        return _FakeQuery(items=self._notifications, count_val=len(self._notifications))

    def add(self, obj):
        self.added = obj

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_notification_adds_and_commits() -> None:
    db = _FakeDb()

    crud_notification.create(
        db,
        user_id=USER_ID,
        type="tailor_complete",
        title="CV Ready",
        body="Your CV is ready.",
    )

    assert db.added is not None
    assert db.committed


def test_create_notification_with_related_fields() -> None:
    related_id = uuid.uuid4()
    db = _FakeDb()

    crud_notification.create(
        db,
        user_id=USER_ID,
        type="deadline_reminder",
        title="Deadline",
        body="Apply soon.",
        related_id=related_id,
        related_type="application",
    )

    assert db.committed


# ---------------------------------------------------------------------------
# get_for_user
# ---------------------------------------------------------------------------

def test_get_for_user_returns_items_and_counts() -> None:
    notif = SimpleNamespace(id=NOTIF_ID, user_id=USER_ID, is_read=False)
    db = _FakeDb(notifications=[notif])

    items, total, unread = crud_notification.get_for_user(db, USER_ID, skip=0, limit=20)

    assert items == [notif]
    assert total == 1
    assert unread == 1


def test_get_for_user_empty_returns_zeros() -> None:
    db = _FakeDb(notifications=[])

    items, total, unread = crud_notification.get_for_user(db, USER_ID)

    assert items == []
    assert total == 0
    assert unread == 0


# ---------------------------------------------------------------------------
# mark_read
# ---------------------------------------------------------------------------

def test_mark_read_sets_is_read_true() -> None:
    notif = SimpleNamespace(id=NOTIF_ID, user_id=USER_ID, is_read=False)
    db = _FakeDb(notifications=[notif])

    result = crud_notification.mark_read(db, NOTIF_ID, USER_ID)

    assert result is notif
    assert notif.is_read is True
    assert db.committed


def test_mark_read_not_found_returns_none() -> None:
    db = _FakeDb(notifications=[])

    result = crud_notification.mark_read(db, NOTIF_ID, USER_ID)

    assert result is None


# ---------------------------------------------------------------------------
# mark_all_read
# ---------------------------------------------------------------------------

def test_mark_all_read_returns_count() -> None:
    db = _FakeDb()

    count = crud_notification.mark_all_read(db, USER_ID)

    assert count == 2
    assert db.committed
