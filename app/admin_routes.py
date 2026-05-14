from datetime import datetime, time

from sqlalchemy import func
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth_utils import admin_required
from .extensions import db
from .models import Task, Transaction, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@admin_required
def panel():
    user_id = request.args.get("user_id", type=int)
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    users = User.query.order_by(User.created_at.desc()).all()

    tasks_query = Task.query
    tx_query = Transaction.query
    if user_id:
        tasks_query = tasks_query.filter((Task.creator_id == user_id) | (Task.assigned_to == user_id))
        tx_query = tx_query.filter(Transaction.user_id == user_id)
    if status in {"OPEN", "REQUESTED", "ASSIGNED", "COMPLETED"}:
        tasks_query = tasks_query.filter(Task.status == status)

    start_dt = parse_date_start(date_from)
    end_dt = parse_date_end(date_to)
    if start_dt:
        tasks_query = tasks_query.filter(Task.created_at >= start_dt)
        tx_query = tx_query.filter(Transaction.created_at >= start_dt)
    if end_dt:
        tasks_query = tasks_query.filter(Task.created_at <= end_dt)
        tx_query = tx_query.filter(Transaction.created_at <= end_dt)

    tasks = tasks_query.order_by(Task.created_at.desc()).all()
    transactions = tx_query.order_by(Transaction.created_at.desc()).limit(200).all()
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
        filters={"user_id": user_id, "status": status, "date_from": date_from, "date_to": date_to},
    )


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == g.current_user.id:
        flash("You cannot deactivate your own admin account.", "danger")
        return redirect(url_for("admin.panel"))
    if user.is_admin:
        flash("Admin accounts cannot be deactivated from this panel.", "danger")
        return redirect(url_for("admin.panel"))

    user.is_active = not user.is_active
    db.session.commit()
    flash("User activated" if user.is_active else "User deactivated", "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == g.current_user.id:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for("admin.panel"))
    if user.is_admin:
        flash("Admin accounts cannot be deleted from this panel.", "danger")
        return redirect(url_for("admin.panel"))

    user.is_active = False
    user.is_deleted = True
    db.session.commit()
    flash("User deleted", "success")
    return redirect(url_for("admin.panel"))


def parse_date_start(value: str):
    if not value:
        return None
    try:
        return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.min)
    except ValueError:
        return None


def parse_date_end(value: str):
    if not value:
        return None
    try:
        return datetime.combine(datetime.strptime(value, "%Y-%m-%d").date(), time.max)
    except ValueError:
        return None
