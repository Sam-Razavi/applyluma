"""Tests for alert-preferences endpoints."""
from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _fake_user():
    return SimpleNamespace(id=USER_ID, email="sam@example.com", is_active=True, is_verified=True)


def _fake_prefs(**overrides):
    from datetime import UTC, datetime
    base = {
        "id": uuid.uuid4(),
        "user_id": USER_ID,
        "enabled": True,
        "score_threshold": 75.0,
        "frequency": "daily",
        "last_sent_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _FakeDb:
    pass


async def _call(method: str, path: str, db=None, **kwargs) -> httpx.Response:
    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    app.dependency_overrides[get_db] = lambda: db or _FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, **kwargs)


@pytest.mark.asyncio
async def test_get_alert_preferences_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.endpoints import alert_preferences as ep
    prefs = _fake_prefs()
    monkeypatch.setattr(ep.crud_alert_preferences, "get_or_create_for_user", lambda db, uid: prefs)

    response = await _call("GET", "/api/v1/me/alert-preferences")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_alert_preferences_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.endpoints import alert_preferences as ep
    prefs = _fake_prefs()
    monkeypatch.setattr(ep.crud_alert_preferences, "get_or_create_for_user", lambda db, uid: prefs)
    monkeypatch.setattr(
        ep.crud_alert_preferences,
        "update",
        lambda db, p, body: _fake_prefs(enabled=False),
    )

    response = await _call("PATCH", "/api/v1/me/alert-preferences", json={"enabled": False})

    assert response.status_code == 200
