"""add missing user fields

Revision ID: 16f20619cd60
Revises: 
Create Date: 2026-05-14 20:59:40.050505
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('full_name', sa.String(120)),
        sa.Column('email', sa.String(120), unique=True),
        sa.Column('phone', sa.String(20), unique=True),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('profile_image', sa.String(255)),
        sa.Column('role', sa.String(20)),
        sa.Column('is_active', sa.Boolean()),
        sa.Column('is_deleted', sa.Boolean()),
        sa.Column('is_frozen', sa.Boolean()),
        sa.Column('has_pending_dues', sa.Boolean()),
        sa.Column('created_at', sa.DateTime())
    )


def downgrade():
    pass
