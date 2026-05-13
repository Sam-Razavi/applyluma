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

from app.api.v1.endpoints import tailor as tailor_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.tailor_job import TailorIntensity, TailorStatus
from app.models.user import UserRole

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CV_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
JD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
JOB_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
OUTPUT_CV_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
CREATED_AT = datetime(2026, 5, 11, tzinfo=UTC)


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


def user(role: UserRole = UserRole.user) -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, role=role, is_active=True)


def cv(content: str | None = "Python developer") -> SimpleNamespace:
    return SimpleNamespace(id=CV_ID, user_id=USER_ID, content=content)


def jd() -> SimpleNamespace:
    return SimpleNamespace(
        id=JD_ID,
        user_id=USER_ID,
        description="Need Python and SQL",
        keywords=["Python", "SQL"],
        job_title="Backend Engineer",
    )


def tailor_job(
    status: TailorStatus = TailorStatus.pending,
    *,
    result_json: dict[str, Any] | None = None,
    output_cv_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=JOB_ID,
        user_id=USER_ID,
        cv_id=CV_ID,
        job_description_id=JD_ID,
        intensity=TailorIntensity.medium,
        status=status,
        celery_task_id=None,
        error_message=None,
        result_json=result_json,
        language="en" if result_json else None,
        output_cv_id=output_cv_id,
        created_at=CREATED_AT,
        job_description=jd(),
    )


def preview_result() -> dict[str, Any]:
    return {
        "language": "en",
        "sections": [
            {
                "section_id": "summary",
                "section_name": "Summary",
                "original": "Original summary",
                "tailored": "Tailored summary",
                "changes": ["Added SQL"],
            },
            {
                "section_id": "skills",
                "section_name": "Skills",
                "original": "Python",
                "tailored": "Python, SQL",
                "changes": ["Added SQL"],
            },
        ],
        "meta": {
            "keywords_added": ["SQL"],
            "keywords_already_present": ["Python"],
            "intensity_applied": "medium",
        },
    }


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
async def test_submit_requires_authentication() -> None:
    response = await request(
        "POST",
        "/api/v1/tailor/submit",
        json_body={
            "cv_id": str(CV_ID),
            "job_description_id": str(JD_ID),
            "intensity": "medium",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_starts_tailoring_job(monkeypatch: pytest.MonkeyPatch) -> None:
    created_job = tailor_job()
    monkeypatch.setattr(tailor_endpoint.crud_tailor, "count_today", lambda db, user_id: 0)
    monkeypatch.setattr(tailor_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: cv())
    monkeypatch.setattr(tailor_endpoint.crud_jd, "get_by_id", lambda db, jd_id, user_id: jd())
    monkeypatch.setattr(
        tailor_endpoint.crud_tailor,
        "create",
        lambda *args, **kwargs: created_job,
    )

    def set_task_id(db: FakeDb, job: SimpleNamespace, celery_task_id: str) -> SimpleNamespace:
        job.celery_task_id = celery_task_id
        return job

    monkeypatch.setattr(tailor_endpoint.crud_tailor, "set_task_id", set_task_id)
    monkeypatch.setattr(
        tailor_endpoint.run_tailoring,
        "delay",
        lambda job_id: SimpleNamespace(id="celery-task-1"),
    )

    response = await request(
        "POST",
        "/api/v1/tailor/submit",
        current_user=user(),
        json_body={
            "cv_id": str(CV_ID),
            "job_description_id": str(JD_ID),
            "intensity": "medium",
        },
    )

    assert response.status_code == 202
    assert response.json()["id"] == str(JOB_ID)
    assert response.json()["status"] == "pending"
    assert created_job.celery_task_id == "celery-task-1"


@pytest.mark.asyncio
async def test_submit_enforces_daily_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tailor_endpoint.crud_tailor, "count_today", lambda db, user_id: 1)

    response = await request(
        "POST",
        "/api/v1/tailor/submit",
        current_user=user(),
        json_body={
            "cv_id": str(CV_ID),
            "job_description_id": str(JD_ID),
            "intensity": "medium",
        },
    )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_status_returns_current_job_state(monkeypatch: pytest.MonkeyPatch) -> None:
    states = [
        tailor_job(TailorStatus.processing),
        tailor_job(TailorStatus.complete, result_json=preview_result()),
    ]
    monkeypatch.setattr(
        tailor_endpoint.crud_tailor,
        "get_by_id",
        lambda db, job_id, user_id: states.pop(0),
    )

    first = await request("GET", f"/api/v1/tailor/{JOB_ID}/status", current_user=user())
    second = await request("GET", f"/api/v1/tailor/{JOB_ID}/status", current_user=user())

    assert first.json()["status"] == "processing"
    assert second.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_preview_requires_completed_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tailor_endpoint.crud_tailor,
        "get_by_id",
        lambda db, job_id, user_id: tailor_job(TailorStatus.pending),
    )

    response = await request("GET", f"/api/v1/tailor/{JOB_ID}/preview", current_user=user())

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_preview_returns_completed_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tailor_endpoint.crud_tailor,
        "get_by_id",
        lambda db, job_id, user_id: tailor_job(TailorStatus.complete, result_json=preview_result()),
    )

    response = await request("GET", f"/api/v1/tailor/{JOB_ID}/preview", current_user=user())

    assert response.status_code == 200
    assert response.json()["sections"][0]["tailored"] == "Tailored summary"
    assert response.json()["meta"]["keywords_added"] == ["SQL"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("accepted_section_ids", "expected_summary", "expected_skills"),
    [
        (None, "Tailored summary", "Python, SQL"),
        (["summary"], "Tailored summary", "Python"),
        ([], "Original summary", "Python"),
    ],
)
async def test_save_accepts_section_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    accepted_section_ids: list[str] | None,
    expected_summary: str,
    expected_skills: str,
) -> None:
    saved: dict[str, Any] = {}
    fake_db = FakeDb()
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(tailor_endpoint, "generate_cv_pdf", lambda sections, output_path: None)
    monkeypatch.setattr(
        tailor_endpoint.crud_tailor,
        "get_by_id",
        lambda db, job_id, user_id: tailor_job(TailorStatus.complete, result_json=preview_result()),
    )

    def create_cv(*args: Any, **kwargs: Any) -> SimpleNamespace:
        saved.update(kwargs)
        return SimpleNamespace(
            id=OUTPUT_CV_ID,
            title=kwargs["title"],
            file_url=kwargs["file_url"],
            is_tailored=False,
            parent_cv_id=None,
            tailor_job_id=None,
        )

    monkeypatch.setattr(tailor_endpoint.crud_cv, "create", create_cv)
    monkeypatch.setattr(
        tailor_endpoint.crud_tailor,
        "set_output_cv",
        lambda db, job, output_cv_id: job,
    )

    response = await request(
        "POST",
        f"/api/v1/tailor/{JOB_ID}/save",
        current_user=user(),
        db=fake_db,
        json_body={
            "accepted_section_ids": accepted_section_ids,
            "cv_title": "Tailored Backend CV",
        },
    )

    assert response.status_code == 200
    assert response.json()["cv_id"] == str(OUTPUT_CV_ID)
    assert expected_summary in saved["content"]
    assert expected_skills in saved["content"]
    assert fake_db.commits == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "expected_limit"),
    [
        (UserRole.user, 1),
        (UserRole.admin, None),
    ],
)
async def test_usage_reports_role_limits(
    monkeypatch: pytest.MonkeyPatch,
    role: UserRole,
    expected_limit: int | None,
) -> None:
    monkeypatch.setattr(tailor_endpoint.crud_tailor, "count_today", lambda db, user_id: 0)

    response = await request("GET", "/api/v1/tailor/usage", current_user=user(role))

    assert response.status_code == 200
    assert response.json()["daily_limit"] == expected_limit
