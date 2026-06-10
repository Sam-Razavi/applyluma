"""Tests for legacy analytics endpoints (app/api/v1/endpoints/analytics/legacy.py)."""
from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.dependencies import get_current_user_id, get_db
from app.main import app


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class _FakeRow:
    """Mimics a SQLAlchemy row with attribute access."""
    def __init__(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)
        self._mapping = fields


class _FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _FakeDb:
    def __init__(self, overview_row=None, rows=None):
        self._overview_row = overview_row
        self._rows = rows or []

    def execute(self, *args, **kwargs):
        return _FakeResult(self._rows if self._rows else ([self._overview_row] if self._overview_row else []))


def _setup(db=None) -> None:
    app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"
    app.dependency_overrides[get_db] = lambda: db or _FakeDb()


async def _get(path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_overview_returns_200_when_no_data() -> None:
    _setup(db=_FakeDb(overview_row=None))

    response = await _get("/api/v1/analytics/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["total_jobs"] == 0


@pytest.mark.asyncio
async def test_overview_returns_stats_when_data_present() -> None:
    overview = _FakeRow(
        total_jobs=500,
        remote_percentage=35.0,
        avg_salary_min=40000,
        avg_salary_max=80000,
        last_updated=None,
    )
    skill_row = _FakeRow(skill="Python")

    class _TwoQueryDb:
        def __init__(self):
            self._call = 0

        def execute(self, *args, **kwargs):
            self._call += 1
            if self._call == 1:
                return _FakeResult([overview])
            return _FakeResult([skill_row])

    _setup(db=_TwoQueryDb())

    response = await _get("/api/v1/analytics/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["total_jobs"] == 500
    assert body["top_skill"] == "Python"


@pytest.mark.asyncio
async def test_top_companies_returns_list() -> None:
    row = _FakeRow(company="Acme Corp", job_count=100)
    _setup(db=_FakeDb(rows=[row]))

    response = await _get("/api/v1/analytics/top-companies")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_top_skills_returns_list() -> None:
    row = _FakeRow(skill="Python", mention_count=500, trend="up")
    _setup(db=_FakeDb(rows=[row]))

    response = await _get("/api/v1/analytics/top-skills")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_jobs_over_time_returns_list() -> None:
    row = _FakeRow(date="2026-01-01", job_count=42)
    _setup(db=_FakeDb(rows=[row]))

    response = await _get("/api/v1/analytics/jobs-over-time")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_recent_jobs_returns_list() -> None:
    from datetime import UTC, datetime
    row = _FakeRow(
        id="aaa",
        title="Engineer",
        company="Acme",
        location="Stockholm",
        url="https://acme.com/job/1",
        remote_allowed=True,
        employment_type="full_time",
        extracted_skills=["Python", "FastAPI"],
        scraped_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    _setup(db=_FakeDb(rows=[row]))

    response = await _get("/api/v1/analytics/recent-jobs")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["title"] == "Engineer"


@pytest.mark.asyncio
async def test_recent_jobs_handles_string_extracted_skills() -> None:
    """extracted_skills as a JSON string (not a list) triggers the parse branch."""
    import json
    from datetime import UTC, datetime
    row = _FakeRow(
        id="bbb",
        title="Dev",
        company="Co",
        location="NY",
        url="https://co.com/job/2",
        remote_allowed=False,
        employment_type="contract",
        extracted_skills=json.dumps(["SQL", "Redis"]),
        scraped_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    _setup(db=_FakeDb(rows=[row]))

    response = await _get("/api/v1/analytics/recent-jobs")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["extracted_skills"] == ["SQL", "Redis"]
