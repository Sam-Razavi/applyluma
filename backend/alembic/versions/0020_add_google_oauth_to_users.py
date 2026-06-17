"""add google oauth to users

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = '0020'
down_revision = '0019'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(), nullable=True, server_default='local'))
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    op.alter_column('users', 'hashed_password', nullable=True)


def downgrade():
    op.alter_column('users', 'hashed_password', nullable=False)
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'google_id')
