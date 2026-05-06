"""add job market tables

Revision ID: a1b2c3d4e5f6
Revises: f6b2c8d4e1a5
Create Date: 2026-05-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f6b2c8d4e1a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("job_id_external", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("employment_type", sa.String(64), nullable=True),
        sa.Column("remote_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("extracted_skills", postgresql.JSONB(), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "job_id_external", name="uq_raw_job_postings_source_external_id"),
    )
    op.create_index("ix_raw_job_postings_source", "raw_job_postings", ["source"])
    op.create_index("ix_raw_job_postings_scraped_at", "raw_job_postings", ["scraped_at"])
    op.create_index("ix_raw_job_postings_company", "raw_job_postings", ["company"])

    op.create_table(
        "job_market_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("metric_date", sa.Date(), nullable=False, unique=True),
        sa.Column("total_jobs_scraped", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("top_companies", postgresql.JSONB(), nullable=True),
        sa.Column("top_skills", postgresql.JSONB(), nullable=True),
        sa.Column("avg_salary_range", postgresql.JSONB(), nullable=True),
        sa.Column("remote_percentage", sa.Float(), nullable=True),
        sa.Column("employment_type_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_job_market_metrics_date", "job_market_metrics", ["metric_date"])


def downgrade() -> None:
    op.drop_table("job_market_metrics")
    op.drop_index("ix_raw_job_postings_company", "raw_job_postings")
    op.drop_index("ix_raw_job_postings_scraped_at", "raw_job_postings")
    op.drop_index("ix_raw_job_postings_source", "raw_job_postings")
    op.drop_table("raw_job_postings")
