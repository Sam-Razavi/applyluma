"""enforce at-most-one default CV per user

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-07

Adds a partial unique index so the database rejects any attempt to set a
second CV as default for the same user, catching edge-case race conditions
that the application-layer atomic UPDATE cannot fully prevent under
READ COMMITTED isolation.

The cleanup CTE below runs first to resolve any pre-existing violations by
keeping only the most recently created default CV per user.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Resolve any pre-existing violations before creating the unique index.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id
                       ORDER BY created_at DESC
                   ) AS rn
            FROM cvs
            WHERE is_default = TRUE
        )
        UPDATE cvs
        SET is_default = FALSE
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_cvs_one_default_per_user ON cvs (user_id) WHERE is_default = TRUE"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_cvs_one_default_per_user")
