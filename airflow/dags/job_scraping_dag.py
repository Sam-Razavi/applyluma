from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

# Make the plugins/job_scrapers package importable inside tasks
sys.path.insert(0, "/opt/airflow/plugins")
from job_scrapers.remotive_client import RemotiveClient
from job_scrapers.the_muse_client import TheMuseClient

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

POSTGRES_CONN_ID = "postgres_default"

# Skills to detect in job descriptions (order matters: longer tokens first)
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

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_db_conn_str() -> str:
    """Return a psycopg2-compatible DSN from Airflow's postgres connection."""
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


# ── Task functions ────────────────────────────────────────────────────────────


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


def deduplicate_jobs(**context: Any) -> int:
    """
    Mark duplicate postings: same title + company within the same scrape date.
    Keeps the earliest record (lowest scraped_at) as canonical.
    """
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
    logger.info("Marked %d duplicate postings", dupes_marked)
    return dupes_marked


def extract_skills(**context: Any) -> int:
    """Parse today's non-duplicate postings and write extracted_skills back."""
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
    import psycopg2.extras

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


def calculate_daily_metrics(**context: Any) -> None:
    """Aggregate today's postings into job_market_metrics."""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    today = date.today().isoformat()

    # ── Fetch today's non-duplicate postings ──────────────────────────────────
    fetch_sql = """
        SELECT
            company,
            remote_allowed,
            employment_type,
            salary_min,
            salary_max,
            extracted_skills
        FROM raw_job_postings
        WHERE DATE(scraped_at) = CURRENT_DATE
          AND is_duplicate = false
    """
    conn = hook.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(fetch_sql)
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        logger.warning("No postings found for today — skipping metrics")
        return

    total = len(rows)
    company_counter: Counter = Counter()
    skill_counter: Counter = Counter()
    emp_type_counter: Counter = Counter()
    salary_mins: list[int] = []
    salary_maxes: list[int] = []
    remote_count = 0

    for company, remote_allowed, employment_type, salary_min, salary_max, extracted_skills in rows:
        company_counter[company or "Unknown"] += 1
        if remote_allowed:
            remote_count += 1
        if employment_type:
            emp_type_counter[employment_type] += 1
        if salary_min:
            salary_mins.append(salary_min)
        if salary_max:
            salary_maxes.append(salary_max)
        if extracted_skills:
            skills = extracted_skills if isinstance(extracted_skills, list) else json.loads(extracted_skills)
            for skill in skills:
                skill_counter[skill] += 1

    top_companies = [{"company": c, "count": n} for c, n in company_counter.most_common(10)]
    top_skills = [{"skill": s, "count": n} for s, n in skill_counter.most_common(20)]
    avg_salary = {
        "avg_min": int(sum(salary_mins) / len(salary_mins)) if salary_mins else None,
        "avg_max": int(sum(salary_maxes) / len(salary_maxes)) if salary_maxes else None,
    }
    remote_pct = round(remote_count / total * 100, 1) if total else 0.0

    upsert_sql = """
        INSERT INTO job_market_metrics (
            metric_date, total_jobs_scraped, top_companies, top_skills,
            avg_salary_range, remote_percentage, employment_type_breakdown
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (metric_date) DO UPDATE SET
            total_jobs_scraped      = EXCLUDED.total_jobs_scraped,
            top_companies           = EXCLUDED.top_companies,
            top_skills              = EXCLUDED.top_skills,
            avg_salary_range        = EXCLUDED.avg_salary_range,
            remote_percentage       = EXCLUDED.remote_percentage,
            employment_type_breakdown = EXCLUDED.employment_type_breakdown
    """

    import psycopg2.extras

    conn = hook.get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                upsert_sql,
                (
                    today,
                    total,
                    psycopg2.extras.Json(top_companies),
                    psycopg2.extras.Json(top_skills),
                    psycopg2.extras.Json(avg_salary),
                    remote_pct,
                    psycopg2.extras.Json(dict(emp_type_counter)),
                ),
            )
    finally:
        conn.close()

    logger.info(
        "Metrics saved: date=%s total=%d remote_pct=%.1f%%",
        today, total, remote_pct,
    )


# ── DAG definition ────────────────────────────────────────────────────────────

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
    dag_id="job_market_scraping",
    description="Daily scrape of Remotive and The Muse, dedup, skill extraction, and metrics",
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

    t_dedup = PythonOperator(
        task_id="deduplicate_jobs",
        python_callable=deduplicate_jobs,
    )

    t_skills = PythonOperator(
        task_id="extract_skills",
        python_callable=extract_skills,
    )

    t_metrics = PythonOperator(
        task_id="calculate_daily_metrics",
        python_callable=calculate_daily_metrics,
    )

    t_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command=(
            "cd /opt/airflow/dbt && "
            "dbt run --profiles-dir . --target dev --models marts 2>&1"
        ),
        env={
            "DBT_DB_HOST": "postgres",
            "DBT_DB_PORT": "5432",
            "POSTGRES_USER":     os.environ.get("POSTGRES_USER",     "applyluma"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "applyluma"),
            "POSTGRES_DB":       os.environ.get("POSTGRES_DB",       "applyluma"),
            "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
        },
    )

    # Both scrapers run in parallel, then the rest is sequential
    [t_scrape_remotive, t_scrape_muse] >> t_dedup >> t_skills >> t_metrics >> t_dbt
