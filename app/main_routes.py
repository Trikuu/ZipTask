from flask import Blueprint, render_template

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
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(5).all()
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", recent_tasks=recent_tasks, recent_transactions=recent_transactions)


@main_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy.html")


@main_bp.route("/terms")
def terms():
    return render_template("terms.html")
