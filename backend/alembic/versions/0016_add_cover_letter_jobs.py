"""add_cover_letter_jobs

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-23
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cover_letter_jobs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cv_id", sa.UUID(as_uuid=True), sa.ForeignKey("cvs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_description_id", sa.UUID(as_uuid=True), sa.ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tone", sa.Enum("formal", "friendly", "concise", name="cover_letter_tone"), nullable=False, server_default="formal"),
        sa.Column("status", sa.Enum("pending", "processing", "complete", "failed", name="cover_letter_status"), nullable=False, server_default="pending"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("generated_text", sa.Text, nullable=True),
        sa.Column("saved_text", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("word_count", sa.Integer, nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("is_saved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cover_letter_jobs")
    op.execute("DROP TYPE IF EXISTS cover_letter_tone")
    op.execute("DROP TYPE IF EXISTS cover_letter_status")
