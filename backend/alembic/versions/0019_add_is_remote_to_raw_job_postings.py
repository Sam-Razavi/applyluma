"""add is_remote to raw_job_postings

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE raw_job_postings ADD COLUMN IF NOT EXISTS is_remote BOOLEAN DEFAULT FALSE"
    )
    op.execute("UPDATE raw_job_postings SET is_remote = FALSE WHERE is_remote IS NULL")
    op.execute("UPDATE raw_job_postings SET is_remote = TRUE WHERE source = 'remotive'")
    op.execute(
        "UPDATE raw_job_postings SET is_remote = TRUE WHERE LOWER(location) LIKE '%remote%'"
    )
    op.execute("ALTER TABLE raw_job_postings ALTER COLUMN is_remote SET DEFAULT FALSE")
    op.execute("ALTER TABLE raw_job_postings ALTER COLUMN is_remote SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE raw_job_postings DROP COLUMN IF EXISTS is_remote")
