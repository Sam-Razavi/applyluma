"""Admin database statistics: per-table rows, sizes and growth."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.admin_audit_log import AdminAuditLog
from app.models.ai_usage_log import AIUsageLog
from app.models.application import Application
from app.models.contact_submission import ContactSubmission
from app.models.cover_letter_job import CoverLetterJob
from app.models.cv import CV
from app.models.job import SavedJob
from app.models.job_description import JobDescription
from app.models.notification import Notification
from app.models.tailor_job import TailorJob
from app.models.user import User

# Fixed allowlist of tables whose growth can be measured via created_at.
# Never derived from client input — the stats endpoint takes no parameters.
_GROWTH_TABLES: dict[str, Any] = {}


def _growth_tables() -> dict[str, Any]:
    # Lazy import to avoid circulars at module import time.
    if not _GROWTH_TABLES:
        from app.models.job import RawJobPosting

        _GROWTH_TABLES.update(
            {
                "users": (User, User.created_at),
                "cvs": (CV, CV.created_at),
                "job_descriptions": (JobDescription, JobDescription.created_at),
                "tailor_jobs": (TailorJob, TailorJob.created_at),
                "cover_letter_jobs": (CoverLetterJob, CoverLetterJob.created_at),
                "applications": (Application, Application.created_at),
                "saved_jobs": (SavedJob, SavedJob.created_at),
                "notifications": (Notification, Notification.created_at),
                "raw_job_postings": (RawJobPosting, RawJobPosting.scraped_at),
                "ai_usage_logs": (AIUsageLog, AIUsageLog.created_at),
                "contact_submissions": (ContactSubmission, ContactSubmission.created_at),
                "admin_audit_log": (AdminAuditLog, AdminAuditLog.created_at),
            }
        )
    return _GROWTH_TABLES


def get_database_stats(db: Session) -> dict[str, Any]:
    db_size = int(db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0)
    rows = db.execute(
        text(
            "SELECT c.relname AS table_name, "
            "GREATEST(c.reltuples, 0)::bigint AS approx_row_count, "
            "pg_total_relation_size(c.oid) AS total_bytes "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' "
            "ORDER BY pg_total_relation_size(c.oid) DESC"
        )
    ).mappings().all()

    now = datetime.now(UTC)
    growth: dict[str, tuple[int, int]] = {}
    for table_name, (model, ts_column) in _growth_tables().items():
        rows_7d = db.scalar(
            select(func.count()).select_from(model).where(ts_column >= now - timedelta(days=7))
        ) or 0
        rows_30d = db.scalar(
            select(func.count()).select_from(model).where(ts_column >= now - timedelta(days=30))
        ) or 0
        growth[table_name] = (int(rows_7d), int(rows_30d))

    tables = []
    for r in rows:
        g = growth.get(r["table_name"])
        tables.append(
            {
                "table_name": r["table_name"],
                "approx_row_count": int(r["approx_row_count"]),
                "total_bytes": int(r["total_bytes"]),
                "rows_7d": g[0] if g else None,
                "rows_30d": g[1] if g else None,
            }
        )
    return {"database_size_bytes": db_size, "tables": tables, "generated_at": now}
