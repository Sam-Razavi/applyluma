from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints import admin as admin_endpoint
from app.core.dependencies import get_current_user, get_db
from app.crud.admin import _health_status, _resolve_stage_health, get_pipeline_health
from app.main import app
from app.models.user import UserRole

ADMIN_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

SAMPLE_STATS = {
    "total_users": 42,
    "premium_users": 5,
    "admin_users": 1,
    "new_users_this_week": 3,
    "total_cvs": 30,
    "total_job_descriptions": 20,
    "total_applications": 60,
    "total_tailor_jobs": 15,
    "tailor_jobs_complete": 10,
    "tailor_jobs_failed": 2,
    "tailor_jobs_pending": 3,
    "total_cover_letters": 8,
}


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.refreshed: list[Any] = []

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: Any) -> None:
        self.refreshed.append(value)


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def admin_user() -> SimpleNamespace:
    return SimpleNamespace(id=ADMIN_ID, role=UserRole.admin, is_active=True, email="admin@test.com")


def regular_user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, role=UserRole.user, is_active=True, email="user@test.com")


def sample_user(
    user_id: uuid.UUID = USER_ID,
    role: UserRole = UserRole.user,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email="user@test.com",
        full_name="Test User",
        role=role,
        is_active=True,
        is_verified=False,
        subscription_status=None,
        created_at=CREATED_AT,
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


# ── Auth/role guard tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_requires_auth() -> None:
    response = await request("GET", "/api/v1/admin/stats")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stats_requires_admin_role() -> None:
    response = await request("GET", "/api/v1/admin/stats", current_user=regular_user())
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_users_requires_admin_role() -> None:
    response = await request("GET", "/api/v1/admin/users", current_user=regular_user())
    assert response.status_code == 403


# ── Stats endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_returns_expected_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_overview_stats", lambda db: SAMPLE_STATS)

    response = await request("GET", "/api/v1/admin/stats", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] == 42
    assert data["premium_users"] == 5
    assert data["admin_users"] == 1
    assert data["new_users_this_week"] == 3
    assert data["total_tailor_jobs"] == 15
    assert data["tailor_jobs_complete"] == 10
    assert data["total_cover_letters"] == 8


# ── User list endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_returns_paginated_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    users = [sample_user() for _ in range(3)]
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "list_users", lambda db, **kwargs: (users, 47)
    )

    response = await request("GET", "/api/v1/admin/users", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 47
    assert data["size"] == 25
    assert data["page"] == 1
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_users_passes_search_to_crud(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list(db: Any, **kwargs: Any) -> tuple[list, int]:
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(admin_endpoint.crud_admin, "list_users", fake_list)
    await request("GET", "/api/v1/admin/users?search=alice&role=premium", current_user=admin_user())

    assert captured.get("search") == "alice"
    assert captured.get("role") == UserRole.premium


# ── Get single user ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_returns_404_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)

    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_returns_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: sample_user()
    )

    response = await request(
        "GET", f"/api/v1/admin/users/{USER_ID}", current_user=admin_user()
    )
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"


# ── Role update ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_role_rejects_self_change(monkeypatch: pytest.MonkeyPatch) -> None:
    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{ADMIN_ID}/role",
        current_user=admin_user(),
        json_body={"role": "user"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_role_returns_404_for_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/role",
        current_user=admin_user(),
        json_body={"role": "premium"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_role_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_set_role(db: Any, user: Any, role: UserRole) -> Any:
        user.role = role
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_role", fake_set_role)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/role",
        current_user=admin_user(),
        json_body={"role": "premium"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "premium"


# ── Active update ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_active_rejects_self_disable() -> None:
    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{ADMIN_ID}/active",
        current_user=admin_user(),
        json_body={"is_active": False},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_active_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_set_active(db: Any, user: Any, is_active: bool) -> Any:
        user.is_active = is_active
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_active", fake_set_active)

    response = await request(
        "PATCH",
        f"/api/v1/admin/users/{USER_ID}/active",
        current_user=admin_user(),
        json_body={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# ── Notify user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_notify_returns_404_for_missing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: None)

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Hello", "body": "Message"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_notify_creates_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    calls: list[dict[str, Any]] = []

    def fake_notify(db: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(admin_endpoint.notification_service, "create_notification", fake_notify)

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Hi there", "body": "Admin says hello", "type": "admin_message"},
    )
    assert response.status_code == 204
    assert len(calls) == 1
    assert calls[0]["title"] == "Hi there"
    assert calls[0]["body"] == "Admin says hello"
    assert calls[0]["type"] == "admin_message"


@pytest.mark.asyncio
async def test_notify_rejects_invalid_notification_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """NotificationType Literal must reject unknown type strings with 422."""
    target = sample_user()
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    response = await request(
        "POST",
        f"/api/v1/admin/users/{USER_ID}/notify",
        current_user=admin_user(),
        json_body={"title": "Hi", "body": "Bad type", "type": "hacked"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_role_emits_audit_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing a user's role must emit a logger.warning with audit fields."""
    import logging

    target = sample_user(role=UserRole.user)
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_user_by_id_admin", lambda db, uid: target)

    def fake_set_role(db: Any, user: Any, role: UserRole) -> Any:
        user.role = role
        return user

    monkeypatch.setattr(admin_endpoint.crud_admin, "set_user_role", fake_set_role)

    log_records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(record)

    handler = _Capture()
    admin_endpoint.logger.addHandler(handler)
    try:
        response = await request(
            "PATCH",
            f"/api/v1/admin/users/{USER_ID}/role",
            current_user=admin_user(),
            json_body={"role": "premium"},
        )
    finally:
        admin_endpoint.logger.removeHandler(handler)

    assert response.status_code == 200
    assert any(r.getMessage() == "admin_role_changed" for r in log_records), (
        "Expected 'admin_role_changed' log record"
    )


@pytest.mark.asyncio
async def test_pipeline_health_requires_auth() -> None:
    response = await request("GET", "/api/v1/admin/pipeline/health")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_pipeline_health_requires_admin_role() -> None:
    response = await request("GET", "/api/v1/admin/pipeline/health", current_user=regular_user())
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pipeline_health_returns_expected_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = {
        "raw_job_postings": {
            "name": "raw_job_postings",
            "count": 12,
            "last_run": datetime(2026, 6, 16, tzinfo=UTC),
            "healthy": True,
            "status": "healthy",
        },
        "extracted_keywords": {
            "name": "extracted_keywords",
            "count": 40,
            "last_run": datetime(2026, 6, 15, tzinfo=UTC),
            "healthy": True,
            "status": "healthy",
        },
        "job_market_metrics": {
            "name": "job_market_metrics",
            "count": 2,
            "last_run": None,
            "healthy": False,
            "status": "stale",
        },
        "sources": [
            {
                "source": "the_muse",
                "count": 7,
                "last_run": datetime(2026, 6, 16, tzinfo=UTC),
                "healthy": True,
                "status": "healthy",
            }
        ],
    }
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_pipeline_health", lambda db: sample)

    response = await request("GET", "/api/v1/admin/pipeline/health", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["raw_job_postings"]["healthy"] is True
    assert data["raw_job_postings"]["status"] == "healthy"
    assert data["job_market_metrics"]["healthy"] is False
    assert data["job_market_metrics"]["status"] == "stale"
    assert data["sources"][0]["source"] == "the_muse"
    assert data["sources"][0]["healthy"] is True
    assert data["sources"][0]["status"] == "healthy"


@pytest.mark.asyncio
async def test_pipeline_jobs_over_time_returns_points(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_jobs_over_time",
        lambda db: [{"date": "2026-06-16", "count": 5}],
    )

    response = await request("GET", "/api/v1/admin/pipeline/jobs-over-time", current_user=admin_user())

    assert response.status_code == 200
    assert response.json() == [{"date": "2026-06-16", "count": 5}]


@pytest.mark.asyncio
async def test_pipeline_jobs_by_source_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_jobs_by_source",
        lambda db: [{"source": "remotive", "count": 3}],
    )

    response = await request("GET", "/api/v1/admin/pipeline/jobs-by-source", current_user=admin_user())

    assert response.status_code == 200
    assert response.json() == [{"source": "remotive", "count": 3}]


@pytest.mark.asyncio
async def test_pipeline_metrics_returns_latest_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_endpoint.crud_admin,
        "get_latest_market_metrics",
        lambda db: {
            "metric_date": "2026-06-16",
            "total_jobs_scraped": 25,
            "remote_percentage": 42.5,
            "top_skills": [{"skill": "Python", "count": 9}],
            "top_companies": [{"company": "ApplyLuma", "count": 4}],
        },
    )

    response = await request("GET", "/api/v1/admin/pipeline/metrics", current_user=admin_user())

    assert response.status_code == 200
    data = response.json()
    assert data["metric_date"] == "2026-06-16"
    assert data["remote_percentage"] == 42.5
    assert data["top_skills"] == [{"skill": "Python", "count": 9}]
    assert data["top_companies"] == [{"company": "ApplyLuma", "count": 4}]


@pytest.mark.asyncio
async def test_pipeline_metrics_returns_empty_response_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_endpoint.crud_admin, "get_latest_market_metrics", lambda db: None)

    response = await request("GET", "/api/v1/admin/pipeline/metrics", current_user=admin_user())

    assert response.status_code == 200
    assert response.json() == {
        "metric_date": None,
        "total_jobs_scraped": None,
        "remote_percentage": None,
        "top_skills": [],
        "top_companies": [],
    }


# ── Pipeline health CRUD unit tests ─────────────────────────────────────────


def _make_log_row(
    pipeline_name: str = "test",
    ran_at: datetime | None = None,
    rows_affected: int = 0,
    status: str = "success",
) -> SimpleNamespace:
    return SimpleNamespace(
        pipeline_name=pipeline_name,
        ran_at=ran_at or datetime.now(UTC),
        rows_affected=rows_affected,
        status=status,
    )


def test_health_status_healthy() -> None:
    row = _make_log_row(ran_at=datetime.now(UTC) - timedelta(hours=1))
    assert _health_status(row) == "healthy"


def test_health_status_stale() -> None:
    row = _make_log_row(ran_at=datetime.now(UTC) - timedelta(hours=30))
    assert _health_status(row) == "stale"


def test_health_status_failed() -> None:
    row = _make_log_row(ran_at=datetime.now(UTC) - timedelta(hours=1), status="failed")
    assert _health_status(row) == "failed"


def test_health_status_none() -> None:
    assert _health_status(None) == "unknown"


def test_resolve_stage_health_uses_log() -> None:
    recent = _make_log_row(pipeline_name="remotive", ran_at=datetime.now(UTC) - timedelta(hours=2))
    log_map = {"remotive": recent}
    last_run, status = _resolve_stage_health(log_map, ["remotive", "the_muse"], None)
    assert status == "healthy"
    assert last_run == recent.ran_at


def test_resolve_stage_health_picks_most_recent_pipeline() -> None:
    old = _make_log_row(pipeline_name="remotive", ran_at=datetime.now(UTC) - timedelta(hours=30))
    recent = _make_log_row(pipeline_name="platsbanken", ran_at=datetime.now(UTC) - timedelta(hours=2))
    log_map = {"remotive": old, "platsbanken": recent}
    last_run, status = _resolve_stage_health(log_map, ["remotive", "platsbanken"], None)
    assert status == "healthy"
    assert last_run == recent.ran_at


def test_resolve_stage_health_fallback_when_no_log() -> None:
    fallback_ts = datetime.now(UTC) - timedelta(hours=5)
    last_run, status = _resolve_stage_health({}, ["remotive"], fallback_ts)
    assert status == "healthy"
    assert last_run == fallback_ts


def test_resolve_stage_health_fallback_stale() -> None:
    old_ts = datetime.now(UTC) - timedelta(hours=48)
    last_run, status = _resolve_stage_health({}, ["remotive"], old_ts)
    assert status == "stale"
    assert last_run == old_ts


def test_resolve_stage_health_no_log_no_fallback() -> None:
    last_run, status = _resolve_stage_health({}, ["remotive"], None)
    assert status == "unknown"
    assert last_run is None


def test_health_status_zero_rows_but_recent_is_healthy() -> None:
    """A DAG that ran recently but inserted 0 rows should still be healthy."""
    row = _make_log_row(ran_at=datetime.now(UTC) - timedelta(hours=1), rows_affected=0)
    assert _health_status(row) == "healthy"


class _Result:
    def __init__(self, *, one: Any | None = None, all: list[Any] | None = None) -> None:
        self._one = one
        self._all = all or []

    def one(self) -> Any:
        return self._one

    def all(self) -> list[Any]:
        return self._all


class _PipelineHealthDb:
    def __init__(self) -> None:
        self.now = datetime.now(UTC)

    def execute(self, statement: Any) -> _Result:
        sql = str(statement)
        if "FROM pipeline_run_log" in sql:
            return _Result(
                all=[
                    _make_log_row(
                        pipeline_name="JobSearch API",
                        ran_at=self.now - timedelta(hours=1),
                        rows_affected=3,
                    )
                ]
            )
        if "FROM raw_job_postings GROUP BY source" in sql:
            return _Result(
                all=[
                    SimpleNamespace(
                        source="JobSearch API",
                        c=422,
                        m=self.now - timedelta(days=2),
                    )
                ]
            )
        if "FROM raw_job_postings" in sql:
            return _Result(one=SimpleNamespace(c=422, m=self.now - timedelta(days=2)))
        if "FROM extracted_keywords" in sql:
            return _Result(one=SimpleNamespace(c=0, m=None))
        if "FROM job_market_metrics" in sql:
            return _Result(one=SimpleNamespace(c=0, m=None))
        raise AssertionError(f"Unexpected query: {sql}")


def test_pipeline_health_uses_jobsearch_api_log_row() -> None:
    health = get_pipeline_health(_PipelineHealthDb())
    jobsearch = health["sources"][0]

    assert jobsearch["source"] == "JobSearch API"
    assert jobsearch["healthy"] is True
    assert jobsearch["status"] == "healthy"
    assert jobsearch["last_run"] is not None
