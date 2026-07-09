"""add ai_usage_logs and app_settings tables

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-09

AI cost tracking: one ai_usage_logs row per OpenAI call (purpose, model,
tokens, computed USD cost, optional user attribution). app_settings is a
small key-value table holding the admin-configurable monthly AI budget and
the budget-alert throttle state.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=40), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("ix_ai_usage_logs_purpose", "ai_usage_logs", ["purpose"])
    op.create_index("ix_ai_usage_logs_created_at", "ai_usage_logs", ["created_at"])

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_ai_usage_logs_created_at", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_purpose", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_logs_user_id", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
