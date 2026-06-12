from __future__ import annotations

import logging

logger = logging.getLogger("airflow.dag_failure")


def notify_dag_failure(context: dict) -> None:
    ti = context["task_instance"]
    logger.error(
        "DAG task failed | dag=%s task=%s run=%s exception=%s",
        context["dag"].dag_id,
        ti.task_id,
        context["run_id"],
        context.get("exception", "unknown"),
    )
