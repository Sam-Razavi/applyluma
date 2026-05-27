"""DAG: scrape_swedish_jobs

Daily scrape of Swedish job boards:
  1. Platsbanken (JobTech Dev API)
  2. Jobbsafari (RSS feeds)
  3. Indeed.se (Adzuna API)

After scraping: deduplication, Platsbanken skill enrichment, keyword extraction.
Schedule: 02:30 UTC (30 minutes after existing scrape_jobs DAG).
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
sys.path.insert(0, "/opt/airflow/plugins")

from job_scrapers.platsbanken_client import PlatsbankenClient
from job_scrapers.jobbsafari_client import JobbsafariClient
from job_scrapers.indeed_se_client import IndeedSeClient

logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = "postgres_default"


def _get_db_conn_str() -> str:
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    return hook.get_uri().replace("postgres://", "postgresql://", 1)


# ------------------------------------------------------------------
# Task callables
# ------------------------------------------------------------------

def scrape_platsbanken(**context: Any) -> dict[str, int]:
    conn_str = _get_db_conn_str()
    client = PlatsbankenClient(
        db_conn_str=conn_str,
        api_key=os.environ.get("PLATSBANKEN_API_KEY"),
    )
    jobs = client.fetch_jobs()
    saved = client.save_to_db(jobs)
    result = {"fetched": len(jobs), "saved": saved}
    logger.info("Platsbanken result: %s", result)
    context["ti"].xcom_push(key="platsbanken_result", value=result)
    return result


def scrape_jobbsafari(**context: Any) -> dict[str, int]:
    conn_str = _get_db_conn_str()
    client = JobbsafariClient(db_conn_str=conn_str)
    jobs = client.fetch_jobs()
    saved = client.save_to_db(jobs)
    result = {"fetched": len(jobs), "saved": saved}
    logger.info("Jobbsafari result: %s", result)
    context["ti"].xcom_push(key="jobbsafari_result", value=result)
    return result


def scrape_indeed_se(**context: Any) -> dict[str, int]:
    conn_str = _get_db_conn_str()
    client = IndeedSeClient(
        db_conn_str=conn_str,
        app_id=os.environ.get("ADZUNA_APP_ID", ""),
        api_key=os.environ.get("ADZUNA_API_KEY", ""),
    )
    jobs = client.fetch_jobs()
    saved = client.save_to_db(jobs)
    result = {"fetched": len(jobs), "saved": saved}
    logger.info("Indeed.se result: %s", result)
    context["ti"].xcom_push(key="indeed_se_result", value=result)
    return result


def deduplicate_swedish_jobs(**context: Any) -> int:
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    sql = """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY lower(title), lower(company)
                    ORDER BY scraped_at ASC
                ) AS rn
            FROM raw_job_postings
            WHERE DATE(scraped_at) = CURRENT_DATE
              AND source IN ('platsbanken', 'jobbsafari', 'indeed_se')
              AND is_duplicate = false
        )
        UPDATE raw_job_postings
        SET is_duplicate = true
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
    """
    conn = hook.get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql)
            dupes_marked = cur.rowcount
    finally:
        conn.close()
    logger.info("Marked %d duplicate Swedish postings", dupes_marked)
    return dupes_marked


def enrich_platsbanken_skills(**context: Any) -> int:
    """Copy Platsbanken's built-in must_have_skills into extracted_skills JSONB."""
    import json
    import psycopg2.extras

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    select_sql = """
        SELECT id, raw_data
        FROM raw_job_postings
        WHERE source = 'platsbanken'
          AND DATE(scraped_at) = CURRENT_DATE
          AND is_duplicate = false
          AND extracted_skills IS NULL
    """
    conn = hook.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            rows = cur.fetchall()

        updates = []
        for job_id, raw_data in rows:
            if not isinstance(raw_data, dict):
                continue
            must_have = raw_data.get("must_have_skills") or []
            nice_have = raw_data.get("nice_to_have_skills") or []
            skills = list({s for s in must_have + nice_have if s})
            if skills:
                updates.append((json.dumps(skills), str(job_id)))

        if updates:
            with conn, conn.cursor() as cur:
                cur.executemany(
                    "UPDATE raw_job_postings SET extracted_skills = %s WHERE id = %s",
                    updates,
                )
    finally:
        conn.close()

    logger.info("Enriched skills for %d Platsbanken postings", len(updates) if "updates" in dir() else 0)
    return len(updates) if updates else 0


def log_swedish_scrape_summary(**context: Any) -> None:
    ti = context["ti"]
    pb = ti.xcom_pull(task_ids="scrape_platsbanken", key="platsbanken_result") or {}
    js = ti.xcom_pull(task_ids="scrape_jobbsafari", key="jobbsafari_result") or {}
    ind = ti.xcom_pull(task_ids="scrape_indeed_se", key="indeed_se_result") or {}
    dupes = ti.xcom_pull(task_ids="deduplicate_swedish_jobs") or 0

    total_fetched = pb.get("fetched", 0) + js.get("fetched", 0) + ind.get("fetched", 0)
    total_saved = pb.get("saved", 0) + js.get("saved", 0) + ind.get("saved", 0)

    logger.info(
        "=== Swedish Scrape Summary ===\n"
        "  Platsbanken : fetched=%d  saved=%d\n"
        "  Jobbsafari  : fetched=%d  saved=%d\n"
        "  Indeed.se   : fetched=%d  saved=%d\n"
        "  Total       : fetched=%d  saved=%d\n"
        "  Duplicates marked: %d",
        pb.get("fetched", 0), pb.get("saved", 0),
        js.get("fetched", 0), js.get("saved", 0),
        ind.get("fetched", 0), ind.get("saved", 0),
        total_fetched, total_saved,
        dupes,
    )


# ------------------------------------------------------------------
# DAG definition
# ------------------------------------------------------------------

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
    dag_id="scrape_swedish_jobs",
    description="Daily scrape of Swedish job boards (Platsbanken, Jobbsafari, Indeed.se)",
    schedule_interval="30 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["job-market", "scraping", "swedish"],
    max_active_runs=1,
) as dag:

    t_pb = PythonOperator(
        task_id="scrape_platsbanken",
        python_callable=scrape_platsbanken,
    )

    t_js = PythonOperator(
        task_id="scrape_jobbsafari",
        python_callable=scrape_jobbsafari,
    )

    t_ind = PythonOperator(
        task_id="scrape_indeed_se",
        python_callable=scrape_indeed_se,
    )

    t_dedup = PythonOperator(
        task_id="deduplicate_swedish_jobs",
        python_callable=deduplicate_swedish_jobs,
    )

    t_enrich = PythonOperator(
        task_id="enrich_platsbanken_skills",
        python_callable=enrich_platsbanken_skills,
    )

    t_summary = PythonOperator(
        task_id="log_swedish_scrape_summary",
        python_callable=log_swedish_scrape_summary,
    )

    [t_pb, t_js, t_ind] >> t_dedup >> t_enrich >> t_summary
