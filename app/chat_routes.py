from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

from .auth_utils import login_required
from .extensions import db
from .models import ChatMessage, Task
from .services import user_can_access_task_chat

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/tasks/<int:task_id>", methods=["GET"])
@login_required
def task_chat(task_id):
    task = Task.query.get_or_404(task_id)
    if not user_can_access_task_chat(g.current_user, task):
        flash("Chat is available only after assignment to task participants.", "danger")
        return redirect(url_for("main.dashboard"))
    return render_template("chat/task_chat.html", task=task)


@chat_bp.route("/tasks/<int:task_id>/messages", methods=["GET"])
@login_required
def messages(task_id):
    task = Task.query.get_or_404(task_id)
    if not user_can_access_task_chat(g.current_user, task):
        return jsonify({"error": "Not allowed"}), 403
    after_id = request.args.get("after_id", 0, type=int)
    query = ChatMessage.query.filter(ChatMessage.task_id == task.id)
    if after_id:
        query = query.filter(ChatMessage.id > after_id)
    items = query.order_by(ChatMessage.timestamp.asc()).limit(100).all()
    return jsonify(
        {
            "messages": [
                {
                    "id": item.id,
                    "sender_id": item.sender_id,
                    "sender_name": item.sender.full_name,
                    "message": item.message,
                    "timestamp": item.timestamp.strftime("%d %b %Y %I:%M %p"),
                    "mine": item.sender_id == g.current_user.id,
                }
                for item in items
            ]
        }
    )


@chat_bp.route("/tasks/<int:task_id>/messages", methods=["POST"])
@login_required
def send_message(task_id):
    task = Task.query.get_or_404(task_id)
    if not user_can_access_task_chat(g.current_user, task):
        return jsonify({"error": "Not allowed"}), 403
    message = request.form.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    db.session.add(ChatMessage(task_id=task.id, sender_id=g.current_user.id, message=message[:2000]))
    db.session.commit()
    return jsonify({"message": "New message"})
