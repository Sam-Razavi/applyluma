"""add applications.stale_reminder_sent + missing hot-path indexes

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-02

- applications.stale_reminder_sent — check_stale_applications previously
  re-notified users about the same stale application on every daily run;
  this flag makes the reminder one-shot (mirrors deadline_reminder_sent).
- raw_job_postings.url index — get_raw_job_by_url() runs on every browser
  extension bookmark and was a sequential scan.
- job_matching_scores.raw_job_posting_id index — backs the correlated
  NOT EXISTS subquery in notify_high_match_jobs and joins by job id.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("stale_reminder_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_raw_job_postings_url", "raw_job_postings", ["url"])
    op.create_index(
        "ix_job_matching_scores_raw_job_posting_id",
        "job_matching_scores",
        ["raw_job_posting_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_matching_scores_raw_job_posting_id", table_name="job_matching_scores")
    op.drop_index("ix_raw_job_postings_url", table_name="raw_job_postings")
    op.drop_column("applications", "stale_reminder_sent")
