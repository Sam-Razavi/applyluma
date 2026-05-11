"""add user role

Revision ID: b5d9f3c2e1a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b5d9f3c2e1a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLE = postgresql.ENUM(
    "user",
    "admin",
    "premium",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('user', 'admin', 'premium')")
    op.add_column(
        "users",
        sa.Column(
            "role",
            USER_ROLE,
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    op.execute("DROP TYPE user_role")
