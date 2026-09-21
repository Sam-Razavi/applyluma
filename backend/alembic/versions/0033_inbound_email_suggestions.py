"""add classification and suggestion columns to inbound_emails

Revision ID: 0033
Revises: 0032

Second slice of inbound email: once a message is matched to an application, it
is also classified (rejection / interview / offer / acknowledged) and, when the
classification is confident enough, raised to the user as a suggestion to move
that application's status.

Nothing applies automatically. suggestion_state tracks the user's decision and
doubles as the guard that stops one email prompting twice.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("inbound_emails", sa.Column("classification", sa.String(length=32), nullable=True))
    op.add_column(
        "inbound_emails",
        sa.Column(
            "classification_confidence", sa.SmallInteger(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "inbound_emails", sa.Column("suggested_status", sa.String(length=50), nullable=True)
    )
    op.add_column("inbound_emails", sa.Column("evidence", sa.Text(), nullable=True))
    op.add_column(
        "inbound_emails",
        sa.Column("suggestion_state", sa.String(length=16), server_default="none", nullable=False),
    )
    # The pending-suggestions list is read per user on every Applications page
    # load, so it gets its own index rather than scanning the user's mail.
    op.create_index(
        "ix_inbound_emails_user_suggestion_state",
        "inbound_emails",
        ["user_id", "suggestion_state"],
    )


def downgrade() -> None:
    op.drop_index("ix_inbound_emails_user_suggestion_state", table_name="inbound_emails")
    op.drop_column("inbound_emails", "suggestion_state")
    op.drop_column("inbound_emails", "evidence")
    op.drop_column("inbound_emails", "suggested_status")
    op.drop_column("inbound_emails", "classification_confidence")
    op.drop_column("inbound_emails", "classification")
