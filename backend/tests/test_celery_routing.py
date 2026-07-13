"""Tests for Celery queue routing: tailor/cover-letter tasks must land on the
dedicated ai_pipeline queue so a second worker (start-worker-ai.sh) can be
deployed without touching application code, while the default worker
(start-worker.sh) still consumes both queues."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tasks.celery_app import celery_app


def _route_for(task_name: str) -> dict:
    return celery_app.amqp.router.route({}, task_name)


def test_tailor_task_routes_to_ai_pipeline_queue() -> None:
    route = _route_for("app.tasks.tailor.run_tailoring")
    assert route["queue"].name == "ai_pipeline"


def test_cover_letter_task_routes_to_ai_pipeline_queue() -> None:
    route = _route_for("app.tasks.cover_letter.run_cover_letter")
    assert route["queue"].name == "ai_pipeline"


def test_unrelated_task_stays_on_default_queue() -> None:
    route = _route_for("app.tasks.notifications.check_upcoming_deadlines")
    assert route["queue"].name == "celery"
