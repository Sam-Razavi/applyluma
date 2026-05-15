"""Tests for Phase 10A job discovery and saved-jobs endpoints."""
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

from app.api.v1.endpoints import jobs as jobs_endpoint
from app.api.v1.endpoints import saved_jobs as saved_jobs_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
JOB_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
SAVED_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
NOW = datetime(2026, 5, 15, tzinfo=UTC)


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


def _job_dict(job_id: uuid.UUID = JOB_ID, **extra: Any) -> dict[str, Any]:
    return {
        "job_id": str(job_id),
        "title": "Senior Python Developer",
        "company": "TechAB",
        "location": "Stockholm",
        "salary_min": 60000,
        "salary_max": 90000,
        "employment_type": "full_time",
        "remote_allowed": False,
        "url": "https://example.com/job/1",
        "source": "platsbanken",
        "scraped_at": NOW.isoformat(),
        "match_score": 87.0,
        "skills_match": 90.0,
        "experience_match": 85.0,
        "salary_match_score": 80.0,
        "education_match": 100.0,
        "location_match": 80.0,
        "explanation": "You have 5/6 required skills.",
        "keywords": [],
        "is_saved": False,
        **extra,
    }


def _saved_job(saved_id: uuid.UUID = SAVED_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=saved_id,
        user_id=USER_ID,
        raw_job_posting_id=JOB_ID,
        list_name="Dream roles",
        notes="Good company",
        starred=False,
        created_at=NOW,
        updated_at=NOW,
        job=None,
    )


async def _request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    db: Any = None,
) -> httpx.Response:
    app.dependency_overrides[get_current_user] = lambda: _user()
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=json_body)


# ------------------------------------------------------------------
# GET /jobs
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_jobs_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs_endpoint.crud_job, "list_jobs", lambda *a, **kw: [_job_dict()])

    resp = await _request("GET", "/api/v1/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["title"] == "Senior Python Developer"
    assert body[0]["source"] == "platsbanken"


@pytest.mark.asyncio
async def test_list_jobs_passes_location_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list_jobs(db, user_id, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(jobs_endpoint.crud_job, "list_jobs", fake_list_jobs)

    resp = await _request("GET", "/api/v1/jobs?location=Stockholm&salary_min=50000")
    assert resp.status_code == 200
    assert captured["location"] == "Stockholm"
    assert captured["salary_min"] == 50000


@pytest.mark.asyncio
async def test_list_jobs_passes_match_score_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list_jobs(db, user_id, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(jobs_endpoint.crud_job, "list_jobs", fake_list_jobs)

    resp = await _request("GET", "/api/v1/jobs?match_score_min=80")
    assert resp.status_code == 200
    assert captured["match_score_min"] == 80.0


@pytest.mark.asyncio
async def test_list_jobs_parses_comma_separated_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list_jobs(db, user_id, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(jobs_endpoint.crud_job, "list_jobs", fake_list_jobs)

    resp = await _request("GET", "/api/v1/jobs?keywords=Python%2CDocker%2CPostgreSQL")
    assert resp.status_code == 200
    assert captured["keywords"] == ["Python", "Docker", "PostgreSQL"]


@pytest.mark.asyncio
async def test_list_jobs_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list_jobs(db, user_id, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(jobs_endpoint.crud_job, "list_jobs", fake_list_jobs)

    resp = await _request("GET", "/api/v1/jobs?page=3&limit=10")
    assert resp.status_code == 200
    assert captured["page"] == 3
    assert captured["limit"] == 10


# ------------------------------------------------------------------
# GET /jobs/{job_id}
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_detail_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    detail = {**_job_dict(), "description": "Full job description here.", "matched_skills": [], "missing_skills": []}
    monkeypatch.setattr(jobs_endpoint.crud_job, "get_job_with_score", lambda *a, **kw: detail)

    resp = await _request("GET", f"/api/v1/jobs/{JOB_ID}")
    assert resp.status_code == 200
    assert resp.json()["job_id"] == str(JOB_ID)
    assert resp.json()["description"] == "Full job description here."


@pytest.mark.asyncio
async def test_get_job_detail_returns_404_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs_endpoint.crud_job, "get_job_with_score", lambda *a, **kw: None)

    resp = await _request("GET", f"/api/v1/jobs/{JOB_ID}")
    assert resp.status_code == 404


# ------------------------------------------------------------------
# GET /jobs/{job_id}/keywords
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_job_keywords_returns_grouped_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    kw = {"technical_skills": ["Python", "PostgreSQL"], "frameworks": ["FastAPI"], "tools": [], "soft_skills": [], "languages": ["English"], "certifications": []}
    monkeypatch.setattr(jobs_endpoint.crud_job, "get_job_keywords", lambda *a, **kw_args: kw)

    resp = await _request("GET", f"/api/v1/jobs/{JOB_ID}/keywords")
    assert resp.status_code == 200
    assert "Python" in resp.json()["technical_skills"]
    assert "FastAPI" in resp.json()["frameworks"]


# ------------------------------------------------------------------
# POST /saved-jobs
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_job_returns_201(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "save_job", lambda db, user_id, body: _saved_job())

    resp = await _request(
        "POST",
        "/api/v1/saved-jobs",
        json_body={"job_id": str(JOB_ID), "list_name": "Dream roles", "notes": "Good company"},
    )
    assert resp.status_code == 201
    assert resp.json()["raw_job_posting_id"] == str(JOB_ID)
    assert resp.json()["list_name"] == "Dream roles"


@pytest.mark.asyncio
async def test_save_job_requires_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    resp = await _request("POST", "/api/v1/saved-jobs", json_body={"list_name": "Dream roles"})
    assert resp.status_code == 422


# ------------------------------------------------------------------
# GET /saved-jobs
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_saved_jobs_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "list_saved_jobs", lambda *a, **kw: [_saved_job()])

    resp = await _request("GET", "/api/v1/saved-jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["list_name"] == "Dream roles"


@pytest.mark.asyncio
async def test_list_saved_jobs_filters_by_list_name(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list(db, user_id, list_name, sort):
        captured["list_name"] = list_name
        return []

    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "list_saved_jobs", fake_list)

    resp = await _request("GET", "/api/v1/saved-jobs?list_name=Backup+options")
    assert resp.status_code == 200
    assert captured["list_name"] == "Backup options"


# ------------------------------------------------------------------
# PATCH /saved-jobs/{id}
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_saved_job_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _saved_job()
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "get_saved_job", lambda *a, **kw: saved)
    updated = _saved_job()
    updated.starred = True
    updated.notes = "Updated notes"
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "update_saved_job", lambda *a, **kw: updated)

    resp = await _request("PATCH", f"/api/v1/saved-jobs/{SAVED_ID}", json_body={"starred": True, "notes": "Updated notes"})
    assert resp.status_code == 200
    assert resp.json()["starred"] is True


@pytest.mark.asyncio
async def test_update_saved_job_404_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "get_saved_job", lambda *a, **kw: None)

    resp = await _request("PATCH", f"/api/v1/saved-jobs/{SAVED_ID}", json_body={"starred": True})
    assert resp.status_code == 404


# ------------------------------------------------------------------
# DELETE /saved-jobs/{id}
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_saved_job_returns_204(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = _saved_job()
    deleted: list[Any] = []
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "get_saved_job", lambda *a, **kw: saved)
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "delete_saved_job", lambda db, saved: deleted.append(saved))

    resp = await _request("DELETE", f"/api/v1/saved-jobs/{SAVED_ID}")
    assert resp.status_code == 204
    assert len(deleted) == 1


@pytest.mark.asyncio
async def test_delete_saved_job_404_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saved_jobs_endpoint.crud_job, "get_saved_job", lambda *a, **kw: None)

    resp = await _request("DELETE", f"/api/v1/saved-jobs/{SAVED_ID}")
    assert resp.status_code == 404
