"""add job_description keywords

Revision ID: f6b2c8d4e1a5
Revises: d4f8e2b1c9a3
Create Date: 2026-05-05 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6b2c8d4e1a5"
down_revision: Union[str, None] = "d4f8e2b1c9a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_descriptions",
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("job_descriptions", "keywords")
