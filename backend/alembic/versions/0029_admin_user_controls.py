"""add login tracking and tailor-limit override columns to users

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-11

Admin control-center additions: last_login_at / login_count are updated on
every successful login (password, OAuth2 form, Google) and surfaced in the
admin user list and profile drawer. daily_tailor_limit_override lets an
admin supersede the role-based daily tailoring limit for a single user
(NULL = role default, 0 = blocked, N = that many per day).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("daily_tailor_limit_override", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "daily_tailor_limit_override")
    op.drop_column("users", "login_count")
    op.drop_column("users", "last_login_at")
