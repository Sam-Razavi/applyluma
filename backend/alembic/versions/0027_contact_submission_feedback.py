"""add feedback fields to contact_submissions

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-09

The in-app feedback form stores into contact_submissions alongside the public
contact form, so the admin Contact inbox becomes one shared inbox. New columns:
- user_id: who sent it (NULL for anonymous public contact submissions)
- category: bug | feature | question | other (in-app) or 'contact' (public form)
- source: 'in_app' | 'contact'
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contact_submissions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "contact_submissions",
        sa.Column("category", sa.String(length=20), nullable=False, server_default="contact"),
    )
    op.add_column(
        "contact_submissions",
        sa.Column("source", sa.String(length=16), nullable=False, server_default="contact"),
    )
    op.create_foreign_key(
        "fk_contact_submissions_user_id",
        "contact_submissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_contact_submissions_user_id", "contact_submissions", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_contact_submissions_user_id", table_name="contact_submissions")
    op.drop_constraint(
        "fk_contact_submissions_user_id", "contact_submissions", type_="foreignkey"
    )
    op.drop_column("contact_submissions", "source")
    op.drop_column("contact_submissions", "category")
    op.drop_column("contact_submissions", "user_id")
