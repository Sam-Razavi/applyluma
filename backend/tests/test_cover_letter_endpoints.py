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

from app.api.v1.endpoints import cover_letters as cl_endpoint
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.models.cover_letter_job import CoverLetterStatus, CoverLetterTone
from app.models.user import UserRole

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CV_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
JD_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
JOB_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CREATED_AT = datetime(2026, 5, 23, tzinfo=UTC)


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value: Any) -> None:
        pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def stub_user(role: UserRole = UserRole.user) -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, role=role, is_active=True)


def stub_cv(content: str | None = "Software engineer with Python experience") -> SimpleNamespace:
    return SimpleNamespace(id=CV_ID, user_id=USER_ID, content=content)


def stub_jd() -> SimpleNamespace:
    return SimpleNamespace(
        id=JD_ID,
        user_id=USER_ID,
        description="Looking for a Python developer",
        job_title="Software Engineer",
        company_name="Acme Corp",
    )


def stub_job(
    status: CoverLetterStatus = CoverLetterStatus.pending,
    *,
    generated_text: str | None = None,
    is_saved: bool = False,
    saved_text: str | None = None,
    title: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=JOB_ID,
        user_id=USER_ID,
        cv_id=CV_ID,
        job_description_id=JD_ID,
        tone=CoverLetterTone.formal,
        status=status,
        celery_task_id=None,
        error_message=None,
        generated_text=generated_text,
        saved_text=saved_text,
        language="en" if generated_text else None,
        word_count=200 if generated_text else None,
        title=title,
        is_saved=is_saved,
        created_at=CREATED_AT,
        job_description=stub_jd(),
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


# --- generate ---

@pytest.mark.asyncio
async def test_generate_requires_authentication() -> None:
    response = await request(
        "POST",
        "/api/v1/cover-letters/generate",
        json_body={"cv_id": str(CV_ID), "job_description_id": str(JD_ID), "tone": "formal"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_creates_job_and_dispatches_task(monkeypatch: pytest.MonkeyPatch) -> None:
    created_job = stub_job()
    monkeypatch.setattr(cl_endpoint.crud_cl, "count_today", lambda db, user_id: 0)
    monkeypatch.setattr(cl_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: stub_cv())
    monkeypatch.setattr(cl_endpoint.crud_jd, "get_by_id", lambda db, jd_id, user_id: stub_jd())
    monkeypatch.setattr(cl_endpoint.crud_cl, "create", lambda *a, **kw: created_job)

    def set_task_id(db: Any, job: SimpleNamespace, celery_task_id: str) -> SimpleNamespace:
        job.celery_task_id = celery_task_id
        return job

    monkeypatch.setattr(cl_endpoint.crud_cl, "set_task_id", set_task_id)
    monkeypatch.setattr(
        cl_endpoint.run_cover_letter,
        "delay",
        lambda job_id: SimpleNamespace(id="celery-task-1"),
    )

    response = await request(
        "POST",
        "/api/v1/cover-letters/generate",
        current_user=stub_user(),
        json_body={"cv_id": str(CV_ID), "job_description_id": str(JD_ID), "tone": "formal"},
    )

    assert response.status_code == 202
    assert response.json()["id"] == str(JOB_ID)
    assert response.json()["status"] == "pending"
    assert created_job.celery_task_id == "celery-task-1"


@pytest.mark.asyncio
async def test_generate_enforces_daily_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "count_today", lambda db, user_id: 2)

    response = await request(
        "POST",
        "/api/v1/cover-letters/generate",
        current_user=stub_user(),
        json_body={"cv_id": str(CV_ID), "job_description_id": str(JD_ID), "tone": "formal"},
    )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_generate_premium_user_higher_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    created_job = stub_job()
    monkeypatch.setattr(cl_endpoint.crud_cl, "count_today", lambda db, user_id: 2)
    monkeypatch.setattr(cl_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: stub_cv())
    monkeypatch.setattr(cl_endpoint.crud_jd, "get_by_id", lambda db, jd_id, user_id: stub_jd())
    monkeypatch.setattr(cl_endpoint.crud_cl, "create", lambda *a, **kw: created_job)
    monkeypatch.setattr(cl_endpoint.crud_cl, "set_task_id", lambda db, job, tid: job)
    monkeypatch.setattr(
        cl_endpoint.run_cover_letter,
        "delay",
        lambda job_id: SimpleNamespace(id="task-1"),
    )

    response = await request(
        "POST",
        "/api/v1/cover-letters/generate",
        current_user=stub_user(UserRole.premium),
        json_body={"cv_id": str(CV_ID), "job_description_id": str(JD_ID), "tone": "formal"},
    )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_generate_returns_404_for_missing_cv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "count_today", lambda db, user_id: 0)
    monkeypatch.setattr(cl_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: None)

    response = await request(
        "POST",
        "/api/v1/cover-letters/generate",
        current_user=stub_user(),
        json_body={"cv_id": str(CV_ID), "job_description_id": str(JD_ID), "tone": "formal"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_returns_422_for_cv_without_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "count_today", lambda db, user_id: 0)
    monkeypatch.setattr(cl_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: stub_cv(content=None))

    response = await request(
        "POST",
        "/api/v1/cover-letters/generate",
        current_user=stub_user(),
        json_body={"cv_id": str(CV_ID), "job_description_id": str(JD_ID), "tone": "formal"},
    )

    assert response.status_code == 422


# --- usage ---

@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "count", "expected_limit"),
    [
        (UserRole.user, 1, 2),
        (UserRole.premium, 5, 10),
        (UserRole.admin, 0, None),
    ],
)
async def test_usage_reports_correct_limits(
    monkeypatch: pytest.MonkeyPatch,
    role: UserRole,
    count: int,
    expected_limit: int | None,
) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "count_today", lambda db, user_id: count)

    response = await request("GET", "/api/v1/cover-letters/usage", current_user=stub_user(role))

    assert response.status_code == 200
    data = response.json()
    assert data["used_today"] == count
    assert data["daily_limit"] == expected_limit
    assert "resets_at" in data


# --- history ---

@pytest.mark.asyncio
async def test_history_returns_user_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    jobs = [stub_job(CoverLetterStatus.complete, generated_text="Dear Hiring Manager...")]
    monkeypatch.setattr(cl_endpoint.crud_cl, "list_for_user", lambda db, user_id: jobs)

    response = await request("GET", "/api/v1/cover-letters/history", current_user=stub_user())

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "complete"


# --- status ---

@pytest.mark.asyncio
async def test_status_returns_current_state(monkeypatch: pytest.MonkeyPatch) -> None:
    states = [
        stub_job(CoverLetterStatus.processing),
        stub_job(CoverLetterStatus.complete, generated_text="Dear..."),
    ]
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: states.pop(0),
    )

    first = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/status", current_user=stub_user())
    second = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/status", current_user=stub_user())

    assert first.json()["status"] == "processing"
    assert second.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_status_returns_404_for_wrong_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "get_by_id", lambda db, job_id, user_id: None)

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/status", current_user=stub_user())

    assert response.status_code == 404


# --- get cover letter ---

@pytest.mark.asyncio
async def test_get_cover_letter_returns_text_when_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(
            CoverLetterStatus.complete, generated_text="Dear Hiring Manager,\n\nI am writing..."
        ),
    )

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}", current_user=stub_user())

    assert response.status_code == 200
    data = response.json()
    assert "Dear Hiring Manager" in data["generated_text"]
    assert data["language"] == "en"
    assert data["tone"] == "formal"


@pytest.mark.asyncio
async def test_get_cover_letter_returns_409_when_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(CoverLetterStatus.pending),
    )

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}", current_user=stub_user())

    assert response.status_code == 409


# --- save ---

@pytest.mark.asyncio
async def test_save_commits_edited_text(monkeypatch: pytest.MonkeyPatch) -> None:
    saved_calls: list[dict[str, Any]] = []

    def fake_save(db: Any, job: Any, *, saved_text: str, title: str | None) -> Any:
        saved_calls.append({"saved_text": saved_text, "title": title})
        job.is_saved = True
        job.saved_text = saved_text
        job.title = title
        return job

    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(
            CoverLetterStatus.complete, generated_text="Dear Hiring Manager..."
        ),
    )
    monkeypatch.setattr(cl_endpoint.crud_cl, "save", fake_save)

    response = await request(
        "POST",
        f"/api/v1/cover-letters/{JOB_ID}/save",
        current_user=stub_user(),
        json_body={"saved_text": "Dear Hiring Manager, edited version...", "title": "Cover letter for Acme"},
    )

    assert response.status_code == 200
    assert saved_calls[0]["saved_text"] == "Dear Hiring Manager, edited version..."
    assert saved_calls[0]["title"] == "Cover letter for Acme"


@pytest.mark.asyncio
async def test_save_returns_409_when_not_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(CoverLetterStatus.processing),
    )

    response = await request(
        "POST",
        f"/api/v1/cover-letters/{JOB_ID}/save",
        current_user=stub_user(),
        json_body={"saved_text": "Some text"},
    )

    assert response.status_code == 409


# --- download ---

@pytest.mark.asyncio
async def test_download_returns_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cl_endpoint.settings, "STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(
            CoverLetterStatus.complete,
            generated_text="Dear Hiring Manager...",
            saved_text="Dear Hiring Manager, edited version...",
            title="Cover letter for Acme",
        ),
    )

    captured: dict[str, Any] = {}

    def fake_pdf(text: str, output_path: Path, *, title: str | None = None) -> None:
        captured["text"] = text
        captured["title"] = title
        output_path.write_bytes(b"%PDF-1.4 stub")

    monkeypatch.setattr(cl_endpoint, "generate_cover_letter_pdf", fake_pdf)
    monkeypatch.setattr(cl_endpoint.cv_render, "is_available", lambda: False)

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/download", current_user=stub_user())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    # Saved (edited) text takes precedence over the raw generated text.
    assert captured["text"] == "Dear Hiring Manager, edited version..."
    assert captured["title"] == "Cover letter for Acme"


@pytest.mark.asyncio
async def test_download_renders_through_cover_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cl_endpoint.settings, "STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(
            CoverLetterStatus.complete,
            generated_text="Dear Hiring Manager,\n\nFirst paragraph.\n\nKind regards,\nSam",
            title="Cover letter for Acme",
        ),
    )
    monkeypatch.setattr(
        cl_endpoint.crud_cv,
        "get_by_id",
        lambda db, cv_id, user_id: SimpleNamespace(
            content="Sam Developer\nsam@example.com\n+46 70 123 4567"
        ),
    )
    monkeypatch.setattr(cl_endpoint.cv_render, "is_available", lambda: True)

    rendered: dict[str, Any] = {}

    def fake_render(context: dict, output_path: Path, template_id: str = "nordic") -> int:
        rendered["context"] = context
        rendered["template_id"] = template_id
        output_path.write_bytes(b"%PDF-1.4 stub")
        return 1

    monkeypatch.setattr(cl_endpoint.cv_render, "render_cover_letter_pdf", fake_render)

    response = await request(
        "GET",
        f"/api/v1/cover-letters/{JOB_ID}/download?template=classic",
        current_user=stub_user(),
    )

    assert response.status_code == 200
    assert rendered["template_id"] == "classic"
    assert rendered["context"]["header"]["full_name"] == "Sam Developer"
    assert rendered["context"]["header"]["contact_bits"] == [
        "sam@example.com",
        "+46 70 123 4567",
    ]
    assert rendered["context"]["title"] == "Cover letter for Acme"
    assert rendered["context"]["paragraphs"][0] == ["Dear Hiring Manager,"]
    assert rendered["context"]["paragraphs"][-1] == ["Kind regards,", "Sam"]


@pytest.mark.asyncio
async def test_download_rejects_unknown_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(
            CoverLetterStatus.complete, generated_text="Dear Hiring Manager..."
        ),
    )

    response = await request(
        "GET",
        f"/api/v1/cover-letters/{JOB_ID}/download?template=sparkly",
        current_user=stub_user(),
    )

    assert response.status_code == 422
    assert "Unknown template" in response.json()["detail"]


@pytest.mark.asyncio
async def test_download_returns_409_when_not_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(CoverLetterStatus.processing),
    )

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/download", current_user=stub_user())

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_download_returns_404_when_no_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(CoverLetterStatus.complete, generated_text=None),
    )

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/download", current_user=stub_user())

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_returns_404_for_wrong_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "get_by_id", lambda db, job_id, user_id: None)

    response = await request("GET", f"/api/v1/cover-letters/{JOB_ID}/download", current_user=stub_user())

    assert response.status_code == 404


# --- delete ---

@pytest.mark.asyncio
async def test_delete_removes_job(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[Any] = []
    monkeypatch.setattr(
        cl_endpoint.crud_cl,
        "get_by_id",
        lambda db, job_id, user_id: stub_job(),
    )
    monkeypatch.setattr(cl_endpoint.crud_cl, "delete", lambda db, job: deleted.append(job))

    response = await request(
        "DELETE",
        f"/api/v1/cover-letters/{JOB_ID}",
        current_user=stub_user(),
    )

    assert response.status_code == 204
    assert len(deleted) == 1


@pytest.mark.asyncio
async def test_delete_returns_404_for_wrong_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cl_endpoint.crud_cl, "get_by_id", lambda db, job_id, user_id: None)

    response = await request(
        "DELETE",
        f"/api/v1/cover-letters/{JOB_ID}",
        current_user=stub_user(),
    )

    assert response.status_code == 404
