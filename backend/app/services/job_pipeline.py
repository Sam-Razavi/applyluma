"""Steps of the nightly job pipeline (scrape → dedupe → skills → keywords →
metrics → salary analytics), run in order by app.tasks.job_pipeline.

This replaced the four Airflow DAGs (scrape_jobs, scrape_swedish_jobs,
transform_jobs, extract_keywords) when the pipeline left Astro for Celery on
Railway. Each step is a plain function over a Session so it can be tested
against a real database without Celery.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date
from typing import Any, cast

from sqlalchemy import CursorResult, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.job_scrapers.base import BaseScraper
from app.services.job_scrapers.dedupe import MARK_TODAYS_DUPLICATES_SQL
from app.services.job_scrapers.keyword_extraction import extract_keywords_simple
from app.services.job_scrapers.platsbanken import PlatsbankenClient
from app.services.job_scrapers.remoteok import RemoteOKClient
from app.services.job_scrapers.remotive import RemotiveClient
from app.services.job_scrapers.skills import skills_for_posting
from app.services.job_scrapers.the_muse import TheMuseClient

logger = logging.getLogger(__name__)

# Order matters only for logs. Dropped: Jobbsafari (RSS feed gone, no API) and
# Indeed SE via Adzuna (Adzuna has no Sweden endpoint; every call returns 404).
SOURCES: list[str] = ["remotive", "the_muse", "remoteok", "platsbanken"]

KEYWORD_BATCH_SIZE = 500
KEYWORD_MAX_BATCHES = 20


def db_conn_str() -> str:
    """psycopg2 DSN for the scrapers, which write with raw psycopg2."""
    url = settings.DATABASE_URL
    for prefix in ("postgresql+psycopg2://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def build_scraper(source: str) -> BaseScraper:
    conn = db_conn_str()
    if source == "remotive":
        return RemotiveClient(db_conn_str=conn, limit=100)
    if source == "the_muse":
        return TheMuseClient(db_conn_str=conn, pages=5)
    if source == "remoteok":
        return RemoteOKClient(db_conn_str=conn)
    if source == "platsbanken":
        return PlatsbankenClient(db_conn_str=conn)
    raise ValueError(f"Unknown job source: {source}")


def scrape_source(source: str) -> int:
    """Fetch one source and insert new postings. Returns rows inserted."""
    scraper = build_scraper(source)
    return scraper.save_to_db(scraper.fetch_jobs())


def mark_duplicates(db: Session) -> int:
    marked = cast(CursorResult[Any], db.execute(text(MARK_TODAYS_DUPLICATES_SQL))).rowcount
    db.commit()
    return int(marked or 0)


def tag_skills(db: Session) -> int:
    """Fill extracted_skills for today's postings that have none yet."""
    rows = db.execute(
        text(
            "SELECT id, source, description, raw_data FROM raw_job_postings "
            "WHERE DATE(scraped_at) = CURRENT_DATE AND is_duplicate = false "
            "AND extracted_skills IS NULL"
        )
    ).all()
    if not rows:
        return 0
    db.execute(
        text("UPDATE raw_job_postings SET extracted_skills = CAST(:skills AS jsonb) WHERE id = :id"),
        [
            {"id": row.id, "skills": json.dumps(skills_for_posting(row.source, row.description, row.raw_data))}
            for row in rows
        ],
    )
    db.commit()
    return len(rows)


def extract_keywords(db: Session) -> int:
    """Extract typed keywords for today's postings, in committed batches."""
    seen: list[str] = []
    for _ in range(KEYWORD_MAX_BATCHES):
        rows = db.execute(
            text(
                "SELECT rjp.id, rjp.description FROM raw_job_postings rjp "
                "WHERE DATE(rjp.scraped_at) = CURRENT_DATE AND rjp.is_duplicate = false "
                "AND NOT EXISTS (SELECT 1 FROM extracted_keywords ek "
                "WHERE ek.raw_job_posting_id = rjp.id) "
                # Postings with nothing extractable get no keyword rows, so
                # exclude the ones this run already processed.
                "AND NOT (rjp.id::text = ANY(:seen)) "
                "LIMIT :limit"
            ),
            {"limit": KEYWORD_BATCH_SIZE, "seen": seen},
        ).all()
        if not rows:
            break
        seen.extend(str(row.id) for row in rows)
        keyword_rows = [
            {"id": row.id, "keyword": kw, "type": kw_type, "confidence": confidence, "frequency": freq}
            for row in rows
            for kw, kw_type, confidence, freq in extract_keywords_simple(row.description or "")
        ]
        if keyword_rows:
            db.execute(
                text(
                    "INSERT INTO extracted_keywords "
                    "(raw_job_posting_id, keyword, keyword_type, confidence_score, frequency) "
                    "VALUES (:id, :keyword, :type, :confidence, :frequency) "
                    "ON CONFLICT (raw_job_posting_id, keyword, keyword_type) DO NOTHING"
                ),
                keyword_rows,
            )
        db.commit()
    return len(seen)


def compute_daily_metrics(db: Session) -> int:
    """Upsert today's job_market_metrics row. Returns postings counted."""
    rows = db.execute(
        text(
            "SELECT company, remote_allowed, employment_type, salary_min, salary_max, "
            "extracted_skills FROM raw_job_postings "
            "WHERE DATE(scraped_at) = CURRENT_DATE AND is_duplicate = false"
        )
    ).all()
    if not rows:
        logger.warning("No postings scraped today; skipping daily metrics")
        return 0

    companies: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    employment_types: Counter[str] = Counter()
    salary_mins: list[int] = []
    salary_maxes: list[int] = []
    remote = 0
    for row in rows:
        companies[row.company or "Unknown"] += 1
        remote += 1 if row.remote_allowed else 0
        if row.employment_type:
            employment_types[row.employment_type] += 1
        if row.salary_min:
            salary_mins.append(row.salary_min)
        if row.salary_max:
            salary_maxes.append(row.salary_max)
        tagged = row.extracted_skills
        if isinstance(tagged, str):
            tagged = json.loads(tagged)
        for skill in tagged or []:
            skills[skill] += 1

    total = len(rows)
    params: dict[str, Any] = {
        "metric_date": date.today(),
        "total": total,
        "top_companies": json.dumps([{"company": c, "count": n} for c, n in companies.most_common(10)]),
        "top_skills": json.dumps([{"skill": s, "count": n} for s, n in skills.most_common(20)]),
        "avg_salary": json.dumps(
            {
                "avg_min": int(sum(salary_mins) / len(salary_mins)) if salary_mins else None,
                "avg_max": int(sum(salary_maxes) / len(salary_maxes)) if salary_maxes else None,
            }
        ),
        "remote_pct": round(remote / total * 100, 1),
        "employment_types": json.dumps(dict(employment_types)),
    }
    db.execute(
        text(
            "INSERT INTO job_market_metrics (metric_date, total_jobs_scraped, top_companies, "
            "top_skills, avg_salary_range, remote_percentage, employment_type_breakdown) "
            "VALUES (:metric_date, :total, CAST(:top_companies AS jsonb), CAST(:top_skills AS jsonb), "
            "CAST(:avg_salary AS jsonb), :remote_pct, CAST(:employment_types AS jsonb)) "
            "ON CONFLICT (metric_date) DO UPDATE SET "
            "total_jobs_scraped = EXCLUDED.total_jobs_scraped, "
            "top_companies = EXCLUDED.top_companies, top_skills = EXCLUDED.top_skills, "
            "avg_salary_range = EXCLUDED.avg_salary_range, "
            "remote_percentage = EXCLUDED.remote_percentage, "
            "employment_type_breakdown = EXCLUDED.employment_type_breakdown"
        ),
        params,
    )
    db.commit()
    return total


# Port of the dbt models stg_job_postings → int_jobs_deduplicated →
# int_jobs_with_skills → fct_job_postings, keeping only the columns the
# salary endpoints and analytics metadata read. Rebuilt in full each night;
# slimmed (archived, description-stripped) rows fall out via the length filter,
# exactly as they would in dbt's staging model.
_FCT_SELECT = r"""
    WITH staged AS (
        SELECT
            id::text AS job_id,
            source AS job_source,
            trim(title) AS job_title,
            trim(company) AS company_name,
            coalesce(nullif(trim(location), ''), 'Unknown') AS location,
            salary_min,
            salary_max,
            lower(coalesce(nullif(trim(employment_type), ''), 'unknown')) AS employment_type,
            coalesce(remote_allowed, false) AS remote_allowed,
            extracted_skills,
            scraped_at,
            date_trunc('day', scraped_at)::date AS scrape_date
        FROM public.raw_job_postings
        WHERE title IS NOT NULL AND trim(title) != ''
          AND company IS NOT NULL AND trim(company) != ''
          AND description IS NOT NULL AND length(description) > 50
          AND url IS NOT NULL AND url != ''
          AND NOT coalesce(is_duplicate, false)
    ),
    normalised AS (
        SELECT *,
            lower(trim(regexp_replace(
                regexp_replace(
                    job_title,
                    '\s*(senior|sr\.?|junior|jr\.?|lead|staff|principal|associate|mid-level|entry.level|intern)\s*',
                    ' ', 'gi'),
                '\s{2,}', ' ', 'g'))) AS normalised_title
        FROM staged
    ),
    deduped AS (
        SELECT * FROM (
            SELECT *, row_number() OVER (
                PARTITION BY lower(company_name), normalised_title ORDER BY scraped_at DESC
            ) AS dedup_rank
            FROM normalised
        ) ranked
        WHERE dedup_rank = 1
    )
    SELECT
        job_id,
        job_source,
        job_title,
        normalised_title,
        company_name,
        location,
        salary_min,
        salary_max,
        CASE
            WHEN salary_min IS NOT NULL AND salary_max IS NOT NULL THEN (salary_min + salary_max) / 2
            ELSE coalesce(salary_min, salary_max)
        END AS salary_midpoint,
        employment_type,
        remote_allowed,
        CASE WHEN jsonb_typeof(extracted_skills) = 'array' THEN ARRAY(
            SELECT lower(trim(s)) FROM jsonb_array_elements_text(extracted_skills) AS e(s)
            WHERE nullif(trim(s), '') IS NOT NULL
        ) END AS skill_array,
        scraped_at,
        scrape_date,
        (job_title ~* '\m(senior|sr\.?|lead|principal|staff|director|vp|head)\M') AS is_senior_role,
        (job_title ~* '\m(manager|director|head of|vp|chief|cto|cpo|ceo)\M') AS is_management_role,
        (job_title ~* '\m(junior|jr\.?|entry.level|associate|intern)\M') AS is_junior_role,
        current_timestamp AS dbt_updated_at
    FROM deduped
"""


def _salary_group(breakdown_type: str, value_expr: str, source: str, min_jobs: int, where: str = "") -> str:
    return f"""
        SELECT
            '{breakdown_type}'::text AS breakdown_type,
            {value_expr}::text AS breakdown_value,
            count(DISTINCT job_id) AS job_count,
            round(percentile_cont(0.25) WITHIN GROUP (ORDER BY salary_midpoint)) AS p25_salary,
            round(percentile_cont(0.50) WITHIN GROUP (ORDER BY salary_midpoint)) AS p50_salary,
            round(percentile_cont(0.75) WITHIN GROUP (ORDER BY salary_midpoint)) AS p75_salary,
            round(percentile_cont(0.90) WITHIN GROUP (ORDER BY salary_midpoint)) AS p90_salary,
            round(avg(salary_midpoint)) AS avg_salary,
            round(min(salary_min)) AS min_salary_floor,
            round(max(salary_max)) AS max_salary_ceiling
        FROM {source}
        {where}
        GROUP BY {value_expr}
        HAVING count(DISTINCT job_id) >= {min_jobs}
    """


_SALARY_JOBS = (
    "(SELECT * FROM analytics.fct_job_postings_build "
    "WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL) jobs"
)

# Port of the dbt model agg_salary_insights.
_AGG_SELECT = " UNION ALL ".join(
    [
        _salary_group(
            "skill", "skill", f"{_SALARY_JOBS}, unnest(skill_array) AS skill", 5,
            "WHERE skill_array IS NOT NULL AND array_length(skill_array, 1) > 0",
        ),
        _salary_group("location", "location", _SALARY_JOBS, 5, "WHERE location != 'Unknown'"),
        _salary_group("company", "company_name", _SALARY_JOBS, 3),
        _salary_group("employment_type", "employment_type", _SALARY_JOBS, 3, "WHERE employment_type != 'unknown'"),
    ]
)


def refresh_salary_analytics(db: Session) -> int:
    """Rebuild analytics.fct_job_postings and analytics.agg_salary_insights.

    Built under *_build names and swapped in by rename inside one transaction,
    so readers never see a half-built or missing table.
    """
    db.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
    db.execute(text("DROP TABLE IF EXISTS analytics.fct_job_postings_build"))
    db.execute(text("DROP TABLE IF EXISTS analytics.agg_salary_insights_build"))
    db.execute(text(f"CREATE TABLE analytics.fct_job_postings_build AS {_FCT_SELECT}"))
    db.execute(text(f"CREATE TABLE analytics.agg_salary_insights_build AS {_AGG_SELECT}"))
    # dbt built these as tables or views depending on the model's config;
    # drop whichever exists before the rename. No CASCADE: if something else
    # depends on them, fail this step visibly rather than drop it silently.
    for name in ("fct_job_postings", "agg_salary_insights"):
        kind = db.execute(
            text(
                "SELECT c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'analytics' AND c.relname = :name"
            ),
            {"name": name},
        ).scalar()
        if kind == "v":
            db.execute(text(f"DROP VIEW analytics.{name}"))
        elif kind is not None:
            db.execute(text(f"DROP TABLE analytics.{name}"))
        db.execute(text(f"ALTER TABLE analytics.{name}_build RENAME TO {name}"))
    rows = db.execute(text("SELECT count(*) FROM analytics.fct_job_postings")).scalar()
    db.commit()
    return int(rows or 0)


def active_user_ids(db: Session) -> list[str]:
    """Active users with a default CV. Without a CV every score is meaningless,
    and scoring the whole feed for them was most of the nightly worker time."""
    return [
        str(uid)
        for uid in db.execute(
            text(
                "SELECT u.id FROM users u WHERE u.is_active = true AND EXISTS "
                "(SELECT 1 FROM cvs c WHERE c.user_id = u.id AND c.is_default = true)"
            )
        ).scalars()
    ]
