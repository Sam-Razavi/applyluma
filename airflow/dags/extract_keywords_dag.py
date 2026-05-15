"""DAG: extract_keywords

Triggered after scrape_swedish_jobs: extracts typed keywords from job descriptions
and stores them in the extracted_keywords table using the Phase 10A NLP extractor.

Also triggers compute_job_matching_scores Celery task for active users.

Schedule: 03:30 UTC (after Swedish scraping).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

import psycopg2
import psycopg2.extras
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
sys.path.insert(0, "/opt/airflow/plugins")

logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = "postgres_default"
REDIS_URL = os.environ.get("AIRFLOW__CELERY__BROKER_URL", "redis://localhost:6379/0")

# Simple inline skill lists for Airflow (no heavy NLP dependency in worker)
_SIMPLE_SKILLS: list[tuple[str, str]] = [
    # (keyword, category)
    ("Python", "technical_skills"), ("JavaScript", "technical_skills"),
    ("TypeScript", "technical_skills"), ("Java", "technical_skills"),
    ("Go", "technical_skills"), ("Rust", "technical_skills"),
    ("C++", "technical_skills"), ("C#", "technical_skills"),
    ("SQL", "technical_skills"), ("PostgreSQL", "technical_skills"),
    ("MySQL", "technical_skills"), ("MongoDB", "technical_skills"),
    ("Redis", "technical_skills"), ("Docker", "technical_skills"),
    ("Kubernetes", "technical_skills"), ("Linux", "technical_skills"),
    ("AWS", "technical_skills"), ("GCP", "technical_skills"),
    ("Azure", "technical_skills"), ("Machine Learning", "technical_skills"),
    ("FastAPI", "frameworks"), ("Django", "frameworks"), ("Flask", "frameworks"),
    ("React", "frameworks"), ("Vue", "frameworks"), ("Angular", "frameworks"),
    ("NextJS", "frameworks"), ("Spring", "frameworks"), ("SpringBoot", "frameworks"),
    ("Git", "tools"), ("GitHub", "tools"), ("Jira", "tools"),
    ("Jenkins", "tools"), ("Terraform", "tools"), ("Ansible", "tools"),
    ("Leadership", "soft_skills"), ("Communication", "soft_skills"),
    ("Agile", "soft_skills"), ("Scrum", "soft_skills"),
    ("Swedish", "languages"), ("English", "languages"),
    ("Svenska", "languages"), ("Engelska", "languages"),
    ("AWS Solutions Architect", "certifications"),
    ("CKA", "certifications"), ("CKAD", "certifications"),
]


def _get_db_conn_str() -> str:
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    return hook.get_uri().replace("postgres://", "postgresql://", 1)


def _extract_keywords_simple(text: str) -> list[tuple[str, str, float, int]]:
    """Return list of (keyword, type, confidence, frequency)."""
    text_lower = text.lower()
    results = []
    for keyword, kw_type in _SIMPLE_SKILLS:
        kw_lower = keyword.lower()
        if kw_lower in text_lower:
            freq = text_lower.count(kw_lower)
            confidence = 1.0 if keyword in text else 0.6
            results.append((keyword, kw_type, confidence, freq))
    return results


def extract_keywords_for_new_jobs(**context: Any) -> int:
    """Extract keywords for jobs scraped today that have no keyword entries yet."""
    conn_str = _get_db_conn_str()
    conn = psycopg2.connect(conn_str)

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT rjp.id, rjp.description
                FROM raw_job_postings rjp
                WHERE DATE(rjp.scraped_at) = CURRENT_DATE
                  AND rjp.is_duplicate = false
                  AND NOT EXISTS (
                      SELECT 1 FROM extracted_keywords ek
                      WHERE ek.raw_job_posting_id = rjp.id
                  )
                LIMIT 500
            """)
            rows = cur.fetchall()

        logger.info("Extracting keywords for %d new postings", len(rows))

        insert_sql = """
            INSERT INTO extracted_keywords
                (raw_job_posting_id, keyword, keyword_type, confidence_score, frequency)
            VALUES %s
            ON CONFLICT (raw_job_posting_id, keyword, keyword_type) DO NOTHING
        """

        all_kw_rows = []
        for job_id, description in rows:
            keywords = _extract_keywords_simple(description or "")
            for keyword, kw_type, confidence, freq in keywords:
                all_kw_rows.append((str(job_id), keyword, kw_type, confidence, freq))

        if all_kw_rows:
            with conn, conn.cursor() as cur:
                psycopg2.extras.execute_values(cur, insert_sql, all_kw_rows)

        logger.info("Inserted keyword rows for %d postings", len(rows))
        return len(rows)

    finally:
        conn.close()


def trigger_matching_score_computation(**context: Any) -> dict[str, Any]:
    """Enqueue compute_job_matching_scores Celery tasks for all active users."""
    try:
        import redis as redis_lib

        conn_str = _get_db_conn_str()
        conn = psycopg2.connect(conn_str)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE is_active = true")
                user_ids = [str(row[0]) for row in cur.fetchall()]
        finally:
            conn.close()

        if not user_ids:
            logger.info("No active users to trigger matching for")
            return {"triggered": 0}

        r = redis_lib.Redis.from_url(REDIS_URL)
        task_name = "app.tasks.matching.compute_job_matching_scores"

        import json as _json
        queued = 0
        for uid in user_ids:
            message = _json.dumps({
                "task": task_name,
                "id": f"match-{uid}-{datetime.utcnow().strftime('%Y%m%d')}",
                "args": [uid],
                "kwargs": {},
            })
            r.lpush("celery", message)
            queued += 1

        logger.info("Queued %d matching score tasks", queued)
        return {"triggered": queued}

    except Exception as exc:
        logger.warning("Could not trigger Celery tasks: %s", exc)
        return {"triggered": 0, "error": str(exc)}


# ------------------------------------------------------------------
# DAG definition
# ------------------------------------------------------------------

default_args = {
    "owner": "applyluma",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="extract_keywords",
    description="Extract typed keywords from new job postings and trigger matching scores",
    schedule_interval="30 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["job-market", "nlp", "matching"],
    max_active_runs=1,
) as dag:

    t_extract = PythonOperator(
        task_id="extract_keywords_for_new_jobs",
        python_callable=extract_keywords_for_new_jobs,
    )

    t_trigger = PythonOperator(
        task_id="trigger_matching_score_computation",
        python_callable=trigger_matching_score_computation,
    )

    t_extract >> t_trigger
