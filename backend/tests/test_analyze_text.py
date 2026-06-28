"""Tests for POST /api/v1/jobs/analyze-text endpoint."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import jobs as jobs_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

SAMPLE_DESCRIPTION = (
    "We are looking for a Senior Python Developer with experience in "
    "FastAPI, PostgreSQL, Redis, and Docker. Knowledge of React and "
    "TypeScript is a plus. Must have strong communication skills."
)


class FakeDb:
    pass


class FakeCvWithContent:
    user_id = USER_ID
    is_default = True
    content = (
        "Experienced developer with skills in Python, FastAPI, Docker, "
        "React, and JavaScript. Strong problem-solving abilities."
    )


class FakeCvQuery:
    def __init__(self, cv: object | None) -> None:
        self._cv = cv

    def filter(self, *_args: object) -> "FakeCvQuery":
        return self

    def first(self) -> object | None:
        return self._cv


class FakeDbWithCv:
    def __init__(self, cv: object | None = None) -> None:
        self._cv = cv

    def query(self, _model: object) -> FakeCvQuery:
        return FakeCvQuery(self._cv)


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


@pytest.mark.asyncio
async def test_analyze_text_returns_keywords() -> None:
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: FakeDbWithCv()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/jobs/analyze-text",
            json={"description": SAMPLE_DESCRIPTION},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "keywords" in data
    assert "matched_skills" in data
    assert "missing_skills" in data
    assert isinstance(data["keywords"], dict)


@pytest.mark.asyncio
async def test_analyze_text_with_cv_returns_matched_and_missing() -> None:
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: FakeDbWithCv(FakeCvWithContent())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/jobs/analyze-text",
            json={"description": SAMPLE_DESCRIPTION},
        )

    assert resp.status_code == 200
    data = resp.json()
    matched_lower = [s.lower() for s in data["matched_skills"]]
    missing_lower = [s.lower() for s in data["missing_skills"]]
    assert "python" in matched_lower
    assert "fastapi" in matched_lower
    assert len(data["missing_skills"]) > 0
    assert "postgresql" in missing_lower or "redis" in missing_lower


@pytest.mark.asyncio
async def test_analyze_text_no_cv_returns_empty_skills() -> None:
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: FakeDbWithCv(None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/jobs/analyze-text",
            json={"description": SAMPLE_DESCRIPTION},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_skills"] == []
    assert data["missing_skills"] == []


@pytest.mark.asyncio
async def test_analyze_text_rejects_empty_description() -> None:
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_db] = lambda: FakeDbWithCv()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v1/jobs/analyze-text",
            json={"description": "   "},
        )

    assert resp.status_code == 422
