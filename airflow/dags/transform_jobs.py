from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

POSTGRES_CONN_ID = "postgres_default"

_DBT_ENV = {
    "DBT_DB_HOST": os.environ.get("DBT_DB_HOST", "postgres"),
    "DBT_DB_PORT": os.environ.get("DBT_DB_PORT", "5432"),
    "POSTGRES_USER":     os.environ.get("POSTGRES_USER",     "applyluma"),
    "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "applyluma"),
    "POSTGRES_DB":       os.environ.get("POSTGRES_DB",       "applyluma"),
}


def calculate_daily_metrics(**context: Any) -> None:
    import psycopg2.extras

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    today = date.today().isoformat()

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
            total_jobs_scraped        = EXCLUDED.total_jobs_scraped,
            top_companies             = EXCLUDED.top_companies,
            top_skills                = EXCLUDED.top_skills,
            avg_salary_range          = EXCLUDED.avg_salary_range,
            remote_percentage         = EXCLUDED.remote_percentage,
            employment_type_breakdown = EXCLUDED.employment_type_breakdown
    """

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
    dag_id="transform_jobs",
    description="Daily analytics: metrics aggregation and dbt transformations (runs after scrape_jobs)",
    schedule_interval="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["job-market", "analytics", "dbt"],
    max_active_runs=1,
) as dag:

    # Coordination with scrape_jobs is time-based: scrape_jobs runs at 02:00 UTC,
    # this DAG runs at 03:00 UTC, giving scraping a 1-hour head start.
    t_validate_dbt = BashOperator(
        task_id="validate_dbt_installation",
        bash_command="dbt --version && echo 'dbt validation OK'",
        append_env=True,
        env=_DBT_ENV,
    )

    t_metrics = PythonOperator(
        task_id="calculate_daily_metrics",
        python_callable=calculate_daily_metrics,
    )

    t_dbt_staging = BashOperator(
        task_id="run_dbt_staging",
        bash_command=(
            "cd /opt/airflow/dbt && "
            "dbt run --profiles-dir . --target prod --select staging 2>&1"
        ),
        append_env=True,
        env=_DBT_ENV,
    )

    t_dbt_marts = BashOperator(
        task_id="run_dbt_marts",
        bash_command=(
            "cd /opt/airflow/dbt && "
            "dbt run --profiles-dir . --target prod --select marts 2>&1"
        ),
        append_env=True,
        env=_DBT_ENV,
    )

    t_dbt_tests = BashOperator(
        task_id="run_dbt_tests",
        bash_command=(
            "cd /opt/airflow/dbt && "
            "dbt test --profiles-dir . --target prod 2>&1"
        ),
        append_env=True,
        env=_DBT_ENV,
    )

    t_validate_dbt >> [t_metrics, t_dbt_staging] >> t_dbt_marts >> t_dbt_tests
