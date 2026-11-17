"""fill the applied date of cards that are in an applied stage without one

Revision ID: 0038
Revises: 0037

Dragging a card to Applied (or accepting an email suggestion) changed only the
status, so the card showed "Not applied" while sitting in the Applied column,
and it was invisible to the "sent per day" stats. The code now stamps the date
when a card enters an applied stage; this fills in the ones already stored.

The date used is when the card first entered an applied stage (its first
status-change event), else when it was created. That is the best record there
is, not a guess at when the application was really sent: change it on the card
if it is wrong. Only empty dates are touched.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE applications a
        SET applied_date = date_trunc(
            'day',
            COALESCE(
                (
                    SELECT MIN(e.event_date)
                    FROM application_events e
                    WHERE e.application_id = a.id
                      AND e.event_type = 'status_changed'
                      AND e.new_value IN ('applied', 'phone_screen', 'interview', 'offer')
                ),
                a.created_at
            ) AT TIME ZONE 'UTC'
        ) AT TIME ZONE 'UTC'
        WHERE a.applied_date IS NULL
          AND a.status IN ('applied', 'phone_screen', 'interview', 'offer')
        """
    )


def downgrade() -> None:
    # The original values were empty and cannot be told apart from dates the
    # user set afterwards, so there is nothing safe to undo.
    pass
