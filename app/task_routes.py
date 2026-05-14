from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth_utils import login_required
from .extensions import db
from .models import Task, TaskApplication
from .services import get_admin_user, money, record_transaction

task_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@task_bp.route("/post", methods=["GET", "POST"])
@login_required
def post_task():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        budget_raw = request.form.get("budget", "").strip()

        try:
            budget = money(budget_raw)
        except Exception:
            budget = Decimal("0.00")

        if not title or not description or not location or budget <= 0:
            flash("Please enter a valid title, description, budget and location.", "danger")
            return render_template("tasks/post.html")

        task = Task(
            creator_id=g.current_user.id,
            title=title,
            description=description,
            budget=budget,
            location=location,
            status="OPEN",
        )
        db.session.add(task)
        db.session.commit()
        flash("Task posted successfully", "success")
        return redirect(url_for("tasks.browse"))

    return render_template("tasks/post.html")


@task_bp.route("/")
def browse():
    status = request.args.get("status", "OPEN")
    query = Task.query
    if status in {"OPEN", "REQUESTED", "ASSIGNED", "COMPLETED"}:
        query = query.filter_by(status=status)
    tasks = query.order_by(Task.created_at.desc()).all()
    applied_task_ids = set()
    if g.current_user:
        applied_task_ids = {
            item.task_id
            for item in TaskApplication.query.filter_by(user_id=g.current_user.id).all()
        }
    return render_template("tasks/browse.html", tasks=tasks, status=status, applied_task_ids=applied_task_ids)


@task_bp.route("/<int:task_id>/apply", methods=["POST"])
@login_required
def apply_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.creator_id == g.current_user.id:
        flash("You cannot apply to your own task.", "danger")
        return redirect(url_for("tasks.browse"))
    if task.status not in {"OPEN", "REQUESTED"}:
        flash("This task is no longer accepting requests.", "warning")
        return redirect(url_for("tasks.browse"))
    existing = TaskApplication.query.filter_by(task_id=task.id, user_id=g.current_user.id).first()
    if existing:
        flash("You have already requested to join this task.", "warning")
        return redirect(url_for("tasks.browse"))

    db.session.add(TaskApplication(task_id=task.id, user_id=g.current_user.id, status="PENDING"))
    task.status = "REQUESTED"
    db.session.commit()
    flash("Request sent", "success")
    return redirect(url_for("tasks.browse", status="REQUESTED"))


@task_bp.route("/<int:task_id>/assign/<int:application_id>", methods=["POST"])
@login_required
def assign_task(task_id, application_id):
    task = Task.query.get_or_404(task_id)
    application = TaskApplication.query.filter_by(id=application_id, task_id=task.id).first_or_404()

    if task.creator_id != g.current_user.id:
        flash("Only the task creator can assign this task.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status == "ASSIGNED":
        flash("This task is already assigned.", "warning")
        return redirect(url_for("main.dashboard"))
    if task.status == "COMPLETED":
        flash("Completed tasks cannot be reassigned.", "warning")
        return redirect(url_for("main.dashboard"))
    if task.creator.wallet.available_balance < task.budget_decimal:
        flash("Add enough wallet balance before assigning this task.", "danger")
        return redirect(url_for("wallet.wallet"))

    task.creator.wallet.locked_balance += task.budget_decimal
    task.assigned_to = application.user_id
    task.status = "ASSIGNED"
    task.assigned_at = datetime.now(timezone.utc)
    application.status = "ASSIGNED"
    TaskApplication.query.filter(
        TaskApplication.task_id == task.id,
        TaskApplication.id != application.id,
    ).update({"status": "REJECTED"}, synchronize_session=False)
    record_transaction(task.creator_id, task.budget_decimal, "TASK_BUDGET_LOCKED", "SUCCESS", task.id)
    db.session.commit()
    flash("Task assigned", "success")
    return redirect(url_for("main.dashboard"))


@task_bp.route("/<int:task_id>/complete", methods=["POST"])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.creator_id != g.current_user.id:
        flash("Only the task creator can mark this task complete.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status != "ASSIGNED" or not task.performer:
        flash("Only assigned tasks can be completed.", "warning")
        return redirect(url_for("main.dashboard"))

    admin = get_admin_user()
    if not admin:
        flash("Admin wallet is not configured.", "danger")
        return redirect(url_for("main.dashboard"))

    budget = task.budget_decimal
    performer_share = (budget * Decimal("0.95")).quantize(Decimal("0.01"))
    admin_share = budget - performer_share

    creator_wallet = task.creator.wallet
    performer_wallet = task.performer.wallet
    admin_wallet = admin.wallet

    if creator_wallet.locked_balance < budget or creator_wallet.balance < budget:
        flash("Locked budget is unavailable. Please contact support.", "danger")
        return redirect(url_for("main.dashboard"))

    creator_wallet.locked_balance -= budget
    creator_wallet.balance -= budget
    performer_wallet.balance += performer_share
    admin_wallet.balance += admin_share
    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)

    record_transaction(task.creator_id, -budget, "TASK_PAYMENT_RELEASED", "SUCCESS", task.id)
    record_transaction(task.performer.id, performer_share, "TASK_EARNING_95_PERCENT", "SUCCESS", task.id)
    record_transaction(admin.id, admin_share, "PLATFORM_FEE_5_PERCENT", "SUCCESS", task.id)
    db.session.commit()
    flash("Task completed successfully. Payment released.", "success")
    return redirect(url_for("main.dashboard"))
