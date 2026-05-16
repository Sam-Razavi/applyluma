"""user_alert_preferences

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_alert_preferences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score_threshold", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("frequency", sa.String(16), nullable=False, server_default="daily"),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_alert_preferences_user"),
    )
    op.create_index("idx_user_alert_preferences_enabled", "user_alert_preferences", ["enabled"])

    op.create_table(
        "job_alert_sent_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["raw_job_posting_id"], ["raw_job_postings.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("user_id", "raw_job_posting_id", name="uq_job_alert_sent_user_job"),
    )
    op.create_index("idx_job_alert_sent_log_user", "job_alert_sent_log", ["user_id", "sent_at"])


def downgrade() -> None:
    op.drop_index("idx_job_alert_sent_log_user", table_name="job_alert_sent_log")
    op.drop_table("job_alert_sent_log")
    op.drop_index("idx_user_alert_preferences_enabled", table_name="user_alert_preferences")
    op.drop_table("user_alert_preferences")
