from flask import Blueprint, g, render_template

from .auth_utils import login_required
from .models import Task, Transaction

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    open_tasks = Task.query.filter_by(status="OPEN").order_by(Task.created_at.desc()).limit(6).all()
    return render_template("home.html", open_tasks=open_tasks)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = g.current_user.id
    recent_tasks = (
        Task.query.filter((Task.creator_id == user_id) | (Task.assigned_to == user_id))
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )
    recent_transactions = (
        Transaction.query.filter_by(user_id=user_id)
        .order_by(Transaction.created_at.desc())
        .limit(5)
        .all()
    )
    active_tasks = Task.query.filter(
        ((Task.creator_id == user_id) | (Task.assigned_to == user_id)),
        Task.status.in_(["OPEN", "REQUESTED", "ASSIGNED", "NEGOTIATING", "UNDER_REVIEW"]),
    ).count()
    completed_tasks = Task.query.filter(
        ((Task.creator_id == user_id) | (Task.assigned_to == user_id)),
        Task.status == "COMPLETED",
    ).count()
    return render_template(
        "dashboard.html",
        recent_tasks=recent_tasks,
        recent_transactions=recent_transactions,
        active_tasks=active_tasks,
        completed_tasks=completed_tasks,
    )


@main_bp.route("/transactions")
@login_required
def transactions():
    transactions = (
        Transaction.query.filter_by(user_id=g.current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return render_template("transactions.html", transactions=transactions)


@main_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy.html")


@main_bp.route("/terms")
def terms():
    return render_template("terms.html")
