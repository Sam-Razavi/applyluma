"""merge saved jobs into job descriptions

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa

revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add new columns to job_descriptions
    op.add_column(
        'job_descriptions',
        sa.Column('starred', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'job_descriptions',
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.add_column(
        'job_descriptions',
        sa.Column('list_name', sa.String(255), nullable=True),
    )

    # 2. For existing JDs that have a matching saved_job (same user + raw_job),
    #    update their starred, notes, and list_name from saved_jobs.
    op.execute("""
        UPDATE job_descriptions jd
        SET starred   = sj.starred,
            notes     = sj.notes,
            list_name = sj.list_name
        FROM saved_jobs sj
        WHERE jd.user_id = sj.user_id
          AND jd.source_raw_job_posting_id = sj.raw_job_posting_id
          AND jd.source_raw_job_posting_id IS NOT NULL
    """)

    # 3. Insert new JDs from saved_jobs that don't already have a matching JD
    #    for that user + raw_job_posting combination.
    op.execute("""
        INSERT INTO job_descriptions (
            id, user_id, source_raw_job_posting_id,
            company_name, job_title, description, url,
            keywords, starred, notes, list_name,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            sj.user_id,
            sj.raw_job_posting_id,
            rjp.company,
            rjp.title,
            rjp.description,
            rjp.url,
            '{}'::varchar[],
            sj.starred,
            sj.notes,
            sj.list_name,
            sj.created_at,
            sj.updated_at
        FROM saved_jobs sj
        JOIN raw_job_postings rjp ON rjp.id = sj.raw_job_posting_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM job_descriptions jd
            WHERE jd.user_id = sj.user_id
              AND jd.source_raw_job_posting_id = sj.raw_job_posting_id
        )
    """)


def downgrade():
    op.drop_column('job_descriptions', 'list_name')
    op.drop_column('job_descriptions', 'notes')
    op.drop_column('job_descriptions', 'starred')
