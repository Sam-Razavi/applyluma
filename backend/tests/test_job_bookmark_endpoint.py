"""Tests for the browser-extension job bookmark endpoint."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import job_bookmark as bookmark_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SAVED_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
NOW = datetime(2026, 6, 2, tzinfo=UTC)

VALID_BODY = {
    "title": "Senior Python Developer",
    "company": "Acme AB",
    "url": "https://www.linkedin.com/jobs/view/1234567890/",
    "description": "We are looking for a senior Python developer.",
    "source": "linkedin",
}


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


def _posting() -> SimpleNamespace:
    return SimpleNamespace(
        id=JOB_ID,
        source="linkedin",
        job_id_external="https://www.linkedin.com/jobs/view/1234567890/",
        title="Senior Python Developer",
        company="Acme AB",
        location=None,
        description="We are looking for a senior Python developer.",
        url="https://www.linkedin.com/jobs/view/1234567890/",
        salary_min=None,
        salary_max=None,
        employment_type=None,
        remote_allowed=False,
        scraped_at=NOW,
        created_at=NOW,
    )


def _saved_job() -> SimpleNamespace:
    return SimpleNamespace(
        id=SAVED_ID,
        user_id=USER_ID,
        raw_job_posting_id=JOB_ID,
        list_name="Extension",
        notes=None,
        starred=False,
        created_at=NOW,
        updated_at=NOW,
        job=_posting(),
    )


async def _post(json_body: dict, *, authenticated: bool = True) -> httpx.Response:
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post("/api/v1/jobs/bookmark", json=json_body)


# ------------------------------------------------------------------
# POST /api/v1/jobs/bookmark
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bookmark_new_job_returns_201(monkeypatch: pytest.MonkeyPatch) -> None:
    """Creates a new RawJobPosting and SavedJob when URL is unseen."""
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_saved_job_by_raw_id", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "save_job", lambda *a, **kw: _saved_job())

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert body["list_name"] == "Extension"
    assert body["raw_job_posting_id"] == str(JOB_ID)


@pytest.mark.asyncio
async def test_bookmark_existing_url_returns_existing_saved_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns the existing SavedJob when the URL is already bookmarked."""
    create_called = []

    def fake_create(*a, **kw):
        create_called.append(True)
        return _posting()

    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", fake_create)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_saved_job_by_raw_id", lambda *a, **kw: _saved_job())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "save_job", lambda *a, **kw: _saved_job())

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201
    assert not create_called, "create_raw_job_from_external must not be called for an existing URL"


@pytest.mark.asyncio
async def test_bookmark_missing_token_returns_401() -> None:
    """Unauthenticated requests are rejected."""
    resp = await _post(VALID_BODY, authenticated=False)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bookmark_defaults_source_to_linkedin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Omitting source defaults to 'linkedin'."""
    captured: dict = {}

    def fake_create(db, data):
        captured["source"] = data.source
        return _posting()

    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", fake_create)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_saved_job_by_raw_id", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "save_job", lambda *a, **kw: _saved_job())

    body = {k: v for k, v in VALID_BODY.items() if k != "source"}
    resp = await _post(body)
    assert resp.status_code == 201
    assert captured["source"] == "linkedin"
