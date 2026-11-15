"""mark job postings that a user saved from the browser extension

Revision ID: 0037
Revises: 0036

A job saved with the extension is stored as a posting so it can be scored and
tailored against. Those rows were indistinguishable from scraped ones, so one
user's saved page showed up in every user's Discover feed, in the source
filter, in alerts and in the market analytics. The flag keeps them out of
everything shared; the user still reaches the job through their saved jobs.

Existing rows are recognised by their external id: the extension stores the
page URL there, a scraper stores the job board's own id.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_job_postings",
        sa.Column("user_submitted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE raw_job_postings SET user_submitted = true "
        "WHERE job_id_external = left(url, 255) AND job_id_external LIKE 'http%'"
    )


def downgrade() -> None:
    op.drop_column("raw_job_postings", "user_submitted")
