"""chat negotiation proof and dues

Revision ID: 0004_chat_negotiation_proof_and_dues
Revises: 0003_task_app
Create Date: 2026-05-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_chat_negotiation_proof_and_dues"
down_revision = "0003_task_app"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("has_pending_dues", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tasks", sa.Column("agreed_price", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("tasks", sa.Column("proposed_price", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("tasks", sa.Column("negotiation_status", sa.String(length=30), nullable=False, server_default="NONE"))
    op.add_column("tasks", sa.Column("completion_image", sa.String(length=255), nullable=True))
    op.add_column("tasks", sa.Column("external_payment_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tasks", sa.Column("creator_external_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tasks", sa.Column("performer_external_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("tasks", sa.Column("payment_mode", sa.String(length=30), nullable=False, server_default="WALLET"))
    op.add_column("tasks", sa.Column("dispute_status", sa.String(length=30), nullable=False, server_default="NONE"))
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_sender_id"), "chat_messages", ["sender_id"], unique=False)
    op.create_index(op.f("ix_chat_messages_task_id"), "chat_messages", ["task_id"], unique=False)
    op.alter_column("users", "is_frozen", server_default=None)
    op.alter_column("users", "has_pending_dues", server_default=None)
    op.alter_column("tasks", "negotiation_status", server_default=None)
    op.alter_column("tasks", "external_payment_requested", server_default=None)
    op.alter_column("tasks", "creator_external_confirmed", server_default=None)
    op.alter_column("tasks", "performer_external_confirmed", server_default=None)
    op.alter_column("tasks", "payment_mode", server_default=None)
    op.alter_column("tasks", "dispute_status", server_default=None)


def downgrade():
    op.drop_index(op.f("ix_chat_messages_task_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_sender_id"), table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_column("tasks", "dispute_status")
    op.drop_column("tasks", "payment_mode")
    op.drop_column("tasks", "performer_external_confirmed")
    op.drop_column("tasks", "creator_external_confirmed")
    op.drop_column("tasks", "external_payment_requested")
    op.drop_column("tasks", "completion_image")
    op.drop_column("tasks", "negotiation_status")
    op.drop_column("tasks", "proposed_price")
    op.drop_column("tasks", "agreed_price")
    op.drop_column("users", "has_pending_dues")
    op.drop_column("users", "is_frozen")
