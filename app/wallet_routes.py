import hmac
import hashlib
from decimal import Decimal

import razorpay
from flask import Blueprint, current_app, flash, g, jsonify, render_template, request

from .auth_utils import login_required
from .extensions import db
from .models import Transaction
from .services import money, record_transaction

wallet_bp = Blueprint("wallet", __name__, url_prefix="/wallet")


def razorpay_client():
    key_id = current_app.config["RAZORPAY_KEY_ID"]
    key_secret = current_app.config["RAZORPAY_KEY_SECRET"]
    if not key_id or not key_secret:
        return None
    return razorpay.Client(auth=(key_id, key_secret))


@wallet_bp.route("/")
@login_required
def wallet():
    transactions = (
        Transaction.query.filter_by(user_id=g.current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return render_template(
        "wallet/index.html",
        transactions=transactions,
        razorpay_key_id=current_app.config["RAZORPAY_KEY_ID"],
    )


@wallet_bp.route("/create-order", methods=["POST"])
@login_required
def create_order():
    try:
        amount = money(request.form.get("amount", "0"))
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    client = razorpay_client()
    if not client:
        return jsonify({"error": "Razorpay keys are not configured"}), 500

    order = client.order.create(
        {
            "amount": int(amount * Decimal("100")),
            "currency": "INR",
            "payment_capture": 1,
            "notes": {"user_id": str(g.current_user.id), "purpose": "wallet_topup"},
        }
    )
    record_transaction(g.current_user.id, amount, "WALLET_TOPUP_INITIATED", "PENDING", reference=order["id"])
    db.session.commit()
    return jsonify(order)


@wallet_bp.route("/verify-payment", methods=["POST"])
@login_required
def verify_payment():
    data = request.get_json(silent=True) or {}
    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")

    if not all([order_id, payment_id, signature]):
        return jsonify({"error": "Invalid payment data"}), 400

    pending = Transaction.query.filter_by(
        user_id=g.current_user.id,
        reference=order_id,
        type="WALLET_TOPUP_INITIATED",
        status="PENDING",
    ).first()
    if not pending:
        return jsonify({"error": "Payment order was not found"}), 400
    amount = money(pending.amount)

    secret = current_app.config["RAZORPAY_KEY_SECRET"].encode()
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        record_transaction(g.current_user.id, amount, "WALLET_TOPUP_FAILED", "FAILED", reference=order_id)
        pending.status = "FAILED"
        db.session.commit()
        return jsonify({"error": "Payment verification failed"}), 400

    existing = Transaction.query.filter_by(reference=payment_id, status="SUCCESS").first()
    if existing:
        return jsonify({"message": "Payment already credited"})

    g.current_user.wallet.balance += amount
    pending.status = "SUCCESS"
    record_transaction(g.current_user.id, amount, "WALLET_TOPUP", "SUCCESS", reference=payment_id)
    db.session.commit()
    flash("Payment successful", "success")
    return jsonify({"message": "Payment successful", "balance": str(g.current_user.wallet.balance)})
