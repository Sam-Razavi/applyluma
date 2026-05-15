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
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
APPLICATION_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CONTACT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
EVENT_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CREATED_AT = datetime(2026, 5, 14, tzinfo=UTC)


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


def event_data(new_value: str = "wishlist", old_value: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=EVENT_ID,
        application_id=APPLICATION_ID,
        event_type="status_changed",
        old_value=old_value,
        new_value=new_value,
        description=None,
        event_date=CREATED_AT,
        created_at=CREATED_AT,
    )


def contact_data() -> SimpleNamespace:
    return SimpleNamespace(
        id=CONTACT_ID,
        application_id=APPLICATION_ID,
        name="Alex Recruiter",
        role="recruiter",
        email="alex@example.com",
        phone="+461234567",
        linkedin_url="https://linkedin.com/in/alex",
        notes="Initial contact",
        created_at=CREATED_AT,
    )


def application_data(
    *,
    status: str = "wishlist",
    events: list[SimpleNamespace] | None = None,
    contacts: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=APPLICATION_ID,
        user_id=USER_ID,
        job_description_id=None,
        cv_id=None,
        company_name="Spotify",
        job_title="Backend Engineer",
        job_url="https://example.com/job",
        status=status,
        applied_date=None,
        source="linkedin",
        salary_min=650000,
        salary_max=800000,
        location="Stockholm",
        remote_type="hybrid",
        priority=2,
        notes="Strong fit",
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        events=events if events is not None else [event_data(new_value=status)],
        contacts=contacts if contacts is not None else [],
    )


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    json_body: dict[str, Any] | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=json_body)


@pytest.mark.asyncio
async def test_create_application(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, Any] = {}

    def mock_create(db, user_id, data):
        created["user_id"] = user_id
        created["status"] = data.status
        return application_data(status=data.status)

    monkeypatch.setattr(applications_endpoint.crud_application, "create_application", mock_create)

    response = await request(
        "POST",
        "/api/v1/applications",
        current_user=user(),
        json_body={
            "company_name": "Spotify",
            "job_title": "Backend Engineer",
            "status": "applied",
            "priority": 2,
        },
    )

    assert response.status_code == 201
    assert created == {"user_id": USER_ID, "status": "applied"}
    assert response.json()["company_name"] == "Spotify"
    assert response.json()["events"][0]["new_value"] == "applied"


@pytest.mark.asyncio
async def test_list_applications_with_status_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def mock_list(db, user_id, status_filter, skip, limit):
        calls.update(
            user_id=user_id,
            status_filter=status_filter,
            skip=skip,
            limit=limit,
        )
        return [application_data(status="interview", events=[], contacts=[])]

    monkeypatch.setattr(applications_endpoint.crud_application, "get_applications", mock_list)

    response = await request(
        "GET",
        "/api/v1/applications?status=interview&skip=5&limit=10",
        current_user=user(),
    )

    assert response.status_code == 200
    assert calls == {
        "user_id": USER_ID,
        "status_filter": "interview",
        "skip": 5,
        "limit": 10,
    }
    assert response.json()[0]["status"] == "interview"


@pytest.mark.asyncio
async def test_get_single_application(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        applications_endpoint.crud_application,
        "get_application",
        lambda db, application_id, user_id: application_data(),
    )

    response = await request("GET", f"/api/v1/applications/{APPLICATION_ID}", current_user=user())

    assert response.status_code == 200
    assert response.json()["id"] == str(APPLICATION_ID)
    assert response.json()["job_title"] == "Backend Engineer"


@pytest.mark.asyncio
async def test_get_single_application_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        applications_endpoint.crud_application,
        "get_application",
        lambda db, application_id, user_id: None,
    )

    response = await request("GET", f"/api/v1/applications/{APPLICATION_ID}", current_user=user())

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_status_returns_created_event(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_update(db, application_id, user_id, data):
        assert data.status == "interview"
        return application_data(
            status="interview",
            events=[event_data(new_value="interview", old_value="applied")],
        )

    monkeypatch.setattr(applications_endpoint.crud_application, "update_application", mock_update)

    response = await request(
        "PATCH",
        f"/api/v1/applications/{APPLICATION_ID}",
        current_user=user(),
        json_body={"status": "interview"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "interview"
    assert body["events"][0]["old_value"] == "applied"
    assert body["events"][0]["new_value"] == "interview"


@pytest.mark.asyncio
async def test_delete_application(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: dict[str, Any] = {}

    def mock_delete(db, application_id, user_id):
        deleted.update(application_id=application_id, user_id=user_id)
        return True

    monkeypatch.setattr(applications_endpoint.crud_application, "delete_application", mock_delete)

    response = await request("DELETE", f"/api/v1/applications/{APPLICATION_ID}", current_user=user())

    assert response.status_code == 204
    assert deleted == {"application_id": APPLICATION_ID, "user_id": USER_ID}


@pytest.mark.asyncio
async def test_add_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_add(db, application_id, user_id, data):
        captured.update(application_id=application_id, user_id=user_id, name=data.name)
        return contact_data()

    monkeypatch.setattr(applications_endpoint.crud_application, "add_contact", mock_add)

    response = await request(
        "POST",
        f"/api/v1/applications/{APPLICATION_ID}/contacts",
        current_user=user(),
        json_body={"name": "Alex Recruiter", "role": "recruiter", "email": "alex@example.com"},
    )

    assert response.status_code == 201
    assert captured == {
        "application_id": APPLICATION_ID,
        "user_id": USER_ID,
        "name": "Alex Recruiter",
    }
    assert response.json()["id"] == str(CONTACT_ID)


@pytest.mark.asyncio
async def test_delete_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def mock_delete(db, contact_id, application_id, user_id):
        captured.update(contact_id=contact_id, application_id=application_id, user_id=user_id)
        return True

    monkeypatch.setattr(applications_endpoint.crud_application, "delete_contact", mock_delete)

    response = await request(
        "DELETE",
        f"/api/v1/applications/{APPLICATION_ID}/contacts/{CONTACT_ID}",
        current_user=user(),
    )

    assert response.status_code == 204
    assert captured == {
        "contact_id": CONTACT_ID,
        "application_id": APPLICATION_ID,
        "user_id": USER_ID,
    }


@pytest.mark.asyncio
async def test_get_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    stats = {
        "wishlist": 1,
        "applied": 2,
        "phone_screen": 0,
        "interview": 1,
        "offer": 0,
        "rejected": 3,
        "withdrawn": 0,
    }
    monkeypatch.setattr(
        applications_endpoint.crud_application,
        "get_stats",
        lambda db, user_id: stats,
    )

    response = await request("GET", "/api/v1/applications/stats", current_user=user())

    assert response.status_code == 200
    assert response.json() == stats
