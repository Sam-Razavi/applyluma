"""add missing foreign-key indexes

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-07

Adds indexes that were absent from the tables created in earlier migrations:

- tailor_jobs.job_description_id  — lookups and deduplication checks in 10B
- tailor_jobs.cv_id               — listing tailor jobs for a given CV
- cvs.parent_cv_id                — recursive version-tree queries
- saved_jobs.raw_job_posting_id   — efficient CASCADE deletes from raw_job_postings
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "a46df757d16a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_tailor_jobs_job_description_id", "tailor_jobs", ["job_description_id"])
    op.create_index("ix_tailor_jobs_cv_id", "tailor_jobs", ["cv_id"])
    op.create_index("ix_cvs_parent_cv_id", "cvs", ["parent_cv_id"])
    op.create_index("ix_saved_jobs_raw_job_posting_id", "saved_jobs", ["raw_job_posting_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_jobs_raw_job_posting_id", table_name="saved_jobs")
    op.drop_index("ix_cvs_parent_cv_id", table_name="cvs")
    op.drop_index("ix_tailor_jobs_cv_id", table_name="tailor_jobs")
    op.drop_index("ix_tailor_jobs_job_description_id", table_name="tailor_jobs")
