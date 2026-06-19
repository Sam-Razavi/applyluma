"""Tests for the browser-extension job bookmark endpoint."""
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

from app.api.v1.endpoints import job_bookmark as bookmark_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
JD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SCORE_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
NOW = datetime(2026, 6, 3, tzinfo=UTC)

VALID_BODY = {
    "title": "Senior Python Developer",
    "company": "Acme AB",
    "url": "https://www.linkedin.com/jobs/view/1234567890/",
    "description": "We are looking for a senior Python developer.",
    "source": "linkedin",
}

FAKE_SCORES = {
    "overall_score": 82.5,
    "skills_match": 90.0,
    "experience_match": 80.0,
    "salary_match": 70.0,
    "education_match": 100.0,
    "location_match": 70.0,
    "explanation": "Strong match.",
    "matched_skills": ["python"],
    "missing_skills": [],
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
        is_remote=False,
        scraped_at=NOW,
        created_at=NOW,
    )


def _jd() -> SimpleNamespace:
    return SimpleNamespace(
        id=JD_ID,
        user_id=USER_ID,
        source_raw_job_posting_id=JOB_ID,
        company_name="Acme AB",
        job_title="Senior Python Developer",
        description="We are looking for a senior Python developer.",
        url="https://www.linkedin.com/jobs/view/1234567890/",
        keywords=[],
        starred=False,
        notes=None,
        list_name="Extension",
        created_at=NOW,
        updated_at=NOW,
    )


def _score() -> SimpleNamespace:
    return SimpleNamespace(id=SCORE_ID, overall_score=82.5)


def _stub_no_scoring(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out scoring so existing tests don't have to set it up."""
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_job_matching_score", lambda *a, **kw: _score())


async def _post(json_body: dict[str, Any], *, authenticated: bool = True) -> httpx.Response:
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post("/api/v1/jobs/bookmark", json=json_body)


async def _get(path: str) -> httpx.Response:
    app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_db] = lambda: FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(path)


# ------------------------------------------------------------------
# POST /api/v1/jobs/bookmark
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bookmark_new_job_returns_201(monkeypatch: pytest.MonkeyPatch) -> None:
    """Creates a new RawJobPosting and JobDescription when URL is unseen."""
    _stub_no_scoring(monkeypatch)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201
    body = resp.json()
    assert body["list_name"] == "Extension"
    assert body["source_raw_job_posting_id"] == str(JOB_ID)


@pytest.mark.asyncio
async def test_bookmark_existing_url_returns_existing_jd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns the existing JobDescription when the URL is already bookmarked."""
    _stub_no_scoring(monkeypatch)
    create_called = []

    def fake_create(*a, **kw):
        create_called.append(True)
        return _posting()

    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", fake_create)
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())

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
    _stub_no_scoring(monkeypatch)
    captured: dict = {}

    def fake_create(db, data):
        captured["source"] = data.source
        return _posting()

    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", fake_create)
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())

    body = {k: v for k, v in VALID_BODY.items() if k != "source"}
    resp = await _post(body)
    assert resp.status_code == 201
    assert captured["source"] == "linkedin"


# ------------------------------------------------------------------
# Instant scoring tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bookmark_triggers_instant_scoring_for_new_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """Score is computed and upserted when no existing score is found."""
    score_upserted: list[dict] = []

    class FakeMatchingService:
        def __init__(self, db):
            pass

        def calculate_match_score(self, *a, **kw):
            return FAKE_SCORES

    monkeypatch.setattr(bookmark_endpoint, "MatchingService", FakeMatchingService)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_job_matching_score", lambda *a, **kw: None)
    monkeypatch.setattr(
        bookmark_endpoint.crud_job,
        "upsert_job_matching_score",
        lambda db, uid, jid, scores: score_upserted.append(scores) or _score(),
    )

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201
    assert len(score_upserted) == 1
    assert score_upserted[0]["overall_score"] == 82.5


@pytest.mark.asyncio
async def test_bookmark_skips_scoring_when_score_already_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Score computation is skipped when a cached score already exists."""
    scoring_called = []

    class FakeMatchingService:
        def __init__(self, db):
            pass

        def calculate_match_score(self, *a, **kw):
            scoring_called.append(True)
            return FAKE_SCORES

    monkeypatch.setattr(bookmark_endpoint, "MatchingService", FakeMatchingService)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_job_matching_score", lambda *a, **kw: _score())

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201
    assert not scoring_called, "MatchingService must not be called when score already exists"


@pytest.mark.asyncio
async def test_bookmark_succeeds_even_if_scoring_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A scoring error never blocks the save response."""
    class BrokenMatchingService:
        def __init__(self, db):
            pass

        def calculate_match_score(self, *a, **kw):
            raise RuntimeError("scoring broke")

    monkeypatch.setattr(bookmark_endpoint, "MatchingService", BrokenMatchingService)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: None)
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_job_matching_score", lambda *a, **kw: None)

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201


# ------------------------------------------------------------------
# GET /api/v1/jobs/bookmark/saved-urls
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_saved_urls_returns_url_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns the list of bookmarked job URLs for the current user."""
    fake_urls = [
        "https://www.linkedin.com/jobs/view/111/",
        "https://www.linkedin.com/jobs/view/222/",
    ]
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "list_saved_urls", lambda *a, **kw: fake_urls)

    resp = await _get("/api/v1/jobs/bookmark/saved-urls")
    assert resp.status_code == 200
    body = resp.json()
    assert body["urls"] == fake_urls


@pytest.mark.asyncio
async def test_bookmark_persists_notes_when_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    """Notes are saved to the JobDescription when the request includes a note."""
    _stub_no_scoring(monkeypatch)
    update_calls: list[Any] = []

    def fake_update(db, jd, updates):
        update_calls.append(updates.notes)
        return _jd()

    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "update", fake_update)

    body = {**VALID_BODY, "notes": "Referred by John"}
    resp = await _post(body)
    assert resp.status_code == 201
    assert update_calls == ["Referred by John"]


@pytest.mark.asyncio
async def test_bookmark_skips_notes_when_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """crud_jd.update is not called for notes when no note is provided."""
    _stub_no_scoring(monkeypatch)
    update_calls: list[Any] = []

    monkeypatch.setattr(bookmark_endpoint.crud_job, "get_raw_job_by_url", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_job, "create_raw_job_from_external", lambda *a, **kw: _posting())
    monkeypatch.setattr(bookmark_endpoint.crud_jd, "get_or_create_from_raw_job", lambda *a, **kw: _jd())
    monkeypatch.setattr(
        bookmark_endpoint.crud_jd,
        "update",
        lambda *a, **kw: update_calls.append(True) or _jd(),
    )

    resp = await _post(VALID_BODY)
    assert resp.status_code == 201
    assert not update_calls, "crud_jd.update must not be called when notes is absent"


@pytest.mark.asyncio
async def test_get_saved_urls_unauthenticated_returns_401() -> None:
    """Unauthenticated requests to saved-urls are rejected."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/v1/jobs/bookmark/saved-urls")
    assert resp.status_code == 401
