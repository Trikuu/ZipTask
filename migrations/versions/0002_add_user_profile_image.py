"""add user profile image

Revision ID: 0002_add_user_profile_image
Revises: 0001_initial_schema
Create Date: 2026-05-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_add_user_profile_image"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("profile_image", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("users", "profile_image")
