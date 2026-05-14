"""manual migration

Revision ID: 0e10d5b9aeb3
Revises: 0002_add_user_profile_image
Create Date: 2026-05-14 18:50:47.931151
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002_add_user_profile_image'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('is_frozen', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('has_pending_dues', sa.Boolean(), nullable=True))

def downgrade():
    op.drop_column('users', 'is_frozen')
    op.drop_column('users', 'has_pending_dues')