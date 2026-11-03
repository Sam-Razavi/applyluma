"""Admin views of the job pipeline: run log, raw postings, stage and source health, and market metrics."""
from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.job_pipeline import SOURCES as PIPELINE_SOURCES


def list_pipeline_runs(
    db: Session,
    *,
    pipeline_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if pipeline_name:
        filters.append("pipeline_name ILIKE :pipeline_name")
        params["pipeline_name"] = f"%{pipeline_name}%"
    if status:
        filters.append("status = :status")
        params["status"] = status
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    total = db.execute(text(f"SELECT COUNT(*) FROM pipeline_run_log {where}"), params).scalar() or 0
    rows = db.execute(
        text(
            "SELECT id, pipeline_name, ran_at, rows_affected, status, error_message "
            f"FROM pipeline_run_log {where} ORDER BY ran_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def list_raw_jobs_admin(
    db: Session,
    *,
    search: str | None = None,
    source: str | None = None,
    duplicate: bool | None = None,
    remote: bool | None = None,
    page: int = 1,
    size: int = 25,
) -> tuple[list[dict[str, Any]], int]:
    filters: list[str] = []
    params: dict[str, Any] = {"limit": size, "offset": (page - 1) * size}
    if search:
        filters.append("(r.title ILIKE :search OR r.company ILIKE :search OR r.location ILIKE :search)")
        params["search"] = f"%{search}%"
    if source:
        filters.append("r.source = :source")
        params["source"] = source
    if duplicate is not None:
        filters.append("r.is_duplicate = :duplicate")
        params["duplicate"] = duplicate
    if remote is not None:
        filters.append("(r.is_remote = :remote OR r.remote_allowed = :remote)")
        params["remote"] = remote
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    count_sql = f"SELECT COUNT(*) FROM raw_job_postings r {where}"
    total = db.execute(text(count_sql), params).scalar() or 0
    rows = db.execute(
        text(
            "SELECT r.id, r.source, r.job_id_external, r.title, r.company, r.location, r.url, "
            "r.salary_min, r.salary_max, r.employment_type, r.remote_allowed, r.is_remote, "
            "r.is_duplicate, r.application_deadline, r.scraped_at, "
            "COUNT(DISTINCT ek.id)::int AS keyword_count, "
            "COUNT(DISTINCT sj.id)::int AS saved_count, "
            "COUNT(DISTINCT jms.id)::int AS matching_score_count "
            "FROM raw_job_postings r "
            "LEFT JOIN extracted_keywords ek ON ek.raw_job_posting_id = r.id "
            "LEFT JOIN saved_jobs sj ON sj.raw_job_posting_id = r.id "
            "LEFT JOIN job_matching_scores jms ON jms.raw_job_posting_id = r.id "
            f"{where} "
            "GROUP BY r.id ORDER BY r.scraped_at DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows], int(total)


def get_raw_job_detail_admin(db: Session, job_id: uuid.UUID) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT r.*, "
            "COUNT(DISTINCT ek.id)::int AS keyword_count, "
            "COUNT(DISTINCT sj.id)::int AS saved_count, "
            "COUNT(DISTINCT jms.id)::int AS matching_score_count "
            "FROM raw_job_postings r "
            "LEFT JOIN extracted_keywords ek ON ek.raw_job_posting_id = r.id "
            "LEFT JOIN saved_jobs sj ON sj.raw_job_posting_id = r.id "
            "LEFT JOIN job_matching_scores jms ON jms.raw_job_posting_id = r.id "
            "WHERE r.id = :job_id GROUP BY r.id"
        ),
        {"job_id": job_id},
    ).mappings().first()
    if row is None:
        return None
    keywords = db.execute(
        text(
            "SELECT keyword AS skill, SUM(frequency)::int AS count "
            "FROM extracted_keywords WHERE raw_job_posting_id = :job_id "
            "GROUP BY keyword ORDER BY count DESC LIMIT 25"
        ),
        {"job_id": job_id},
    ).mappings().all()
    data = dict(row)
    data["keywords"] = [dict(k) for k in keywords]
    return data


_HEALTH_WINDOW = timedelta(hours=25)


# Sources the old Airflow DAGs scraped. Their archived rows stay in
# raw_job_postings for 90 days, so without this they showed as "Stale".
RETIRED_SOURCES: frozenset[str] = frozenset(
    {"jobbsafari", "indeed_se", "adzuna_remote", "adzuna_nl", "adzuna_fr", "adzuna_de"}
)


_STAGE_PIPELINES: dict[str, list[str]] = {
    "raw_job_postings": list(PIPELINE_SOURCES),
    "extracted_keywords": ["extracted_keywords"],
    "job_market_metrics": ["transform_jobs"],
}


def _health_status(log_row: Any | None) -> str:
    """Return 'healthy', 'stale', or 'failed' based on the latest pipeline_run_log entry."""
    if log_row is None:
        return "unknown"
    if log_row.status == "failed":
        return "failed"
    if (datetime.now(UTC) - log_row.ran_at) <= _HEALTH_WINDOW:
        return "healthy"
    return "stale"


def _get_pipeline_log_map(db: Session) -> dict[str, Any]:
    rows = db.execute(
        text(
            "SELECT DISTINCT ON (pipeline_name) "
            "pipeline_name, ran_at, rows_affected, status "
            "FROM pipeline_run_log "
            "ORDER BY pipeline_name, ran_at DESC"
        )
    ).all()
    return {r.pipeline_name: r for r in rows}


def _resolve_stage_health(
    log_map: dict[str, Any],
    pipeline_names: list[str],
    fallback_last_run: datetime | None,
) -> tuple[datetime | None, str]:
    """Pick the most recent log entry across the given pipeline names.

    Falls back to *fallback_last_run* (legacy MAX query) when no log rows exist.
    """
    best = None
    for name in pipeline_names:
        entry = log_map.get(name)
        if entry is not None and (best is None or entry.ran_at > best.ran_at):
            best = entry

    if best is not None:
        return best.ran_at, _health_status(best)

    if fallback_last_run is not None and (datetime.now(UTC) - fallback_last_run) <= _HEALTH_WINDOW:
        return fallback_last_run, "healthy"
    if fallback_last_run is not None:
        return fallback_last_run, "stale"
    return None, "unknown"


def get_pipeline_health(db: Session) -> dict[str, Any]:
    log_map = _get_pipeline_log_map(db)

    rjp = db.execute(text("SELECT COUNT(*) AS c, MAX(scraped_at) AS m FROM raw_job_postings")).one()
    ek = db.execute(text("SELECT COUNT(*) AS c, MAX(created_at) AS m FROM extracted_keywords")).one()
    jmm = db.execute(text("SELECT COUNT(*) AS c, MAX(created_at) AS m FROM job_market_metrics")).one()
    src = db.execute(
        text(
            "SELECT source, COUNT(*) AS c, COUNT(*) FILTER (WHERE archived_at IS NULL) AS live, "
            "MAX(scraped_at) AS m "
            "FROM raw_job_postings GROUP BY source ORDER BY c DESC"
        )
    ).all()

    def stage(name: str, row: Any) -> dict[str, Any]:
        pipelines = _STAGE_PIPELINES.get(name, [])
        last_run, status = _resolve_stage_health(log_map, pipelines, row.m)
        return {
            "name": name,
            "count": int(row.c or 0),
            "last_run": last_run,
            "healthy": status == "healthy",
            "status": status,
        }

    def unscheduled(row: Any, status: str) -> dict[str, Any]:
        # Not run by the nightly pipeline, so freshness says nothing about health.
        return {
            "source": row.source,
            "count": int(row.c or 0),
            "last_run": row.m,
            "healthy": False,
            "status": status,
        }

    def source_health(row: Any) -> dict[str, Any]:
        entry = log_map.get(row.source)
        if entry is not None:
            status = _health_status(entry)
            return {
                "source": row.source,
                "count": int(row.c or 0),
                "last_run": entry.ran_at,
                "healthy": status == "healthy",
                "status": status,
            }
        fallback_healthy = row.m is not None and (datetime.now(UTC) - row.m) <= _HEALTH_WINDOW
        return {
            "source": row.source,
            "count": int(row.c or 0),
            "last_run": row.m,
            "healthy": fallback_healthy,
            "status": "healthy" if fallback_healthy else ("stale" if row.m else "unknown"),
        }

    return {
        "raw_job_postings": stage("raw_job_postings", rjp),
        "extracted_keywords": stage("extracted_keywords", ek),
        "job_market_metrics": stage("job_market_metrics", jmm),
        "sources": _source_rows(src, source_health, unscheduled),
    }


def _source_rows(
    src: list[Any],
    scheduled: Callable[[Any], dict[str, Any]],
    unscheduled: Callable[[Any, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Scheduled sources first (always listed, health from the run log), then
    sources users saved jobs from (extension, Job Search tab) as "on_demand",
    then retired scrapers that still have live postings as "retired". Retired
    scrapers whose postings are all archived are left out."""
    by_source = {r.source: r for r in src}
    rows = [
        scheduled(by_source.get(name) or SimpleNamespace(source=name, c=0, live=0, m=None))
        for name in PIPELINE_SOURCES
    ]
    for r in src:
        if r.source in PIPELINE_SOURCES:
            continue
        if r.source in RETIRED_SOURCES:
            if (getattr(r, "live", 0) or 0) > 0:
                rows.append(unscheduled(r, "retired"))
        else:
            rows.append(unscheduled(r, "on_demand"))
    return rows


def get_jobs_over_time(db: Session, days: int = 14) -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        text(
            "SELECT DATE(scraped_at) AS d, COUNT(*) AS c FROM raw_job_postings "
            "WHERE scraped_at >= :cutoff GROUP BY DATE(scraped_at)"
        ),
        {"cutoff": cutoff},
    ).all()
    counts = {r.d.isoformat(): int(r.c) for r in rows}
    today = datetime.now(UTC).date()
    return [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "count": counts.get((today - timedelta(days=i)).isoformat(), 0),
        }
        for i in range(days - 1, -1, -1)
    ]


def get_jobs_by_source(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text("SELECT source, COUNT(*) AS c FROM raw_job_postings GROUP BY source ORDER BY c DESC")
    ).all()
    return [{"source": r.source, "count": int(r.c)} for r in rows]


def get_latest_market_metrics(db: Session) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT metric_date, total_jobs_scraped, top_skills, top_companies, remote_percentage "
            "FROM job_market_metrics ORDER BY metric_date DESC, created_at DESC LIMIT 1"
        )
    ).first()
    if row is None:
        return None
    top_skills = [
        {"skill": s.get("skill", ""), "count": int(s.get("count", 0))}
        for s in (row.top_skills or [])
        if isinstance(s, dict)
    ]
    top_companies = [
        {"company": c.get("company", ""), "count": int(c.get("count", 0))}
        for c in (row.top_companies or [])
        if isinstance(c, dict)
    ]
    return {
        "metric_date": row.metric_date,
        "total_jobs_scraped": row.total_jobs_scraped,
        "remote_percentage": float(row.remote_percentage) if row.remote_percentage is not None else None,
        "top_skills": top_skills,
        "top_companies": top_companies,
    }
