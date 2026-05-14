from decimal import Decimal

from flask import current_app
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import Transaction, User, Wallet


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def ensure_wallet(user: User) -> Wallet:
    if user.wallet:
        return user.wallet
    wallet = Wallet(user=user, balance=money("0"), locked_balance=money("0"))
    db.session.add(wallet)
    return wallet


def get_admin_user() -> User:
    return User.query.filter_by(role="ADMIN").order_by(User.id.asc()).first()


def bootstrap_admin() -> None:
    email = current_app.config["DEFAULT_ADMIN_EMAIL"].strip().lower()
    password = current_app.config["DEFAULT_ADMIN_PASSWORD"]
    if not email or not password:
        raise RuntimeError("DEFAULT_ADMIN_EMAIL and DEFAULT_ADMIN_PASSWORD must be configured.")

    admin = User.query.filter_by(email=email).first()
    if admin:
        if admin.role != "ADMIN":
            admin.role = "ADMIN"
        ensure_wallet(admin)
        db.session.commit()
        return

    admin = User(full_name="ZipTask Admin", email=email, phone="0000000000", role="ADMIN")
    admin.set_password(password)
    db.session.add(admin)
    db.session.flush()
    ensure_wallet(admin)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        admin = User.query.filter_by(email=email).first()
        if admin:
            admin.role = "ADMIN"
            ensure_wallet(admin)
            db.session.commit()


def record_transaction(user_id: int, amount, txn_type: str, status: str = "SUCCESS", task_id: int | None = None, reference: str | None = None) -> Transaction:
    txn = Transaction(
        user_id=user_id,
        task_id=task_id,
        amount=money(amount),
        type=txn_type,
        status=status,
        reference=reference,
    )
    db.session.add(txn)
    return txn
