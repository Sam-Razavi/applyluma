"""Unit tests for app/crud/user.py."""
from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import get_password_hash
from app.crud import user as crud_user


class _FakeQuery:
    def __init__(self, user):
        self._user = user

    def filter(self, *args):
        return self

    def first(self):
        return self._user


class _FakeDb:
    def __init__(self, user=None):
        self._user = user
        self.committed = False
        self.refreshed: list = []

    def query(self, model):
        return _FakeQuery(self._user)

    def get(self, model, pk):
        return self._user

    def add(self, obj):
        pass

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)

    def delete(self, obj):
        pass


def _make_user(**overrides):
    base = {
        "id": uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "email": "sam@example.com",
        "hashed_password": get_password_hash("SecurePass1!"),
        "full_name": "Sam Smith",
        "is_verified": False,
        "is_active": True,
        "verification_token": "valid-token-123",
        "password_reset_token": None,
        "password_reset_expires_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# verify_email
# ---------------------------------------------------------------------------

def test_verify_email_sets_verified_flag() -> None:
    user = _make_user()
    db = _FakeDb(user=user)

    result = crud_user.verify_email(db, "valid-token-123")

    assert result is user
    assert user.is_verified is True
    assert user.verification_token is None
    assert db.committed


def test_verify_email_unknown_token_returns_none() -> None:
    db = _FakeDb(user=None)

    result = crud_user.verify_email(db, "unknown-token")

    assert result is None


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------

def test_authenticate_correct_password_returns_user() -> None:
    user = _make_user()
    db = _FakeDb(user=user)

    result = crud_user.authenticate(db, "sam@example.com", "SecurePass1!")

    assert result is user


def test_authenticate_wrong_password_returns_none() -> None:
    user = _make_user()
    db = _FakeDb(user=user)

    result = crud_user.authenticate(db, "sam@example.com", "WrongPassword!")

    assert result is None


def test_authenticate_unknown_email_returns_none() -> None:
    db = _FakeDb(user=None)

    result = crud_user.authenticate(db, "nobody@example.com", "anypassword")

    assert result is None


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

def test_get_by_id_valid_uuid_returns_user() -> None:
    user = _make_user()
    db = _FakeDb(user=user)

    result = crud_user.get_by_id(db, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert result is user


def test_get_by_id_invalid_uuid_returns_none() -> None:
    db = _FakeDb(user=None)

    result = crud_user.get_by_id(db, "not-a-uuid")

    assert result is None


# ---------------------------------------------------------------------------
# consume_password_reset_token
# ---------------------------------------------------------------------------

def test_consume_reset_token_valid_clears_token() -> None:
    user = _make_user(
        password_reset_token="reset-token",
        password_reset_expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db = _FakeDb(user=user)

    result = crud_user.consume_password_reset_token(db, "reset-token", "NewSecure1!")

    assert result is user
    assert user.password_reset_token is None
    assert user.password_reset_expires_at is None
    assert db.committed


def test_consume_reset_token_expired_returns_none() -> None:
    user = _make_user(
        password_reset_token="reset-token",
        password_reset_expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db = _FakeDb(user=user)

    result = crud_user.consume_password_reset_token(db, "reset-token", "NewSecure1!")

    assert result is None


def test_consume_reset_token_not_found_returns_none() -> None:
    db = _FakeDb(user=None)

    result = crud_user.consume_password_reset_token(db, "nonexistent-token", "NewSecure1!")

    assert result is None


def test_consume_reset_token_missing_expiry_returns_none() -> None:
    user = _make_user(
        password_reset_token="reset-token",
        password_reset_expires_at=None,
    )
    db = _FakeDb(user=user)

    result = crud_user.consume_password_reset_token(db, "reset-token", "NewSecure1!")

    assert result is None


def test_consume_reset_token_naive_datetime_treated_as_utc() -> None:
    """Naive datetimes stored in the DB (no tzinfo) are treated as UTC."""
    naive_future = datetime.utcnow() + timedelta(hours=1)  # naive, but 1h in future
    user = _make_user(
        password_reset_token="reset-token",
        password_reset_expires_at=naive_future,
    )
    db = _FakeDb(user=user)

    result = crud_user.consume_password_reset_token(db, "reset-token", "NewSecure1!")

    assert result is user  # Naive datetime is accepted as UTC — reset succeeds


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_user_adds_and_commits() -> None:
    from app.schemas.user import UserCreate
    db = _FakeDb()
    user_in = UserCreate(email="new@example.com", password="SecurePass1!", full_name="New User")

    crud_user.create(db, user_in)

    assert db.committed


# ---------------------------------------------------------------------------
# refresh_verification_token
# ---------------------------------------------------------------------------

def test_refresh_verification_token_sets_new_token() -> None:
    user = _make_user()
    old_token = user.verification_token
    db = _FakeDb(user=user)

    new_token = crud_user.refresh_verification_token(db, user)

    assert new_token
    assert user.verification_token == new_token
    assert user.verification_token != old_token
    assert db.committed


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------

def test_update_profile_changes_full_name() -> None:
    from app.schemas.user import UserUpdate
    user = _make_user()
    db = _FakeDb(user=user)

    crud_user.update_profile(db, user, UserUpdate(full_name="Updated Name"))

    assert user.full_name == "Updated Name"
    assert db.committed


def test_update_profile_no_change_when_none() -> None:
    from app.schemas.user import UserUpdate
    user = _make_user()
    original_name = user.full_name
    db = _FakeDb(user=user)

    crud_user.update_profile(db, user, UserUpdate())

    assert user.full_name == original_name
    assert db.committed


# ---------------------------------------------------------------------------
# update_password
# ---------------------------------------------------------------------------

def test_update_password_changes_hash() -> None:
    user = _make_user()
    original_hash = user.hashed_password
    db = _FakeDb(user=user)

    crud_user.update_password(db, user, "BrandNew1!")

    assert user.hashed_password != original_hash
    assert db.committed


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_user_commits() -> None:
    user = _make_user()
    db = _FakeDb(user=user)

    crud_user.delete(db, user)

    assert db.committed


# ---------------------------------------------------------------------------
# create_password_reset_token
# ---------------------------------------------------------------------------

def test_create_password_reset_token_sets_expiry() -> None:
    user = _make_user()
    db = _FakeDb(user=user)

    token = crud_user.create_password_reset_token(db, user)

    assert token
    assert user.password_reset_token == token
    assert user.password_reset_expires_at is not None
    assert db.committed


def test_update_profile_sets_preferred_template() -> None:
    from app.schemas.user import UserUpdate
    user = _make_user()
    user.preferred_template = None
    db = _FakeDb(user=user)

    crud_user.update_profile(db, user, UserUpdate(preferred_template="modern"))

    assert user.preferred_template == "modern"
    assert db.committed


def test_update_profile_keeps_preferred_template_when_omitted() -> None:
    from app.schemas.user import UserUpdate
    user = _make_user()
    user.preferred_template = "executive"
    db = _FakeDb(user=user)

    crud_user.update_profile(db, user, UserUpdate(full_name="New Name"))

    assert user.preferred_template == "executive"
