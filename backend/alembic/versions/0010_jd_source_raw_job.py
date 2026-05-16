"""jd_source_raw_job

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_descriptions",
        sa.Column("source_raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_job_descriptions_source_raw_job_posting_id",
        "job_descriptions",
        "raw_job_postings",
        ["source_raw_job_posting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_jd_user_raw_job",
        "job_descriptions",
        ["user_id", "source_raw_job_posting_id"],
        unique=True,
        postgresql_where=sa.text("source_raw_job_posting_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_jd_user_raw_job", table_name="job_descriptions")
    op.drop_constraint(
        "fk_job_descriptions_source_raw_job_posting_id",
        "job_descriptions",
        type_="foreignkey",
    )
    op.drop_column("job_descriptions", "source_raw_job_posting_id")
