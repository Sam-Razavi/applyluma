"""The user's own forwarding address (Settings) and the "which application is
this email about?" picker (Applications page)."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import applications as applications_endpoint
from app.api.v1.endpoints import email_forwarding as forwarding_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import UserRole

USER_ID = uuid.UUID("12121212-1212-1212-1212-121212121212")
APPLICATION_ID = uuid.UUID("34343434-3434-3434-3434-343434343434")
EMAIL_ID = uuid.UUID("56565656-5656-5656-5656-565656565656")
NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)


def make_user(role: UserRole = UserRole.user) -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, email="sam@example.com", role=role, inbox_token="tok123")


@pytest.fixture(autouse=True)
def clear_overrides(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    monkeypatch.setattr(settings, "INBOUND_EMAIL_WEBHOOK_SECRET", "secret")
    monkeypatch.setattr(settings, "INBOUND_EMAIL_DOMAIN", "in.applyluma.com")
    monkeypatch.setattr(settings, "INBOUND_EMAIL_USER_ENABLED", False)
    yield
    app.dependency_overrides.clear()


def as_user(user: SimpleNamespace) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def call(method: str, path: str, json: dict[str, Any] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.request(method, path, json=json)


def install_forwarding(
    monkeypatch: pytest.MonkeyPatch, confirmation: SimpleNamespace | None = None
) -> dict[str, Any]:
    state: dict[str, Any] = {"rotated": False}

    def rotate(db: Any, user: SimpleNamespace) -> str:
        state["rotated"] = True
        user.inbox_token = "newtok456"
        return user.inbox_token

    monkeypatch.setattr(
        forwarding_endpoint,
        "crud_user",
        SimpleNamespace(ensure_inbox_token=lambda db, u: u.inbox_token, rotate_inbox_token=rotate),
    )
    monkeypatch.setattr(
        forwarding_endpoint,
        "crud_inbound_email",
        SimpleNamespace(
            forwarding_stats=lambda db, uid: (3, NOW),
            latest_from_sender=lambda db, uid, sender, since: confirmation,
        ),
    )
    return state


@pytest.mark.asyncio
async def test_hidden_from_regular_users_until_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    install_forwarding(monkeypatch)
    as_user(make_user())

    response = await call("GET", "/api/v1/email-forwarding")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "address": None,
        "emails_received": 0,
        "last_received_at": None,
        "gmail_confirmation": None,
    }


@pytest.mark.asyncio
async def test_admins_see_their_address_before_it_is_opened_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_forwarding(monkeypatch)
    as_user(make_user(UserRole.admin))

    data = (await call("GET", "/api/v1/email-forwarding")).json()

    assert data["enabled"] is True
    assert data["address"] == "u-tok123@in.applyluma.com"
    assert data["emails_received"] == 3


@pytest.mark.asyncio
async def test_everyone_sees_it_once_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "INBOUND_EMAIL_USER_ENABLED", True)
    install_forwarding(monkeypatch)
    as_user(make_user())

    data = (await call("GET", "/api/v1/email-forwarding")).json()

    assert data["enabled"] is True
    assert data["address"] == "u-tok123@in.applyluma.com"


@pytest.mark.asyncio
async def test_never_shown_while_inbound_email_is_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "INBOUND_EMAIL_WEBHOOK_SECRET", "")
    install_forwarding(monkeypatch)
    as_user(make_user(UserRole.admin))

    data = (await call("GET", "/api/v1/email-forwarding")).json()

    assert data["enabled"] is False


@pytest.mark.asyncio
async def test_gmail_confirmation_code_is_shown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gmail emails its confirmation code to the forwarding address, which the
    user cannot read, so Settings shows it."""
    confirmation = SimpleNamespace(
        subject="(#987654321) Gmail Forwarding Confirmation - Receive Mail from sam@gmail.com",
        snippet="Confirmation code: 987654321\nhttps://mail-settings.google.com/mail/vf-abc",
        created_at=NOW,
    )
    install_forwarding(monkeypatch, confirmation=confirmation)
    as_user(make_user(UserRole.admin))

    data = (await call("GET", "/api/v1/email-forwarding")).json()

    assert data["gmail_confirmation"]["code"] == "987654321"
    assert data["gmail_confirmation"]["link"] == "https://mail-settings.google.com/mail/vf-abc"


@pytest.mark.asyncio
async def test_rotate_replaces_the_address(monkeypatch: pytest.MonkeyPatch) -> None:
    state = install_forwarding(monkeypatch)
    as_user(make_user(UserRole.admin))

    response = await call("POST", "/api/v1/email-forwarding/rotate")

    assert response.status_code == 200
    assert state["rotated"] is True
    assert response.json()["address"] == "u-newtok456@in.applyluma.com"


@pytest.mark.asyncio
async def test_rotate_is_unavailable_when_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    state = install_forwarding(monkeypatch)
    as_user(make_user())

    response = await call("POST", "/api/v1/email-forwarding/rotate")

    assert response.status_code == 404
    assert state["rotated"] is False


# --- Unmatched emails ----------------------------------------------------------


def unmatched_row(**overrides: Any) -> SimpleNamespace:
    data = {
        "id": EMAIL_ID,
        "from_address": "noreply@teamtailor.com",
        "subject": "Your application",
        "classification": "rejection",
        "suggested_status": "rejected",
        "evidence": "Unfortunately we have decided to move forward with other candidates.",
        "received_at": None,
        "created_at": NOW,
        "suggestion_state": "none",
        "matched_application_id": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def application_obj(status: str = "rejected") -> SimpleNamespace:
    return SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        job_description_id=None,
        cv_id=None,
        company_name="Acme",
        job_title="Engineer",
        job_url=None,
        status=status,
        applied_date=None,
        interview_date=None,
        deadline=None,
        source=None,
        salary_min=None,
        salary_max=None,
        location=None,
        remote_type=None,
        priority=1,
        notes=None,
        created_at="2026-11-01T00:00:00Z",
        updated_at="2026-11-01T00:00:00Z",
    )


def install_unmatched(
    monkeypatch: pytest.MonkeyPatch,
    *,
    row: SimpleNamespace | None,
    application: SimpleNamespace | None,
) -> dict[str, Any]:
    state: dict[str, Any] = {"assigned": None, "state_set": None, "updated": None}

    def assign(db: Any, target: SimpleNamespace, application_id: uuid.UUID) -> SimpleNamespace:
        state["assigned"] = application_id
        target.matched_application_id = application_id
        return target

    def set_state(db: Any, target: SimpleNamespace, value: str) -> SimpleNamespace:
        state["state_set"] = value
        return target

    monkeypatch.setattr(
        applications_endpoint,
        "crud_inbound_email",
        SimpleNamespace(
            list_unmatched=lambda db, uid, since: [row] if row else [],
            get_unmatched=lambda db, eid, uid: row if row and eid == row.id else None,
            assign_to_application=assign,
            set_suggestion_state=set_state,
        ),
    )

    def update(db: Any, app_id: uuid.UUID, user_id: uuid.UUID, payload: Any) -> Any:
        state["updated"] = (app_id, payload.status)
        return application

    monkeypatch.setattr(
        applications_endpoint,
        "crud_application",
        SimpleNamespace(
            get_application=lambda db, aid, uid: application if aid == APPLICATION_ID else None,
            update_application=update,
        ),
    )
    return state


@pytest.mark.asyncio
async def test_lists_unmatched_emails_with_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    install_unmatched(monkeypatch, row=unmatched_row(), application=None)
    as_user(make_user())

    response = await call("GET", "/api/v1/applications/email-unmatched")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["suggested_status"] == "rejected"
    assert items[0]["evidence"].startswith("Unfortunately")


@pytest.mark.asyncio
async def test_assigning_applies_the_status_through_the_normal_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = install_unmatched(monkeypatch, row=unmatched_row(), application=application_obj())
    as_user(make_user())

    response = await call(
        "POST",
        f"/api/v1/applications/email-unmatched/{EMAIL_ID}/assign",
        json={"application_id": str(APPLICATION_ID)},
    )

    assert response.status_code == 200
    assert state["assigned"] == APPLICATION_ID
    assert state["updated"] == (APPLICATION_ID, "rejected")
    assert state["state_set"] == "accepted"


@pytest.mark.asyncio
async def test_assigning_to_someone_elses_application_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = install_unmatched(monkeypatch, row=unmatched_row(), application=application_obj())
    as_user(make_user())

    response = await call(
        "POST",
        f"/api/v1/applications/email-unmatched/{EMAIL_ID}/assign",
        json={"application_id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    assert state["assigned"] is None
    assert state["updated"] is None


@pytest.mark.asyncio
async def test_dismissing_an_unmatched_email(monkeypatch: pytest.MonkeyPatch) -> None:
    state = install_unmatched(monkeypatch, row=unmatched_row(), application=None)
    as_user(make_user())

    response = await call("POST", f"/api/v1/applications/email-unmatched/{EMAIL_ID}/dismiss")

    assert response.status_code == 204
    assert state["state_set"] == "dismissed"


@pytest.mark.asyncio
async def test_unknown_unmatched_email_is_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    install_unmatched(monkeypatch, row=None, application=None)
    as_user(make_user())

    response = await call("POST", f"/api/v1/applications/email-unmatched/{EMAIL_ID}/dismiss")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unmatched_path_is_not_shadowed_by_the_id_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_unmatched(monkeypatch, row=None, application=None)
    as_user(make_user())

    response = await call("GET", "/api/v1/applications/email-unmatched")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_gmail_confirmation_is_hidden_once_later_mail_arrives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mail arriving after the confirmation means forwarding works; the
    "confirm forwarding" prompt would only be noise."""
    from datetime import timedelta

    confirmation = SimpleNamespace(
        subject="(#987654321) Gmail Forwarding Confirmation",
        snippet="Confirmation code: 987654321",
        created_at=NOW - timedelta(hours=1),
    )
    install_forwarding(monkeypatch, confirmation=confirmation)  # latest email is NOW
    as_user(make_user(UserRole.admin))

    data = (await call("GET", "/api/v1/email-forwarding")).json()

    assert data["gmail_confirmation"] is None


# --- The user's inbox ----------------------------------------------------------


def inbox_row(**overrides: Any) -> SimpleNamespace:
    data = {
        "id": EMAIL_ID,
        "from_address": "talent@supportwave.com",
        "subject": "Application unsuccessful",
        "snippet": "We regret to inform you...",
        "received_at": None,
        "created_at": NOW,
        "classification": "rejection",
        "suggested_status": "rejected",
        "evidence": "We regret to inform you",
        "suggestion_state": "pending",
        "matched_application_id": APPLICATION_ID,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def install_inbox(monkeypatch: pytest.MonkeyPatch, rows: list[Any]) -> dict[str, Any]:
    state: dict[str, Any] = {"listed": None, "deleted": None}

    def list_for_user(db: Any, user_id: uuid.UUID, **kw: Any) -> tuple[list[Any], int]:
        state["listed"] = kw
        return rows, len(rows)

    def delete_for_user(db: Any, email_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        state["deleted"] = (email_id, user_id)
        return email_id == EMAIL_ID

    monkeypatch.setattr(
        forwarding_endpoint,
        "crud_inbound_email",
        SimpleNamespace(list_for_user=list_for_user, delete_for_user=delete_for_user),
    )
    return state


@pytest.mark.asyncio
async def test_inbox_lists_emails_with_what_they_matched(monkeypatch: pytest.MonkeyPatch) -> None:
    state = install_inbox(monkeypatch, [(inbox_row(), "supportwave", "IT Support Specialist")])
    as_user(make_user())

    response = await call("GET", "/api/v1/email-forwarding/messages?matched=true&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["company_name"] == "supportwave"
    assert item["classification"] == "rejection"
    assert item["suggestion_state"] == "pending"
    # Gmail's confirmation is setup plumbing and stays out of the inbox.
    assert state["listed"]["exclude_sender"] == "forwarding-noreply@google.com"
    assert state["listed"]["matched"] is True
    assert state["listed"]["limit"] == 10


@pytest.mark.asyncio
async def test_inbox_delete_is_scoped_to_the_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    state = install_inbox(monkeypatch, [])
    as_user(make_user())

    ok = await call("DELETE", f"/api/v1/email-forwarding/messages/{EMAIL_ID}")
    missing = await call("DELETE", f"/api/v1/email-forwarding/messages/{uuid.uuid4()}")

    assert ok.status_code == 204
    assert state["deleted"][1] == USER_ID
    assert missing.status_code == 404
