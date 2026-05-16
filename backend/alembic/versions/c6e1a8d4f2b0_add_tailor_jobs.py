"""add tailor_jobs table and cv tailoring columns

Revision ID: c6e1a8d4f2b0
Revises: b5d9f3c2e1a7
Create Date: 2026-05-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c6e1a8d4f2b0"
down_revision: str | None = "b5d9f3c2e1a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TAILOR_STATUS = postgresql.ENUM(
    "pending",
    "processing",
    "complete",
    "failed",
    name="tailor_status",
    create_type=False,
)
TAILOR_INTENSITY = postgresql.ENUM(
    "light",
    "medium",
    "aggressive",
    name="tailor_intensity",
    create_type=False,
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute("CREATE TYPE tailor_status AS ENUM ('pending', 'processing', 'complete', 'failed')")
    op.execute("CREATE TYPE tailor_intensity AS ENUM ('light', 'medium', 'aggressive')")

    op.create_table(
        "tailor_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cv_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_description_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intensity", TAILOR_INTENSITY, nullable=False, server_default="medium"),
        sa.Column("status", TAILOR_STATUS, nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("output_cv_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cv_id"], ["cvs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["job_description_id"], ["job_descriptions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["output_cv_id"], ["cvs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tailor_jobs_user_id", "tailor_jobs", ["user_id"])

    op.add_column(
        "cvs",
        sa.Column("is_tailored", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "cvs",
        sa.Column("parent_cv_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "cvs",
        sa.Column("tailor_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cvs_parent_cv_id_cvs",
        "cvs",
        "cvs",
        ["parent_cv_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_cvs_tailor_job_id_tailor_jobs",
        "cvs",
        "tailor_jobs",
        ["tailor_job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_cvs_tailor_job_id_tailor_jobs", "cvs", type_="foreignkey")
    op.drop_constraint("fk_cvs_parent_cv_id_cvs", "cvs", type_="foreignkey")
    op.drop_column("cvs", "tailor_job_id")
    op.drop_column("cvs", "parent_cv_id")
    op.drop_column("cvs", "is_tailored")
    op.drop_index("ix_tailor_jobs_user_id", table_name="tailor_jobs")
    op.drop_table("tailor_jobs")
    op.execute("DROP TYPE tailor_intensity")
    op.execute("DROP TYPE tailor_status")
