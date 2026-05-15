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
from app.core.dependencies import get_current_user, get_db
from app.main import app
from app.schemas.cv import CVDiffResponse, CVDiffSection

USER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ROOT_CV_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TAILORED_CV_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
CREATED_AT = datetime(2026, 5, 15, tzinfo=UTC)


class FakeDb:
    pass


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def user() -> SimpleNamespace:
    return SimpleNamespace(id=USER_ID, is_active=True)


def cv_data(
    cv_id: uuid.UUID,
    *,
    title: str,
    is_tailored: bool = False,
    parent_cv_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=cv_id,
        user_id=USER_ID,
        title=title,
        filename="resume.pdf",
        content="Skills: Python, FastAPI",
        file_url="cvs/uuid/resume.pdf",
        is_default=False,
        is_tailored=is_tailored,
        parent_cv_id=parent_cv_id,
        tailor_job_id=None,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


def version_node(
    cv_id: uuid.UUID,
    title: str,
    *,
    is_tailored: bool = False,
    children: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=cv_id,
        title=title,
        is_tailored=is_tailored,
        created_at=CREATED_AT,
        children=children or [],
    )


async def request(
    method: str,
    path: str,
    *,
    current_user: SimpleNamespace | None = None,
    db: FakeDb | None = None,
) -> httpx.Response:
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db or FakeDb()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_get_history_returns_tree_with_root_and_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = cv_data(ROOT_CV_ID, title="Base CV")
    tailored = cv_data(
        TAILORED_CV_ID,
        title="Tailored CV",
        is_tailored=True,
        parent_cv_id=ROOT_CV_ID,
    )
    captured: dict[str, Any] = {}

    def mock_get_by_id(db, cv_id, user_id):
        assert user_id == USER_ID
        return {ROOT_CV_ID: root, TAILORED_CV_ID: tailored}.get(cv_id)

    def mock_get_version_tree(db, root_cv_id):
        captured["root_cv_id"] = root_cv_id
        return version_node(
            ROOT_CV_ID,
            "Base CV",
            children=[version_node(TAILORED_CV_ID, "Tailored CV", is_tailored=True)],
        )

    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_by_id", mock_get_by_id)
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_version_tree", mock_get_version_tree)

    response = await request(
        "GET",
        f"/api/v1/cvs/{TAILORED_CV_ID}/history",
        current_user=user(),
    )

    assert response.status_code == 200
    assert captured["root_cv_id"] == ROOT_CV_ID
    body = response.json()
    assert body["id"] == str(ROOT_CV_ID)
    assert body["children"][0]["id"] == str(TAILORED_CV_ID)
    assert body["children"][0]["is_tailored"] is True


@pytest.mark.asyncio
async def test_get_diff_returns_section_data(monkeypatch: pytest.MonkeyPatch) -> None:
    diff = CVDiffResponse(
        cv_id=TAILORED_CV_ID,
        sections=[
            CVDiffSection(
                name="Summary",
                original="Backend developer",
                tailored="Backend developer with FastAPI experience",
                changes=2,
            )
        ],
    )
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_cv_diff", lambda db, cv_id, user_id: diff)

    response = await request(
        "GET",
        f"/api/v1/cvs/{TAILORED_CV_ID}/diff",
        current_user=user(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cv_id"] == str(TAILORED_CV_ID)
    assert body["sections"][0]["name"] == "Summary"
    assert body["sections"][0]["changes"] == 2


@pytest.mark.asyncio
async def test_get_diff_on_non_tailored_cv_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cvs_endpoint.crud_cv, "get_cv_diff", lambda db, cv_id, user_id: None)

    response = await request(
        "GET",
        f"/api/v1/cvs/{ROOT_CV_ID}/diff",
        current_user=user(),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_returns_401() -> None:
    response = await request("GET", f"/api/v1/cvs/{ROOT_CV_ID}/history")

    assert response.status_code == 401
