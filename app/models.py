from datetime import datetime, timezone
from decimal import Decimal

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="USER")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    is_frozen = db.Column(db.Boolean, nullable=False, default=False)
    has_pending_dues = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    wallet = db.relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    tasks_created = db.relationship("Task", foreign_keys="Task.creator_id", back_populates="creator")
    tasks_assigned = db.relationship("Task", foreign_keys="Task.assigned_to", back_populates="performer")
    transactions = db.relationship("Transaction", back_populates="user")
    applications = db.relationship("TaskApplication", back_populates="user", cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", back_populates="sender")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Numeric(10, 2), nullable=False)
    location = db.Column(db.String(160), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="OPEN")
    agreed_price = db.Column(db.Numeric(10, 2), nullable=True)
    proposed_price = db.Column(db.Numeric(10, 2), nullable=True)
    negotiation_status = db.Column(db.String(30), nullable=False, default="NONE")
    completion_image = db.Column(db.String(255), nullable=True)
    external_payment_requested = db.Column(db.Boolean, nullable=False, default=False)
    creator_external_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    performer_external_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    payment_mode = db.Column(db.String(30), nullable=False, default="WALLET")
    dispute_status = db.Column(db.String(30), nullable=False, default="NONE")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    creator = db.relationship("User", foreign_keys=[creator_id], back_populates="tasks_created")
    performer = db.relationship("User", foreign_keys=[assigned_to], back_populates="tasks_assigned")
    applications = db.relationship("TaskApplication", back_populates="task", cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", back_populates="task", cascade="all, delete-orphan")

    @property
    def budget_decimal(self) -> Decimal:
        return Decimal(self.budget).quantize(Decimal("0.01"))

    @property
    def agreed_price_decimal(self) -> Decimal:
        value = self.agreed_price if self.agreed_price is not None else self.budget
        return Decimal(value).quantize(Decimal("0.01"))


class TaskApplication(db.Model):
    __tablename__ = "task_applications"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="PENDING")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task = db.relationship("Task", back_populates="applications")
    user = db.relationship("User", back_populates="applications")

    __table_args__ = (db.UniqueConstraint("task_id", "user_id", name="uq_task_application_user"),)


class Wallet(db.Model):
    __tablename__ = "wallets"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    balance = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    locked_balance = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="wallet")

    @property
    def available_balance(self) -> Decimal:
        return (Decimal(self.balance) - Decimal(self.locked_balance)).quantize(Decimal("0.01"))


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="SUCCESS")
    reference = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="transactions")
    task = db.relationship("Task")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task = db.relationship("Task", back_populates="chat_messages")
    sender = db.relationship("User", back_populates="chat_messages")
