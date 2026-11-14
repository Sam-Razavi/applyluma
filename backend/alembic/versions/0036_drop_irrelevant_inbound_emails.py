"""delete stored inbound emails that are not about a job application

Revision ID: 0036
Revises: 0035

Until now every forwarded email was stored, so inboxes filled with newsletters,
receipts and delivery notices. New mail of that kind is no longer stored
(services/inbound_email/relevance.py); this removes what is already there.

Only rows nobody acted on are touched (suggestion_state 'none', no decision
detected). Gmail's forwarding confirmation is kept: Settings reads its code.
The headers of old rows were never stored, so "bulk" is judged from the sender
and the text alone.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from app.services.inbound_email.forwarded import is_gmail_confirmation
    from app.services.inbound_email.relevance import is_job_related, looks_bulk

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, from_address, from_domain, subject, snippet, matched_application_id
            FROM inbound_emails
            WHERE suggestion_state = 'none' AND classification IS NULL
            """
        )
    ).mappings().all()

    doomed = []
    for row in rows:
        if is_gmail_confirmation(row["from_address"]):
            continue
        keep, _ = is_job_related(
            subject=row["subject"],
            snippet=row["snippet"],
            from_domain=row["from_domain"],
            classification=None,
            matched=row["matched_application_id"] is not None,
            bulk=looks_bulk(headers={}, from_address=row["from_address"], snippet=row["snippet"]),
        )
        if not keep:
            doomed.append(row["id"])

    for row_id in doomed:
        bind.execute(sa.text("DELETE FROM inbound_emails WHERE id = :id"), {"id": row_id})


def downgrade() -> None:
    # Deleted mail cannot be restored.
    pass
