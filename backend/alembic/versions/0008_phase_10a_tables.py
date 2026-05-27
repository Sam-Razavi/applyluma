"""phase_10a_tables - saved_jobs, extracted_keywords, job_matching_scores

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "saved_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("list_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("starred", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["raw_job_posting_id"], ["raw_job_postings.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "raw_job_posting_id", name="uq_saved_jobs_user_job"),
    )
    op.create_index("idx_saved_jobs_user_created", "saved_jobs", ["user_id", "created_at"])
    op.create_index("idx_saved_jobs_starred", "saved_jobs", ["user_id", "starred"])

    op.create_table(
        "extracted_keywords",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("keyword_type", sa.String(50), nullable=False),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "frequency",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["raw_job_posting_id"], ["raw_job_postings.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "raw_job_posting_id",
            "keyword",
            "keyword_type",
            name="uq_extracted_keywords_job_kw_type",
        ),
    )
    op.create_index("idx_extracted_keywords_job", "extracted_keywords", ["raw_job_posting_id"])
    op.create_index("idx_extracted_keywords_type", "extracted_keywords", ["keyword_type"])

    op.create_table(
        "job_matching_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("skills_match", sa.Float(), nullable=True),
        sa.Column("experience_match", sa.Float(), nullable=True),
        sa.Column("salary_match", sa.Float(), nullable=True),
        sa.Column("education_match", sa.Float(), nullable=True),
        sa.Column("location_match", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "cached_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["raw_job_posting_id"], ["raw_job_postings.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "user_id",
            "raw_job_posting_id",
            name="uq_job_matching_scores_user_job",
        ),
    )
    op.create_index(
        "idx_job_matching_scores_user_score",
        "job_matching_scores",
        ["user_id", "overall_score"],
    )
    op.create_index(
        "idx_job_matching_scores_computed",
        "job_matching_scores",
        ["computed_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_job_matching_scores_computed", table_name="job_matching_scores")
    op.drop_index("idx_job_matching_scores_user_score", table_name="job_matching_scores")
    op.drop_table("job_matching_scores")
    op.drop_index("idx_extracted_keywords_type", table_name="extracted_keywords")
    op.drop_index("idx_extracted_keywords_job", table_name="extracted_keywords")
    op.drop_table("extracted_keywords")
    op.drop_index("idx_saved_jobs_starred", table_name="saved_jobs")
    op.drop_index("idx_saved_jobs_user_created", table_name="saved_jobs")
    op.drop_table("saved_jobs")
