"""stable schema

Revision ID: 0001_stable_schema
Revises:
Create Date: 2026-05-18 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_stable_schema"
down_revision = None
branch_labels = None
depends_on = None


def table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def columns(inspector, table_name):
    if not table_exists(inspector, table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def add_column_if_missing(inspector, table_name, column):
    if table_name in inspector.get_table_names() and column.name not in columns(inspector, table_name):
        op.add_column(table_name, column)


def create_index_if_missing(inspector, name, table_name, fields, unique=False):
    if not table_exists(inspector, table_name):
        return
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if name not in existing:
        op.create_index(name, table_name, fields, unique=unique)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not table_exists(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("full_name", sa.String(length=120), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("profile_image", sa.String(length=255), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("has_pending_dues", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("phone"),
        )
    else:
        add_column_if_missing(inspector, "users", sa.Column("profile_image", sa.String(length=255), nullable=True))
        add_column_if_missing(inspector, "users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        add_column_if_missing(inspector, "users", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
        add_column_if_missing(inspector, "users", sa.Column("is_frozen", sa.Boolean(), nullable=False, server_default=sa.false()))
        add_column_if_missing(inspector, "users", sa.Column("has_pending_dues", sa.Boolean(), nullable=False, server_default=sa.false()))
    create_index_if_missing(inspector, "ix_users_email", "users", ["email"])
    create_index_if_missing(inspector, "ix_users_phone", "users", ["phone"])

    inspector = sa.inspect(bind)
    if not table_exists(inspector, "tasks"):
        op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("creator_id", sa.Integer(), nullable=False),
            sa.Column("assigned_to", sa.Integer(), nullable=True),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("budget", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("location", sa.String(length=160), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("agreed_price", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("proposed_price", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("negotiation_status", sa.String(length=30), nullable=False, server_default="NONE"),
            sa.Column("completion_image", sa.String(length=255), nullable=True),
            sa.Column("external_payment_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("creator_external_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("performer_external_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("payment_mode", sa.String(length=30), nullable=False, server_default="WALLET"),
            sa.Column("dispute_status", sa.String(length=30), nullable=False, server_default="NONE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
            sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        for column in [
            sa.Column("agreed_price", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("proposed_price", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("negotiation_status", sa.String(length=30), nullable=False, server_default="NONE"),
            sa.Column("completion_image", sa.String(length=255), nullable=True),
            sa.Column("external_payment_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("creator_external_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("performer_external_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("payment_mode", sa.String(length=30), nullable=False, server_default="WALLET"),
            sa.Column("dispute_status", sa.String(length=30), nullable=False, server_default="NONE"),
        ]:
            add_column_if_missing(inspector, "tasks", column)
    create_index_if_missing(inspector, "ix_tasks_creator_id", "tasks", ["creator_id"])
    create_index_if_missing(inspector, "ix_tasks_assigned_to", "tasks", ["assigned_to"])

    inspector = sa.inspect(bind)
    if not table_exists(inspector, "wallets"):
        op.create_table(
            "wallets",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("balance", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("locked_balance", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("user_id"),
        )

    if not table_exists(inspector, "transactions"):
        op.create_table(
            "transactions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("task_id", sa.Integer(), nullable=True),
            sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("type", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("reference", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    create_index_if_missing(inspector, "ix_transactions_user_id", "transactions", ["user_id"])
    create_index_if_missing(inspector, "ix_transactions_task_id", "transactions", ["task_id"])
    create_index_if_missing(inspector, "ix_transactions_reference", "transactions", ["reference"])

    if not table_exists(inspector, "task_applications"):
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
    create_index_if_missing(inspector, "ix_task_applications_task_id", "task_applications", ["task_id"])
    create_index_if_missing(inspector, "ix_task_applications_user_id", "task_applications", ["user_id"])

    if not table_exists(inspector, "chat_messages"):
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
    create_index_if_missing(inspector, "ix_chat_messages_sender_id", "chat_messages", ["sender_id"])
    create_index_if_missing(inspector, "ix_chat_messages_task_id", "chat_messages", ["task_id"])


def downgrade():
    pass
