"""add preferred_template column to users

Revision ID: 0030
Revises: 0029

Stores the user's default CV template (nordic/classic/modern/executive).
NULL means the application default (nordic). Used as the starting template
in AI Tailor and editable from the Settings page.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferred_template", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferred_template")
