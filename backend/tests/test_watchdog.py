"""Health watchdog: state transitions and email throttling."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import ai_usage as ai_usage_module
from app.services import email_service as email_service_module
from app.tasks import watchdog as watchdog_module


class FakeDb:
    def close(self) -> None:
        pass


class FakeSettingsStore:
    """Stands in for the app_settings-backed get_setting/set_setting pair."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, db, key):  # noqa: ANN001
        return self.values.get(key)

    def set(self, db, key, value):  # noqa: ANN001
        self.values[key] = value


@pytest.fixture(autouse=True)
def patch_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(watchdog_module, "SessionLocal", lambda: FakeDb())


def _patch_all_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(watchdog_module, "_check_db", lambda db: {"status": "ok"})
    monkeypatch.setattr(watchdog_module, "_check_redis", lambda client: {"status": "ok"})
    monkeypatch.setattr(watchdog_module, "_check_celery", lambda: {"status": "ok"})
    monkeypatch.setattr(watchdog_module, "get_redis_client", lambda: object())
    monkeypatch.setattr(
        watchdog_module.crud_admin,
        "get_pipeline_health",
        lambda db: {"raw_job_postings": {"healthy": True}},
    )
    monkeypatch.setattr(watchdog_module, "_failed_ai_jobs_last_hour", lambda db: 0)


def _install_settings_store(monkeypatch: pytest.MonkeyPatch) -> tuple[FakeSettingsStore, list[dict]]:
    store = FakeSettingsStore()
    monkeypatch.setattr(ai_usage_module, "get_setting", store.get)
    monkeypatch.setattr(ai_usage_module, "set_setting", store.set)

    sent: list[dict] = []

    def fake_send_email(to_email: str, subject: str, html_body: str) -> None:
        sent.append({"to": to_email, "subject": subject, "body": html_body})

    monkeypatch.setattr(email_service_module, "send_email", fake_send_email)
    return store, sent


@pytest.mark.asyncio
async def test_all_healthy_stays_ok_and_sends_no_email(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    _store, sent = _install_settings_store(monkeypatch)

    result = watchdog_module.run_health_watchdog()

    assert result == {"state": "ok", "emailed": "false"}
    assert sent == []


@pytest.mark.asyncio
async def test_transition_to_degraded_sends_one_email(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    monkeypatch.setattr(watchdog_module, "_check_redis", lambda client: {"status": "degraded"})
    _store, sent = _install_settings_store(monkeypatch)

    result = watchdog_module.run_health_watchdog()

    assert result["state"] == "degraded:redis"
    assert result["emailed"] == "true"
    assert len(sent) == 1
    assert "redis" in sent[0]["subject"]


@pytest.mark.asyncio
async def test_same_degraded_state_does_not_re_email(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    monkeypatch.setattr(watchdog_module, "_check_redis", lambda client: {"status": "degraded"})
    _store, sent = _install_settings_store(monkeypatch)

    watchdog_module.run_health_watchdog()
    result = watchdog_module.run_health_watchdog()

    assert result["emailed"] == "false"
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_new_failing_check_while_degraded_emails_again(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    monkeypatch.setattr(watchdog_module, "_check_redis", lambda client: {"status": "degraded"})
    _store, sent = _install_settings_store(monkeypatch)

    watchdog_module.run_health_watchdog()

    monkeypatch.setattr(watchdog_module, "_check_celery", lambda: {"status": "degraded"})
    result = watchdog_module.run_health_watchdog()

    assert result["state"] == "degraded:celery,redis"
    assert result["emailed"] == "true"
    assert len(sent) == 2


@pytest.mark.asyncio
async def test_recovery_sends_recovery_email(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    monkeypatch.setattr(watchdog_module, "_check_redis", lambda client: {"status": "degraded"})
    _store, sent = _install_settings_store(monkeypatch)

    watchdog_module.run_health_watchdog()

    monkeypatch.setattr(watchdog_module, "_check_redis", lambda client: {"status": "ok"})
    result = watchdog_module.run_health_watchdog()

    assert result == {"state": "ok", "emailed": "true"}
    assert len(sent) == 2
    assert "cleared" in sent[1]["subject"]


@pytest.mark.asyncio
async def test_ai_job_failure_spike_marks_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    monkeypatch.setattr(watchdog_module, "_failed_ai_jobs_last_hour", lambda db: 5)
    monkeypatch.setattr(watchdog_module.settings, "WATCHDOG_FAILURE_SPIKE_THRESHOLD", 5)
    _install_settings_store(monkeypatch)

    result = watchdog_module.run_health_watchdog()

    assert result["state"] == "degraded:ai_job_failures"


@pytest.mark.asyncio
async def test_pipeline_unhealthy_marks_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_healthy(monkeypatch)
    monkeypatch.setattr(
        watchdog_module.crud_admin,
        "get_pipeline_health",
        lambda db: {"raw_job_postings": {"healthy": False}},
    )
    _install_settings_store(monkeypatch)

    result = watchdog_module.run_health_watchdog()

    assert result["state"] == "degraded:pipeline"
