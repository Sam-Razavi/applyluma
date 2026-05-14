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

from app.api.v1.endpoints import cvs as cvs_endpoint
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.main import app

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CV_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
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

def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)

def cv_data(cv_id: uuid.UUID = CV_ID, is_default: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=cv_id,
        user_id=USER_ID,
        title="My CV",
        filename="resume.pdf",
        content="Skills: Python, FastAPI",
        file_url="cvs/uuid/resume.pdf",
        is_default=is_default,
        is_tailored=False,
        parent_cv_id=None,
        tailor_job_id=None,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )

async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    json_body: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=json_body, files=files, data=data)

@pytest.mark.asyncio
async def test_list_cvs_returns_user_cvs(monkeypatch: pytest.MonkeyPatch) -> None:
    cvs = [cv_data(is_default=True), cv_data(cv_id=uuid.uuid4())]
    monkeypatch.setattr(cvs_endpoint.crud_cv, "list_for_user", lambda db, user_id: cvs)

    response = await request("GET", "/api/v1/cvs", current_user=user())

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["id"] == str(CV_ID)
    assert response.json()[0]["is_default"] is True

@pytest.mark.asyncio
async def test_get_cv_returns_not_found_for_missing_cv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: None)

    response = await request("GET", f"/api/v1/cvs/{CV_ID}", current_user=user())

    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_cv_returns_cv_details(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: cv_data())

    response = await request("GET", f"/api/v1/cvs/{CV_ID}", current_user=user())

    assert response.status_code == 200
    assert response.json()["id"] == str(CV_ID)
    assert response.json()["content"] == "Skills: Python, FastAPI"

@pytest.mark.asyncio
async def test_update_cv_modifies_title(monkeypatch: pytest.MonkeyPatch) -> None:
    cv = cv_data()
    fake_db = FakeDb()
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: cv)

    response = await request(
        "PATCH",
        f"/api/v1/cvs/{CV_ID}",
        current_user=user(),
        db=fake_db,
        json_body={"title": "Updated Title"},
    )

    assert response.status_code == 200
    assert cv.title == "Updated Title"
    assert fake_db.commits == 1

@pytest.mark.asyncio
async def test_set_default_cv_calls_crud(monkeypatch: pytest.MonkeyPatch) -> None:
    cv = cv_data()
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: cv)
    monkeypatch.setattr(cvs_endpoint.crud_cv, "set_default", lambda db, cv_obj: cv_obj)

    response = await request("PATCH", f"/api/v1/cvs/{CV_ID}/set-default", current_user=user())

    assert response.status_code == 200
    assert response.json()["id"] == str(CV_ID)

@pytest.mark.asyncio
async def test_delete_cv_removes_file_and_record(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cv = cv_data()
    cv.file_url = "cvs/test/resume.pdf"
    fake_storage = tmp_path / "storage"
    cv_file = fake_storage / cv.file_url
    cv_file.parent.mkdir(parents=True)
    cv_file.write_text("dummy content")

    monkeypatch.setattr(settings, "STORAGE_DIR", str(fake_storage))
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: cv)
    
    deleted = []
    monkeypatch.setattr(cvs_endpoint.crud_cv, "delete", lambda db, cv_obj: deleted.append(cv_obj))

    response = await request("DELETE", f"/api/v1/cvs/{CV_ID}", current_user=user())

    assert response.status_code == 204
    assert not cv_file.exists()
    assert len(deleted) == 1

@pytest.mark.asyncio
async def test_upload_cv_rejects_unsupported_type(monkeypatch: pytest.MonkeyPatch) -> None:
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    response = await request("POST", "/api/v1/cvs/upload", current_user=user(), files=files)

    assert response.status_code == 415

@pytest.mark.asyncio
async def test_upload_cv_processes_valid_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_storage = tmp_path / "storage"
    monkeypatch.setattr(settings, "STORAGE_DIR", str(fake_storage))
    monkeypatch.setattr(cvs_endpoint, "parse_cv", lambda path, ext: "Parsed Content")
    monkeypatch.setattr(cvs_endpoint.crud_cv, "count_for_user", lambda db, user_id: 0)
    
    def mock_create(db, **kwargs):
        return cv_data(is_default=kwargs.get("is_default", False))
        
    monkeypatch.setattr(cvs_endpoint.crud_cv, "create", mock_create)

    files = {"file": ("resume.pdf", b"%PDF-1.4 content", "application/pdf")}
    data = {"title": "Uploaded CV"}
    
    response = await request("POST", "/api/v1/cvs/upload", current_user=user(), files=files, data=data)

    assert response.status_code == 201
    assert response.json()["is_default"] is True
    
    # Check if file was actually "stored"
    stored_files = list(fake_storage.glob("cvs/**/*.pdf"))
    assert len(stored_files) == 1
