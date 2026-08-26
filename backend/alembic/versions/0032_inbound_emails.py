"""add inbound_emails table and users.inbox_token

Revision ID: 0032
Revises: 0031

Inbound email ingestion: users forward job-related mail to a unique per-user
address, u-{inbox_token}@{INBOUND_EMAIL_DOMAIN}, and an inbound-parse vendor
POSTs the parsed message to the webhook. Each accepted message becomes an
inbound_emails row carrying the match decision against the user's applications.

Only metadata plus a truncated snippet is stored — never a full body — and the
CASCADE on user_id means account deletion erases the lot.

inbox_token is backfilled for existing users so every account has a working
address the moment the feature is enabled.
"""
import secrets
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("inbox_token", sa.String(length=64), nullable=True))
    # The unique constraint supplies the index the recipient lookup needs, so
    # no separate one is created.
    op.create_unique_constraint("uq_users_inbox_token", "users", ["inbox_token"])

    # Backfill existing accounts. Done row by row because each token must be
    # distinct — there is no set-based way to generate per-row secrets.
    # Skipped when generating SQL offline, where there is no connection to read
    # from; those rows keep a NULL token and get one lazily from
    # crud_user.ensure_inbox_token instead.
    if not context.is_offline_mode():
        connection = op.get_bind()
        user_ids = connection.execute(
            sa.text("SELECT id FROM users WHERE inbox_token IS NULL")
        ).fetchall()
        for (user_id,) in user_ids:
            connection.execute(
                sa.text("UPDATE users SET inbox_token = :token WHERE id = :id"),
                {"token": secrets.token_hex(16), "id": user_id},
            )

    op.create_table(
        "inbound_emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("message_id", sa.String(length=512), nullable=True),
        sa.Column("from_address", sa.String(length=320), nullable=False),
        sa.Column("from_domain", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched_application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_confidence", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("match_method", sa.String(length=50), server_default="none", nullable=False),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("vendor", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_application_id"], ["applications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_inbound_emails_user_dedupe"),
    )
    op.create_index("ix_inbound_emails_user_id", "inbound_emails", ["user_id"])
    op.create_index("ix_inbound_emails_from_domain", "inbound_emails", ["from_domain"])
    op.create_index(
        "ix_inbound_emails_matched_application_id", "inbound_emails", ["matched_application_id"]
    )
    op.create_index("ix_inbound_emails_user_created", "inbound_emails", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_inbound_emails_user_created", table_name="inbound_emails")
    op.drop_index("ix_inbound_emails_matched_application_id", table_name="inbound_emails")
    op.drop_index("ix_inbound_emails_from_domain", table_name="inbound_emails")
    op.drop_index("ix_inbound_emails_user_id", table_name="inbound_emails")
    op.drop_table("inbound_emails")

    op.drop_constraint("uq_users_inbox_token", "users", type_="unique")
    op.drop_column("users", "inbox_token")
