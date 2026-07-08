"""add contact submissions table

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column("remote_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contact_submissions_created_at", "contact_submissions", ["created_at"])
    op.create_index("ix_contact_submissions_email", "contact_submissions", ["email"])
    op.create_index("ix_contact_submissions_status", "contact_submissions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_contact_submissions_status", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_email", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_created_at", table_name="contact_submissions")
    op.drop_table("contact_submissions")
