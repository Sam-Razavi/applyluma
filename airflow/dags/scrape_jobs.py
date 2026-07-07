from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
sys.path.insert(0, "/opt/airflow/plugins")
from job_scrapers.dedupe import mark_todays_duplicates
from job_scrapers.remoteok_client import RemoteOKClient
from job_scrapers.remotive_client import RemotiveClient
from job_scrapers.the_muse_client import TheMuseClient

logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = "postgres_default"

TRACKED_SKILLS: list[str] = [
    "fastapi", "django", "flask",
    "react", "next.js", "vue", "angular",
    "typescript", "javascript", "python", "golang", "rust", "java", "kotlin",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "gcp", "azure",
    "graphql", "rest api", "grpc",
    "celery", "airflow", "kafka", "rabbitmq",
    "machine learning", "llm", "openai", "langchain",
    "ci/cd", "github actions", "terraform",
]


def _get_db_conn_str() -> str:
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    return hook.get_uri().replace("postgres://", "postgresql://", 1)


def _extract_skills_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for skill in TRACKED_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


def scrape_remotive(**context: Any) -> dict[str, int]:
    conn_str = _get_db_conn_str()
    client = RemotiveClient(db_conn_str=conn_str, limit=100)
    jobs = client.fetch_jobs()
    saved = client.save_to_db(jobs)
    result = {"fetched": len(jobs), "saved": saved}
    logger.info("Remotive result: %s", result)
    context["ti"].xcom_push(key="remotive_result", value=result)
    return result


def scrape_the_muse(**context: Any) -> dict[str, int]:
    conn_str = _get_db_conn_str()
    client = TheMuseClient(db_conn_str=conn_str, pages=5)
    jobs = client.fetch_jobs()
    saved = client.save_to_db(jobs)
    result = {"fetched": len(jobs), "saved": saved}
    logger.info("The Muse result: %s", result)
    context["ti"].xcom_push(key="the_muse_result", value=result)
    return result


def scrape_remoteok(**context: Any) -> dict[str, int]:
    conn_str = _get_db_conn_str()
    client = RemoteOKClient(db_conn_str=conn_str)
    jobs = client.fetch_jobs()
    saved = client.save_to_db(jobs)
    result = {"fetched": len(jobs), "saved": saved}
    logger.info("RemoteOK result: %s", result)
    context["ti"].xcom_push(key="remoteok_result", value=result)
    return result


def deduplicate_jobs(**context: Any) -> int:
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    conn = hook.get_conn()
    try:
        dupes_marked = mark_todays_duplicates(conn)
    finally:
        conn.close()
    logger.info("Marked %d duplicate postings", dupes_marked)
    return dupes_marked


def extract_skills(**context: Any) -> int:
    import psycopg2.extras

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    select_sql = """
        SELECT id, description
        FROM raw_job_postings
        WHERE DATE(scraped_at) = CURRENT_DATE
          AND is_duplicate = false
          AND extracted_skills IS NULL
    """
    update_sql = """
        UPDATE raw_job_postings
        SET extracted_skills = %s
        WHERE id = %s
    """
    conn = hook.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            rows = cur.fetchall()

        updates = [
            (json.dumps(_extract_skills_from_text(description)), str(job_id))
            for job_id, description in rows
        ]

        with conn, conn.cursor() as cur:
            cur.executemany(update_sql, updates)
    finally:
        conn.close()

    logger.info("Extracted skills for %d postings", len(updates))
    return len(updates)


def log_scrape_summary(**context: Any) -> None:
    ti = context["ti"]
    remotive = ti.xcom_pull(task_ids="scrape_remotive_jobs", key="remotive_result") or {}
    the_muse = ti.xcom_pull(task_ids="scrape_the_muse_jobs", key="the_muse_result") or {}
    remoteok = ti.xcom_pull(task_ids="scrape_remoteok_jobs", key="remoteok_result") or {}
    dupes = ti.xcom_pull(task_ids="deduplicate_jobs") or 0
    skills_processed = ti.xcom_pull(task_ids="extract_skills") or 0

    total_fetched = remotive.get("fetched", 0) + the_muse.get("fetched", 0) + remoteok.get("fetched", 0)
    total_saved = remotive.get("saved", 0) + the_muse.get("saved", 0) + remoteok.get("saved", 0)

    logger.info(
        "=== Scrape Summary ===\n"
        "  Remotive : fetched=%d  saved=%d\n"
        "  The Muse : fetched=%d  saved=%d\n"
        "  RemoteOK : fetched=%d  saved=%d\n"
        "  Total    : fetched=%d  saved=%d\n"
        "  Duplicates marked : %d\n"
        "  Skills extracted  : %d postings",
        remotive.get("fetched", 0), remotive.get("saved", 0),
        the_muse.get("fetched", 0), the_muse.get("saved", 0),
        remoteok.get("fetched", 0), remoteok.get("saved", 0),
        total_fetched, total_saved,
        dupes,
        skills_processed,
    )


default_args = {
    "owner": "applyluma",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="scrape_jobs",
    description="Daily scrape of Remotive, The Muse, and RemoteOK, deduplication, and skill extraction",
    schedule_interval="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["job-market", "scraping"],
    max_active_runs=1,
) as dag:

    t_scrape_remotive = PythonOperator(
        task_id="scrape_remotive_jobs",
        python_callable=scrape_remotive,
    )

    t_scrape_muse = PythonOperator(
        task_id="scrape_the_muse_jobs",
        python_callable=scrape_the_muse,
    )

    t_scrape_remoteok = PythonOperator(
        task_id="scrape_remoteok_jobs",
        python_callable=scrape_remoteok,
    )

    t_dedup = PythonOperator(
        task_id="deduplicate_jobs",
        python_callable=deduplicate_jobs,
    )

    t_skills = PythonOperator(
        task_id="extract_skills",
        python_callable=extract_skills,
    )

    t_summary = PythonOperator(
        task_id="log_scrape_summary",
        python_callable=log_scrape_summary,
    )

    [t_scrape_remotive, t_scrape_muse, t_scrape_remoteok] >> t_dedup >> t_skills >> t_summary
