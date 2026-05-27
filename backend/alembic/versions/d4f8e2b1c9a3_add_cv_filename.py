"""add cv filename

Revision ID: d4f8e2b1c9a3
Revises: c3e7b4a91f20
Create Date: 2026-05-05 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4f8e2b1c9a3"
down_revision: Union[str, None] = "c3e7b4a91f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add as nullable first so any pre-existing rows don't violate the constraint,
    # then backfill and tighten to non-nullable.
    op.add_column("cvs", sa.Column("filename", sa.String(255), nullable=True))
    op.execute("UPDATE cvs SET filename = title WHERE filename IS NULL")
    op.alter_column("cvs", "filename", nullable=False)


def downgrade() -> None:
    op.drop_column("cvs", "filename")
