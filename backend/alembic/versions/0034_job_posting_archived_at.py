"""add archived_at to raw_job_postings

Revision ID: 0034
Revises: 0033

Retention for scraped job ads. A daily task archives postings whose deadline
has passed or that are older than 30 days: they disappear from every
user-facing job surface, and for postings nobody saved or applied to, the
bulky description/raw_data, keywords and match scores are dropped. Archived
rows are deleted outright 90 days later. The slim row is kept that long
because the scrapers insert with ON CONFLICT (source, job_id_external) DO
NOTHING: deleting an ad that is still listed at its source would let the
next scrape re-insert it as a brand-new job.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_job_postings",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_raw_job_postings_archived_at", "raw_job_postings", ["archived_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_raw_job_postings_archived_at", table_name="raw_job_postings")
    op.drop_column("raw_job_postings", "archived_at")
