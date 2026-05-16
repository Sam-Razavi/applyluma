"""application_raw_job_link

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_applications_raw_job_posting_id",
        "applications",
        "raw_job_postings",
        ["raw_job_posting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_applications_raw_job",
        "applications",
        ["user_id", "raw_job_posting_id"],
    )
    op.create_index(
        "uq_app_user_raw_job",
        "applications",
        ["user_id", "raw_job_posting_id"],
        unique=True,
        postgresql_where=sa.text("raw_job_posting_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_app_user_raw_job", table_name="applications")
    op.drop_index("idx_applications_raw_job", table_name="applications")
    op.drop_constraint("fk_applications_raw_job_posting_id", "applications", type_="foreignkey")
    op.drop_column("applications", "raw_job_posting_id")
