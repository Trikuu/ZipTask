from sqlalchemy import func
from flask import Blueprint, render_template

from .auth_utils import admin_required
from .models import Task, Transaction, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def panel():
    users = User.query.order_by(User.created_at.desc()).all()
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(100).all()
    total_earnings = (
        Transaction.query.with_entities(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.type == "PLATFORM_FEE_5_PERCENT", Transaction.status == "SUCCESS")
        .scalar()
    )
    return render_template(
        "admin/panel.html",
        users=users,
        tasks=tasks,
        transactions=transactions,
        total_earnings=total_earnings,
    )
