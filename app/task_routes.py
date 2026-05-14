from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth_utils import login_required
from .extensions import db
from .models import Task, TaskApplication
from .services import (
    assert_user_can_act,
    complete_external_payment,
    complete_wallet_payment,
    money,
    record_transaction,
    save_proof_image,
    task_amount,
)

task_bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@task_bp.route("/post", methods=["GET", "POST"])
@login_required
def post_task():
    blocked = assert_user_can_act(g.current_user)
    if blocked:
        flash(blocked, "danger")
        return redirect(url_for("wallet.wallet"))
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
    if status in {"OPEN", "REQUESTED", "ASSIGNED", "NEGOTIATING", "UNDER_REVIEW", "COMPLETED"}:
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
    blocked = assert_user_can_act(g.current_user)
    if blocked:
        flash(blocked, "danger")
        return redirect(url_for("wallet.wallet"))

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
    blocked = assert_user_can_act(g.current_user)
    if blocked:
        flash(blocked, "danger")
        return redirect(url_for("wallet.wallet"))

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

    task.agreed_price = task.budget_decimal
    task.creator.wallet.locked_balance += task.agreed_price_decimal
    task.assigned_to = application.user_id
    task.status = "ASSIGNED"
    task.assigned_at = datetime.now(timezone.utc)
    application.status = "ASSIGNED"
    TaskApplication.query.filter(
        TaskApplication.task_id == task.id,
        TaskApplication.id != application.id,
    ).update({"status": "REJECTED"}, synchronize_session=False)
    record_transaction(task.creator_id, task.agreed_price_decimal, "TASK_BUDGET_LOCKED", "SUCCESS", task.id)
    db.session.commit()
    flash("Task assigned", "success")
    return redirect(url_for("main.dashboard"))


@task_bp.route("/<int:task_id>/negotiate", methods=["POST"])
@login_required
def propose_price(task_id):
    task = Task.query.get_or_404(task_id)
    if task.assigned_to != g.current_user.id:
        flash("Only the assigned performer can negotiate price.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status not in {"ASSIGNED", "NEGOTIATING"}:
        flash("Price can be negotiated only after assignment.", "warning")
        return redirect(url_for("main.dashboard"))

    try:
        proposed = money(request.form.get("proposed_price", "0"))
    except Exception:
        proposed = Decimal("0.00")
    if proposed <= 0:
        flash("Enter a valid proposed price.", "danger")
        return redirect(url_for("main.dashboard"))

    task.proposed_price = proposed
    task.negotiation_status = "PENDING"
    task.status = "NEGOTIATING"
    db.session.commit()
    flash("Negotiation sent", "success")
    return redirect(url_for("main.dashboard"))


@task_bp.route("/<int:task_id>/negotiation/<decision>", methods=["POST"])
@login_required
def review_negotiation(task_id, decision):
    task = Task.query.get_or_404(task_id)
    if task.creator_id != g.current_user.id:
        flash("Only the task creator can review negotiation.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status != "NEGOTIATING" or task.negotiation_status != "PENDING" or task.proposed_price is None:
        flash("No pending negotiation found.", "warning")
        return redirect(url_for("main.dashboard"))

    if decision == "accept":
        current = task.agreed_price_decimal
        proposed = money(task.proposed_price)
        delta = proposed - current
        if delta > 0 and task.creator.wallet.available_balance < delta:
            flash("Add enough wallet balance to accept this negotiated price.", "danger")
            return redirect(url_for("wallet.wallet"))
        task.creator.wallet.locked_balance += delta
        task.agreed_price = proposed
        task.negotiation_status = "ACCEPTED"
        task.status = "ASSIGNED"
        record_transaction(task.creator_id, delta, "NEGOTIATED_BUDGET_ADJUSTMENT", "SUCCESS", task.id)
        flash("Negotiation accepted", "success")
    elif decision == "reject":
        task.negotiation_status = "REJECTED"
        task.status = "ASSIGNED"
        flash("Negotiation rejected", "success")
    else:
        flash("Invalid negotiation action.", "danger")
        return redirect(url_for("main.dashboard"))

    db.session.commit()
    return redirect(url_for("main.dashboard"))


@task_bp.route("/<int:task_id>/commit", methods=["POST"])
@login_required
def commit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.assigned_to != g.current_user.id:
        flash("Only the assigned performer can commit this task.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status != "ASSIGNED":
        flash("Only assigned tasks can be committed.", "warning")
        return redirect(url_for("main.dashboard"))

    try:
        task.completion_image = save_proof_image(request.files.get("completion_image"), task.id)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.dashboard"))

    task.status = "UNDER_REVIEW"
    task.dispute_status = "NONE"
    db.session.commit()
    flash("Task submitted for review", "success")
    return redirect(url_for("main.dashboard"))


@task_bp.route("/<int:task_id>/review/<decision>", methods=["POST"])
@login_required
def review_completion(task_id, decision):
    task = Task.query.get_or_404(task_id)
    if task.creator_id != g.current_user.id:
        flash("Only the task creator can review submitted work.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status != "UNDER_REVIEW" or not task.performer:
        flash("No submitted work is waiting for review.", "warning")
        return redirect(url_for("main.dashboard"))

    if decision == "reject":
        task.status = "ASSIGNED"
        task.dispute_status = "REJECTED_BY_CREATOR"
        db.session.commit()
        flash("Submission rejected and sent back to performer.", "success")
        return redirect(url_for("main.dashboard"))
    if decision != "accept":
        flash("Invalid review action.", "danger")
        return redirect(url_for("main.dashboard"))

    try:
        if task.payment_mode == "EXTERNAL":
            complete_external_payment(task)
        else:
            complete_wallet_payment(task)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.dashboard"))

    task.status = "COMPLETED"
    task.completed_at = datetime.now(timezone.utc)
    task.dispute_status = "NONE"
    db.session.commit()
    flash("Task completed", "success")
    return redirect(url_for("main.dashboard"))


@task_bp.route("/<int:task_id>/external-payment", methods=["POST"])
@login_required
def confirm_external_payment(task_id):
    task = Task.query.get_or_404(task_id)
    if g.current_user.id not in {task.creator_id, task.assigned_to}:
        flash("Only task participants can confirm external payment.", "danger")
        return redirect(url_for("main.dashboard"))
    if task.status not in {"ASSIGNED", "UNDER_REVIEW"}:
        flash("External payment can be confirmed only after assignment.", "warning")
        return redirect(url_for("main.dashboard"))

    task.payment_mode = "EXTERNAL"
    task.external_payment_requested = True
    if g.current_user.id == task.creator_id:
        task.creator_external_confirmed = True
    else:
        task.performer_external_confirmed = True
    db.session.commit()
    flash("External payment confirmation saved", "success")
    return redirect(url_for("main.dashboard"))
