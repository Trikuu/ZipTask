from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
import re
import smtplib
from uuid import uuid4

from flask import current_app, url_for
from sqlalchemy.exc import IntegrityError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from .extensions import db
from .models import Task, Transaction, User, Wallet


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def validate_password(password: str) -> list[str]:
    errors = []
    if not 8 <= len(password) <= 12:
        errors.append("Password must be 8 to 12 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must include at least one uppercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must include at least one number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include at least one special character.")
    return errors


def password_reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="ziptask-password-reset")


def generate_password_reset_token(user: User) -> str:
    return password_reset_serializer().dumps({"user_id": user.id, "email": user.email})


def verify_password_reset_token(token: str, max_age_seconds: int = 1800) -> tuple[User | None, str | None]:
    try:
        data = password_reset_serializer().loads(token, max_age=max_age_seconds)
    except SignatureExpired:
        return None, "Token expired"
    except BadSignature:
        return None, "Invalid reset token"

    user = User.query.get(data.get("user_id"))
    if not user or user.email != data.get("email") or user.is_deleted or not user.is_active:
        return None, "Invalid reset token"
    return user, None


def send_password_reset_email(user: User) -> bool:
    server = current_app.config["MAIL_SERVER"]
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    if not server or not username or not password:
        current_app.logger.warning("Password reset email skipped because SMTP is not configured.")
        return False

    token = generate_password_reset_token(user)
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    message = EmailMessage()
    message["Subject"] = "Reset your ZipTask password"
    message["From"] = username
    message["To"] = user.email
    message.set_content(
        f"Hi {user.full_name},\n\n"
        f"Use this link to reset your ZipTask password. It expires in 30 minutes:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )

    with smtplib.SMTP(server, current_app.config["MAIL_PORT"]) as smtp:
        if current_app.config["MAIL_USE_TLS"]:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return True


def ensure_wallet(user: User) -> Wallet:
    if user.wallet:
        return user.wallet
    wallet = Wallet(user=user, balance=money("0"), locked_balance=money("0"))
    db.session.add(wallet)
    return wallet


def assert_user_can_act(user: User) -> str | None:
    if user.is_frozen:
        return "Your account is frozen. Please contact admin."
    if user.has_pending_dues:
        return "Payment pending. Clear dues before taking new actions."
    return None


def user_can_access_task_chat(user: User, task: Task) -> bool:
    return bool(task.assigned_to and user.id in {task.creator_id, task.assigned_to})


def task_amount(task: Task) -> Decimal:
    return task.agreed_price_decimal


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_proof_image(file_storage, task_id: int) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("Proof image is required.")
    if not allowed_image(file_storage.filename):
        raise ValueError("Proof image must be JPG, PNG, or WEBP.")
    upload_dir = Path(current_app.config["PROOF_UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    filename = f"task-{task_id}-{uuid4().hex}.{ext}"
    file_storage.save(upload_dir / filename)
    return f"uploads/proofs/{filename}"


def complete_wallet_payment(task: Task) -> None:
    admin = get_admin_user()
    if not admin:
        raise ValueError("Admin wallet is not configured.")

    amount = task_amount(task)
    performer_share = (amount * Decimal("0.95")).quantize(Decimal("0.01"))
    admin_share = amount - performer_share
    creator_wallet = task.creator.wallet

    if creator_wallet.locked_balance < amount or creator_wallet.balance < amount:
        raise ValueError("Locked budget is unavailable. Please contact support.")

    creator_wallet.locked_balance -= amount
    creator_wallet.balance -= amount
    task.performer.wallet.balance += performer_share
    admin.wallet.balance += admin_share
    record_transaction(task.creator_id, -amount, "TASK_PAYMENT_RELEASED", "SUCCESS", task.id)
    record_transaction(task.performer.id, performer_share, "TASK_EARNING_95_PERCENT", "SUCCESS", task.id)
    record_transaction(admin.id, admin_share, "PLATFORM_FEE_5_PERCENT", "SUCCESS", task.id)


def complete_external_payment(task: Task) -> None:
    admin = get_admin_user()
    if not admin:
        raise ValueError("Admin wallet is not configured.")
    if not task.creator_external_confirmed or not task.performer_external_confirmed:
        raise ValueError("Both users must confirm external payment.")

    amount = task_amount(task)
    admin_share = amount - (amount * Decimal("0.95")).quantize(Decimal("0.01"))
    creator_wallet = task.creator.wallet
    credit_limit = money(current_app.config["PLATFORM_FEE_CREDIT_LIMIT"])
    new_balance = money(creator_wallet.balance) - admin_share
    if new_balance < credit_limit:
        raise ValueError("Payment pending. Add money to wallet to cover platform fee.")

    creator_wallet.locked_balance = max(money("0"), money(creator_wallet.locked_balance) - amount)
    creator_wallet.balance = new_balance
    task.creator.has_pending_dues = creator_wallet.balance < 0
    admin.wallet.balance += admin_share
    record_transaction(task.creator_id, -admin_share, "EXTERNAL_PAYMENT_PLATFORM_FEE", "SUCCESS", task.id)
    record_transaction(admin.id, admin_share, "PLATFORM_FEE_5_PERCENT", "SUCCESS", task.id)


def get_admin_user() -> User:
    return User.query.filter_by(role="ADMIN").order_by(User.id.asc()).first()


def bootstrap_admin() -> None:
    email = current_app.config["DEFAULT_ADMIN_EMAIL"].strip().lower()
    password = current_app.config["DEFAULT_ADMIN_PASSWORD"]
    phone = current_app.config["DEFAULT_ADMIN_PHONE"].strip()
    if not email or not password or not phone:
        raise RuntimeError("DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD and DEFAULT_ADMIN_PHONE must be configured.")

    admin = User.query.filter_by(email=email).first()
    if admin:
        if admin.role != "ADMIN":
            admin.role = "ADMIN"
        admin.phone = phone
        admin.is_active = True
        admin.is_deleted = False
        ensure_wallet(admin)
        db.session.commit()
        return

    admin = User(full_name="ZipTask Admin", email=email, phone=phone, role="ADMIN")
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
