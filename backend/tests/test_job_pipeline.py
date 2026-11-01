"""Nightly job pipeline task: step order, isolation of failures, lock, run log."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks import job_pipeline as task_module


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def delete(self, key: str) -> None:
        self.store.pop(key, None)

    def exists(self, key: str) -> int:
        return int(key in self.store)


class _FakeDb:
    def __init__(self) -> None:
        self.rollbacks = 0
        self.closed = False

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"calls": [], "runs": [], "queued": [], "redis": _FakeRedis(), "db": _FakeDb()}
    steps = task_module.steps

    monkeypatch.setattr(task_module, "get_redis_client", lambda: state["redis"])
    monkeypatch.setattr(task_module, "SessionLocal", lambda: state["db"])
    monkeypatch.setattr(task_module, "RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(
        task_module, "_log_run",
        lambda db, name, rows, status, error=None: state["runs"].append((name, rows, status, error)),
    )

    def scrape(source: str) -> int:
        state["calls"].append(f"scrape:{source}")
        return 10

    monkeypatch.setattr(steps, "scrape_source", scrape)
    for name, rows in (
        ("mark_duplicates", 2), ("tag_skills", 40), ("extract_keywords", 40),
        ("compute_daily_metrics", 48), ("refresh_salary_analytics", 900),
    ):
        monkeypatch.setattr(
            steps, name, lambda db, _n=name, _r=rows: state["calls"].append(_n) or _r
        )
    monkeypatch.setattr(steps, "active_user_ids", lambda db: ["u1", "u2"])

    from app.tasks import matching

    monkeypatch.setattr(
        matching.compute_job_matching_scores, "delay",
        lambda uid, **kw: state["queued"].append((uid, kw)),
    )
    return state


def test_runs_every_step_in_order_and_logs_runs(env: dict[str, Any]) -> None:
    result = task_module.run_job_pipeline.run()

    sources = [f"scrape:{s}" for s in task_module.steps.SOURCES]
    assert env["calls"] == sources + [
        "mark_duplicates", "tag_skills", "extract_keywords",
        "compute_daily_metrics", "refresh_salary_analytics",
    ]
    assert [r[0] for r in env["runs"]] == task_module.steps.SOURCES + [
        "extracted_keywords", "transform_jobs", "salary_analytics",
    ]
    assert all(r[2] == "success" for r in env["runs"])
    assert result["sources"]["platsbanken"] == {"status": "success", "inserted": 10}
    assert result["matching"] == {"status": "success", "rows": 2}
    assert env["queued"] == [("u1", {"chain": True}), ("u2", {"chain": True})]
    assert env["db"].closed
    assert env["redis"].store == {}  # lock released


def test_a_failing_source_is_retried_logged_and_does_not_stop_the_rest(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts = {"remoteok": 0}

    def scrape(source: str) -> int:
        env["calls"].append(f"scrape:{source}")
        if source == "remoteok":
            attempts["remoteok"] += 1
            raise ConnectionError("remoteok down")
        return 5

    monkeypatch.setattr(task_module.steps, "scrape_source", scrape)

    result = task_module.run_job_pipeline.run()

    assert attempts["remoteok"] == task_module.SOURCE_ATTEMPTS
    assert result["sources"]["remoteok"]["status"] == "failed"
    assert ("remoteok", 0, "failed", "ConnectionError('remoteok down')") in env["runs"]
    assert "scrape:platsbanken" in env["calls"] and "refresh_salary_analytics" in env["calls"]


def test_a_failing_step_rolls_back_and_later_steps_still_run(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(db: Any) -> int:
        raise RuntimeError("bad sql")

    monkeypatch.setattr(task_module.steps, "compute_daily_metrics", boom)

    result = task_module.run_job_pipeline.run()

    assert result["metrics"]["status"] == "failed"
    assert ("transform_jobs", 0, "failed", "RuntimeError('bad sql')") in env["runs"]
    assert env["db"].rollbacks == 1
    assert result["salary_analytics"]["status"] == "success"
    assert env["queued"]  # matching still queued


def test_a_second_run_is_skipped_while_one_holds_the_lock(env: dict[str, Any]) -> None:
    env["redis"].set(task_module.LOCK_KEY, "someone-else")

    result = task_module.run_job_pipeline.run()

    assert result == {"skipped": "already running"}
    assert env["calls"] == []
    assert env["redis"].get(task_module.LOCK_KEY) == "someone-else"  # not released by us
    assert task_module.pipeline_is_running()


def test_beat_schedules_the_pipeline_at_two() -> None:
    from app.tasks.celery_app import celery_app

    entry = celery_app.conf.beat_schedule["run-job-pipeline-daily"]
    assert entry["task"] == "app.tasks.job_pipeline.run_job_pipeline"
    assert entry["schedule"].hour == {2} and entry["schedule"].minute == {0}
    assert "app.tasks.job_pipeline.run_job_pipeline" in celery_app.tasks
