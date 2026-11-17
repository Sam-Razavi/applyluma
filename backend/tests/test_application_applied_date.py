"""A card that enters an applied stage gets an applied date, whatever the path."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.crud import application as crud
from app.schemas.application import ApplicationCreate, ApplicationUpdate

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def refresh(self, obj: Any) -> None:
        pass


def card(status: str, applied_date: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), status=status, applied_date=applied_date)


@pytest.fixture(autouse=True)
def no_reference_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crud, "_validate_owned_references", lambda *a, **k: None)


def midnight_today() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


@pytest.mark.parametrize("stage", ["applied", "phone_screen", "interview", "offer"])
def test_moving_a_card_to_an_applied_stage_stamps_today(
    stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = card("wishlist")
    monkeypatch.setattr(crud, "get_application", lambda *a, **k: existing)
    crud.update_application(FakeSession(), existing.id, USER_ID, ApplicationUpdate(status=stage))
    assert existing.applied_date == midnight_today()


def test_an_existing_date_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = datetime(2026, 11, 2, tzinfo=UTC)
    existing = card("wishlist", applied_date=sent)
    monkeypatch.setattr(crud, "get_application", lambda *a, **k: existing)
    crud.update_application(
        FakeSession(), existing.id, USER_ID, ApplicationUpdate(status="applied")
    )
    assert existing.applied_date == sent


def test_wishlist_and_rejected_do_not_get_a_date(monkeypatch: pytest.MonkeyPatch) -> None:
    for status in ("wishlist", "rejected", "withdrawn"):
        existing = card("applied")
        existing.applied_date = None
        monkeypatch.setattr(crud, "get_application", lambda *a, _e=existing, **k: _e)
        crud.update_application(
            FakeSession(), existing.id, USER_ID, ApplicationUpdate(status=status)
        )
        assert existing.applied_date is None, status


def test_an_explicit_clear_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = card("applied", applied_date=datetime(2026, 11, 2, tzinfo=UTC))
    monkeypatch.setattr(crud, "get_application", lambda *a, **k: existing)
    crud.update_application(
        FakeSession(), existing.id, USER_ID, ApplicationUpdate(applied_date=None)
    )
    assert existing.applied_date is None


def test_creating_an_applied_card_without_a_date_stamps_today() -> None:
    created = crud.create_application(
        FakeSession(),
        USER_ID,
        ApplicationCreate(company_name="Acme", job_title="Dev", status="applied"),
    )
    assert created.applied_date == midnight_today()


def test_creating_a_wishlist_card_leaves_the_date_empty() -> None:
    created = crud.create_application(
        FakeSession(),
        USER_ID,
        ApplicationCreate(company_name="Acme", job_title="Dev", status="wishlist"),
    )
    assert created.applied_date is None
