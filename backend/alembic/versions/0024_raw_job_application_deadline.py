"""add raw_job_postings.application_deadline

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-03

- Discover "For You" feed should hide jobs whose application deadline has
  passed. Only Platsbanken ads carry a real deadline today
  (last_application_date, buried in raw_data JSONB) — the_muse/remotive have
  no equivalent field. Backfill existing Platsbanken rows from raw_data;
  everything else gets NULL, which the feed filter treats as "still live"
  since we can't positively say it expired.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_job_postings",
        sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE raw_job_postings
        SET application_deadline = (raw_data->>'last_application_date')::timestamptz
        WHERE source = 'platsbanken'
          AND raw_data->>'last_application_date' IS NOT NULL
          AND raw_data->>'last_application_date' != ''
        """
    )
    op.create_index(
        "ix_raw_job_postings_application_deadline",
        "raw_job_postings",
        ["application_deadline"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_job_postings_application_deadline", table_name="raw_job_postings")
    op.drop_column("raw_job_postings", "application_deadline")
