"""Suggestion endpoint tests.

The endpoints move a user's data, so ownership scoping and the "nothing
applies without a click" contract carry the weight here.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import applications as applications_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
APPLICATION_ID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
SUGGESTION_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=USER_ID, email="sam@example.com"
    )
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    yield
    app.dependency_overrides.clear()


def suggestion_row(**overrides: Any) -> SimpleNamespace:
    data = {
        "id": SUGGESTION_ID,
        "matched_application_id": APPLICATION_ID,
        "suggested_status": "rejected",
        "classification": "rejection",
        "classification_confidence": 90,
        "evidence": "Tyvärr har du inte gått vidare.",
        "from_address": "hr@sveasolar.com",
        "subject": "Din ansökan",
        "received_at": None,
        "suggestion_state": "pending",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    rows: list[tuple[SimpleNamespace, str, str]] | None = None,
    row: SimpleNamespace | None = None,
    application: SimpleNamespace | None = None,
    updated: SimpleNamespace | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {"state_set": None, "update_called_with": None}

    def set_state(db: Any, target: SimpleNamespace, value: str) -> SimpleNamespace:
        state["state_set"] = value
        target.suggestion_state = value
        return target

    monkeypatch.setattr(
        applications_endpoint,
        "crud_inbound_email",
        SimpleNamespace(
            list_pending_suggestions=lambda db, user_id: rows or [],
            get_pending_suggestion=lambda db, sid, uid: row if row and sid == row.id else None,
            set_suggestion_state=set_state,
        ),
    )

    def update_application(db: Any, app_id: Any, user_id: Any, payload: Any) -> Any:
        state["update_called_with"] = (app_id, user_id, payload.status)
        return updated

    monkeypatch.setattr(
        applications_endpoint,
        "crud_application",
        SimpleNamespace(
            get_application=lambda db, aid, uid: application,
            update_application=update_application,
        ),
    )
    return state


async def request(method: str, path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_lists_pending_suggestion_with_its_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(
        monkeypatch,
        rows=[(suggestion_row(), "Svea Solar", "Engineer")],
        application=SimpleNamespace(status="applied"),
    )
    response = await request("GET", "/api/v1/applications/email-suggestions")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["company_name"] == "Svea Solar"
    assert item["current_status"] == "applied"
    assert item["suggested_status"] == "rejected"
    assert "inte gått vidare" in item["evidence"]


@pytest.mark.asyncio
async def test_suggestion_already_satisfied_is_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """No point prompting to set a status the application already has."""
    install(
        monkeypatch,
        rows=[(suggestion_row(), "Svea Solar", "Engineer")],
        application=SimpleNamespace(status="rejected"),
    )
    response = await request("GET", "/api/v1/applications/email-suggestions")

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_accept_applies_the_status_and_marks_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = suggestion_row()
    updated = SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        job_description_id=None,
        cv_id=None,
        company_name="Svea Solar",
        job_title="Engineer",
        job_url=None,
        status="rejected",
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
        created_at="2026-09-18T00:00:00Z",
        updated_at="2026-09-18T00:00:00Z",
    )
    state = install(monkeypatch, row=row, updated=updated)

    response = await request(
        "POST", f"/api/v1/applications/email-suggestions/{SUGGESTION_ID}/accept"
    )

    assert response.status_code == 200
    # Goes through the normal update path, so the timeline records it.
    assert state["update_called_with"] == (APPLICATION_ID, USER_ID, "rejected")
    assert state["state_set"] == "accepted"


@pytest.mark.asyncio
async def test_dismiss_marks_dismissed_without_touching_the_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = install(monkeypatch, row=suggestion_row())

    response = await request(
        "POST", f"/api/v1/applications/email-suggestions/{SUGGESTION_ID}/dismiss"
    )

    assert response.status_code == 204
    assert state["state_set"] == "dismissed"
    assert state["update_called_with"] is None


@pytest.mark.asyncio
async def test_accepting_another_users_suggestion_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lookups are user-scoped, so a guessed id must resolve to nothing."""
    state = install(monkeypatch, row=suggestion_row())

    response = await request(
        "POST", f"/api/v1/applications/email-suggestions/{uuid.uuid4()}/accept"
    )

    assert response.status_code == 404
    assert state["update_called_with"] is None


@pytest.mark.asyncio
async def test_dismissing_unknown_suggestion_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, row=None)
    response = await request(
        "POST", f"/api/v1/applications/email-suggestions/{SUGGESTION_ID}/dismiss"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_suggestions_path_is_not_shadowed_by_the_id_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: /{application_id} matched first and 422'd on the literal path."""
    install(monkeypatch, rows=[], application=None)
    response = await request("GET", "/api/v1/applications/email-suggestions")
    assert response.status_code == 200
