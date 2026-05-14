"""admin user status and task applications

Revision ID: 0003_admin_user_status_and_task_applications
Revises: 0002_add_user_profile_image
Create Date: 2026-05-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "task_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_application_user"),
    )
    op.create_index(op.f("ix_task_applications_task_id"), "task_applications", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_applications_user_id"), "task_applications", ["user_id"], unique=False)
    op.alter_column("users", "is_active", server_default=None)
    op.alter_column("users", "is_deleted", server_default=None)


def downgrade():
    op.drop_index(op.f("ix_task_applications_user_id"), table_name="task_applications")
    op.drop_index(op.f("ix_task_applications_task_id"), table_name="task_applications")
    op.drop_table("task_applications")
    op.drop_column("users", "is_deleted")
    op.drop_column("users", "is_active")
