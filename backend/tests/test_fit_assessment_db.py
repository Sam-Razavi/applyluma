"""Fit assessment endpoints and task against a real Postgres.

The endpoints query the database directly, so fakes would test nothing.
Opt-in, like the other real-database tests (CI sets TEST_DATABASE_URL):

    TEST_DATABASE_URL=postgresql://... pytest tests/test_fit_assessment_db.py
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="needs TEST_DATABASE_URL")

RESULT = {
    "recommendation": "consider",
    "rule": "R3",
    "reason": "1 of 2 mandatory requirements are met.",
    "limited_information": True,
    "model_recommendation": "high_priority",
    "summary": "A partial fit.",
    "missing_information": ["Driving licence"],
    "requirements": [],
    "quote_stats": {},
    "meta": {"model": "gpt-4o-2024-08-06"},
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.v1.endpoints import fit_assessments as endpoint
    from app.core.config import settings
    from app.core.dependencies import get_current_user, get_db
    from app.main import app
    from app.models.cv import CV
    from app.models.job import RawJobPosting
    from app.models.user import User, UserRole
    from app.tasks import fit_assessment as task_module

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    factory = sessionmaker(bind=engine)
    db = factory()
    tag = uuid.uuid4().hex[:8]

    def user(role: UserRole, with_cv: bool = True) -> User:
        row = User(email=f"fit-{role.value}-{uuid.uuid4().hex[:6]}-{tag}@example.com",
                   hashed_password="x", role=role)
        db.add(row)
        db.flush()
        if with_cv:
            db.add(CV(user_id=row.id, title="CV", filename="cv.txt", is_default=True,
                      content="BSc Computer Science. Python and SQL."))
        return row

    admin, other_admin, plain = user(UserRole.admin), user(UserRole.admin), user(UserRole.user)
    no_cv = user(UserRole.admin, with_cv=False)
    posting = RawJobPosting(
        source="platsbanken", job_id_external=uuid.uuid4().hex, title="Junior Developer",
        company="Acme", location="Stockholm", description="Python is required.",
        url=f"https://example.com/{tag}", raw_data={},
    )
    db.add(posting)
    db.commit()

    queued: list[str] = []
    monkeypatch.setattr(endpoint.run_fit_assessment, "delay",
                        lambda assessment_id: queued.append(assessment_id) or SimpleNamespace(id="task-1"))
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "FIT_ASSESSMENT_ACCESS", "admin")
    monkeypatch.setattr(task_module, "SessionLocal", factory)

    current = {"user": admin}
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current["user"]

    yield SimpleNamespace(db=db, admin=admin, other_admin=other_admin, plain=plain, no_cv=no_cv,
                          posting=posting, queued=queued, current=current, settings=settings,
                          task_module=task_module, endpoint=endpoint)

    app.dependency_overrides.clear()
    db.rollback()
    db.query(User).filter(User.email.like(f"%-{tag}@example.com")).delete(synchronize_session=False)
    db.query(RawJobPosting).filter(RawJobPosting.url == f"https://example.com/{tag}").delete()
    db.commit()
    db.close()
    engine.dispose()


def fit_advisor_prompt_version() -> str:
    from app.services.fit_advisor import PROMPT_VERSION

    return PROMPT_VERSION


async def call(method: str, path: str, **kw: Any) -> httpx.Response:
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, f"/api/v1/fit-assessments{path}", **kw)


@pytest.mark.asyncio
async def test_feature_is_invisible_to_roles_without_access(env: SimpleNamespace) -> None:
    env.current["user"] = env.plain
    body = {"raw_job_posting_id": str(env.posting.id)}

    assert (await call("GET", "/status")).json() == {"enabled": False, "daily_limit": None, "used_today": 0}
    assert (await call("POST", "", json=body)).status_code == 404
    assert (await call("GET", f"/latest?raw_job_posting_id={env.posting.id}")).status_code == 404
    assert env.queued == []

    # Opening it to everyone is a setting, not a code change.
    env.settings.FIT_ASSESSMENT_ACCESS = "all"
    assert (await call("GET", "/status")).json() == {"enabled": True, "daily_limit": 5, "used_today": 0}

    # And without a model key it is off for everyone.
    env.current["user"] = env.admin
    env.settings.OPENAI_API_KEY = ""
    assert (await call("GET", "/status")).json()["enabled"] is False


@pytest.mark.asyncio
async def test_request_run_and_read_an_assessment(env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    body = {"raw_job_posting_id": str(env.posting.id)}

    assert (await call("GET", f"/latest?raw_job_posting_id={env.posting.id}")).json() is None

    created = await call("POST", "", json=body)
    assert created.status_code == 202
    assessment = created.json()
    assert assessment["status"] == "pending" and assessment["result"] is None
    assert (assessment["job_title"], assessment["company"]) == ("Junior Developer", "Acme")
    assert (assessment["model"], assessment["prompt_version"], assessment["rules_version"]) == (
        "gpt-4o-2024-08-06", fit_advisor_prompt_version(), "1",
    )
    assert env.queued == [assessment["id"]]

    # Asking again while it runs returns the same row and queues nothing.
    again = await call("POST", "", json=body)
    assert again.status_code == 200 and again.json()["id"] == assessment["id"]
    assert len(env.queued) == 1

    seen: dict[str, Any] = {}

    def fake_assess(cv_text: str, ad_text: str, *, user_id: uuid.UUID) -> dict[str, Any]:
        seen.update(cv=cv_text, ad=ad_text, user_id=user_id)
        return RESULT

    monkeypatch.setattr(env.task_module.fit_advisor, "assess", fake_assess)
    assert env.task_module.run_fit_assessment.run(assessment["id"])["status"] == "complete"
    assert seen["ad"] == "Junior Developer\nAcme\nStockholm\n\nPython is required."
    assert seen["cv"].startswith("BSc Computer Science") and seen["user_id"] == env.admin.id

    env.db.expire_all()
    done = (await call("GET", f"/{assessment['id']}")).json()
    assert done["status"] == "complete"
    assert done["recommendation"] == "consider" and done["limited_information"] is True
    assert done["result"]["missing_information"] == ["Driving licence"]
    assert (await call("GET", f"/latest?raw_job_posting_id={env.posting.id}")).json()["id"] == assessment["id"]

    # Same CV, same ad, same versions: the stored result is shown, no new run.
    reused = await call("POST", "", json=body)
    assert reused.status_code == 200 and reused.json()["status"] == "complete"
    assert len(env.queued) == 1

    # force runs it again as a new row.
    forced = await call("POST", "", json={**body, "force": True})
    assert forced.status_code == 202 and forced.json()["id"] != assessment["id"]
    assert len(env.queued) == 2

    # Another user cannot read it.
    env.current["user"] = env.other_admin
    assert (await call("GET", f"/{assessment['id']}")).status_code == 404
    assert (await call("GET", f"/latest?raw_job_posting_id={env.posting.id}")).json() is None


@pytest.mark.asyncio
async def test_request_needs_a_real_job_and_a_default_cv(env: SimpleNamespace) -> None:
    assert (await call("POST", "", json={"raw_job_posting_id": str(uuid.uuid4())})).status_code == 404

    env.current["user"] = env.no_cv
    response = await call("POST", "", json={"raw_job_posting_id": str(env.posting.id)})
    assert response.status_code == 422 and "default" in response.json()["detail"]
    assert env.queued == []


@pytest.mark.asyncio
async def test_daily_limit_applies_to_new_runs_only(env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.user import UserRole

    monkeypatch.setitem(env.endpoint._DAILY_LIMIT, UserRole.admin, 1)
    body = {"raw_job_posting_id": str(env.posting.id)}

    assert (await call("POST", "", json=body)).status_code == 202
    assert (await call("GET", "/status")).json() == {"enabled": True, "daily_limit": 1, "used_today": 1}
    # Reading the stored one is free; a forced new run is not.
    assert (await call("POST", "", json=body)).status_code == 200
    assert (await call("POST", "", json={**body, "force": True})).status_code == 429


@pytest.mark.asyncio
async def test_model_failure_is_stored_and_a_new_run_is_allowed(
    env: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = {"raw_job_posting_id": str(env.posting.id)}
    assessment = (await call("POST", "", json=body)).json()

    def failing(*args: Any, **kw: Any) -> dict[str, Any]:
        raise env.task_module.fit_advisor.FitAdvisorError("AI API error: timed out")

    monkeypatch.setattr(env.task_module.fit_advisor, "assess", failing)
    assert env.task_module.run_fit_assessment.run(assessment["id"]) == {"error": "AI API error: timed out"}

    env.db.expire_all()
    failed = (await call("GET", f"/{assessment['id']}")).json()
    assert failed["status"] == "failed" and failed["error_message"] == "AI API error: timed out"
    # A failed run is neither "latest" nor reused, and does not use up the limit.
    assert (await call("GET", f"/latest?raw_job_posting_id={env.posting.id}")).json() is None
    assert (await call("POST", "", json=body)).status_code == 202
    assert (await call("GET", "/status")).json()["used_today"] == 1


@pytest.mark.asyncio
async def test_assessment_survives_deletion_of_its_posting(env: SimpleNamespace) -> None:
    """The retention task deletes old postings; the foreign key must not block that."""
    from app.models.fit_assessment import FitAssessment
    from app.models.job import RawJobPosting

    assessment = (await call("POST", "", json={"raw_job_posting_id": str(env.posting.id)})).json()

    env.db.query(RawJobPosting).filter(RawJobPosting.id == env.posting.id).delete()
    env.db.commit()
    env.db.expire_all()

    row = env.db.query(FitAssessment).filter(FitAssessment.id == uuid.UUID(assessment["id"])).one()
    assert row.raw_job_posting_id is None
    assert (row.job_title, row.company) == ("Junior Developer", "Acme")
