"""add linkedin_id and github_id columns to users

Revision ID: 0031
Revises: 0030

Multi-provider login: LinkedIn and GitHub OAuth mirror the existing
google_id column — unique nullable provider user ids used by
crud_user.upsert_oauth_user for lookup and account linking.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("linkedin_id", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("github_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_users_linkedin_id", "users", ["linkedin_id"])
    op.create_unique_constraint("uq_users_github_id", "users", ["github_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_github_id", "users", type_="unique")
    op.drop_constraint("uq_users_linkedin_id", "users", type_="unique")
    op.drop_column("users", "github_id")
    op.drop_column("users", "linkedin_id")
