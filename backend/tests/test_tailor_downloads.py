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


def cv(**overrides: Any) -> SimpleNamespace:
    values = {
        "id": CV_ID,
        "user_id": USER_ID,
        "title": "Original CV",
        "filename": "original.docx",
        "file_url": None,
        "content": "Alex Example\nalex@example.com\n+1 555 0100\nStockholm, Sweden",
        "is_default": True,
        "is_tailored": False,
        "parent_cv_id": None,
        "tailor_job_id": None,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


async def request(path: str, *, db: FakeDb | None = None) -> httpx.Response:
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_download_generates_pdf_for_original_cv_without_pdf_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = FakeDb()
    original_cv = cv()
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: original_cv)

    response = await request(f"/api/v1/cvs/{CV_ID}/download", db=fake_db)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="original.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert original_cv.file_url == f"cvs/{USER_ID}/{CV_ID}.pdf"
    assert original_cv.filename == "original.pdf"
    assert fake_db.commits == 1


@pytest.mark.asyncio
async def test_download_regenerates_missing_tailored_pdf(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = FakeDb()
    tailored_cv = cv(
        title="Tailored Backend CV",
        filename="tailored_backend.pdf",
        file_url=f"cvs/{USER_ID}/tailored_backend.pdf",
        content=(
            "## Contact Information\n"
            "Alex Example\n"
            "alex@example.com\n"
            "+1 555 0100\n"
            "Stockholm, Sweden"
        ),
        is_default=False,
        is_tailored=True,
    )
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", lambda db, cv_id, user_id: tailored_cv)

    response = await request(f"/api/v1/cvs/{CV_ID}/download", db=fake_db)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'filename="tailored_backend.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert (tmp_path / "cvs" / str(USER_ID) / "tailored_backend.pdf").exists()
    assert fake_db.commits == 0
