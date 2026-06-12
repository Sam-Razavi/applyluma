"""add composite performance indexes

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-12

Adds three composite indexes missing from earlier migrations:

- applications(user_id, status)     — every kanban/list query filters on both
- tailor_jobs(user_id, created_at)  — count_today() filters user + time range
- raw_job_postings(is_duplicate)    — list_jobs() always filters is_duplicate=false
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_applications_user_id_status", "applications", ["user_id", "status"])
    op.create_index("ix_tailor_jobs_user_id_created_at", "tailor_jobs", ["user_id", "created_at"])
    op.create_index("ix_raw_job_postings_is_duplicate", "raw_job_postings", ["is_duplicate"])


def downgrade() -> None:
    op.drop_index("ix_raw_job_postings_is_duplicate", table_name="raw_job_postings")
    op.drop_index("ix_tailor_jobs_user_id_created_at", table_name="tailor_jobs")
    op.drop_index("ix_applications_user_id_status", table_name="applications")
