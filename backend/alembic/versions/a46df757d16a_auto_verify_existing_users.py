"""auto-verify all existing users

Revision ID: a46df757d16a
Revises: f6b2c8d4e1a5
Create Date: 2026-05-31 00:00:00.000000

One-time data migration: marks every existing unverified user as verified
so that the new email-verification gate does not lock out anyone who
registered before enforcement was introduced.
"""
from alembic import op

revision = "a46df757d16a"
down_revision = "f6b2c8d4e1a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET is_verified = true WHERE is_verified = false")


def downgrade() -> None:
    pass  # irreversible — do not un-verify users on rollback
