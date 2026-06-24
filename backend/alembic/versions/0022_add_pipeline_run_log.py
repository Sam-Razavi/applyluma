"""add pipeline_run_log table

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-24
"""
import sqlalchemy as sa

from alembic import op

revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'pipeline_run_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pipeline_name', sa.String(length=100), nullable=False),
        sa.Column('ran_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('rows_affected', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='success', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_pipeline_run_log_name_ran_at',
        'pipeline_run_log',
        ['pipeline_name', sa.text('ran_at DESC')],
    )


def downgrade() -> None:
    op.drop_index('ix_pipeline_run_log_name_ran_at', table_name='pipeline_run_log')
    op.drop_table('pipeline_run_log')
