"""add fit_assessments

Revision ID: 0035
Revises: 0034

Stores AI-assisted job-fit assessments (thesis component, thesis/DESIGN.md):
the recommendation the decision rules produced, the model's own suggestion,
the full output, and the model, prompt and rules versions that produced it.

raw_job_posting_id is ON DELETE SET NULL so the retention task can still
delete old postings.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fit_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cv_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cvs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "raw_job_posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_job_postings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("job_title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.String(20), nullable=True),
        sa.Column("model_recommendation", sa.String(20), nullable=True),
        sa.Column("limited_information", sa.Boolean(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(16), nullable=False),
        sa.Column("rules_version", sa.String(16), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_fit_assessments_user_id", "fit_assessments", ["user_id"])
    op.create_index("ix_fit_assessments_input_hash", "fit_assessments", ["input_hash"])
    op.create_index(
        "ix_fit_assessments_user_posting",
        "fit_assessments",
        ["user_id", "raw_job_posting_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("fit_assessments")
