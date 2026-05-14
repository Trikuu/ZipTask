from flask import Blueprint, current_app, flash, g, make_response, redirect, render_template, request, url_for

from .auth_utils import create_token
from .extensions import db
from .models import User
from .services import ensure_wallet, send_password_reset_email, validate_password, verify_password_reset_token

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if g.current_user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        accepted_privacy = request.form.get("accept_privacy") == "on"
        accepted_terms = request.form.get("accept_terms") == "on"

        if not all([full_name, email, phone, password]):
            flash("All fields are required.", "danger")
            return render_template("auth/signup.html")
        password_errors = validate_password(password)
        if password_errors:
            for error in password_errors:
                flash(error, "danger")
            return render_template("auth/signup.html")
        if not accepted_privacy or not accepted_terms:
            flash("You must accept the Privacy Policy and Terms & Conditions.", "danger")
            return render_template("auth/signup.html")
        if User.query.filter_by(email=email).first():
            flash("Email is already registered.", "danger")
            return render_template("auth/signup.html")
        if User.query.filter_by(phone=phone).first():
            flash("Phone number is already registered.", "danger")
            return render_template("auth/signup.html")

        user = User(full_name=full_name, email=email, phone=phone, role="USER")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        ensure_wallet(user)
        db.session.commit()
        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.current_user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")
        if user.is_deleted or not user.is_active or user.is_frozen:
            flash("Your account is inactive. Please contact admin.", "danger")
            return render_template("auth/login.html")

        token = create_token(user)
        next_url = request.args.get("next") or url_for("admin.panel" if user.is_admin else "main.dashboard")
        response = make_response(redirect(next_url))
        response.set_cookie("ziptask_token", token, httponly=True, samesite="Lax", max_age=7 * 24 * 60 * 60)
        flash("Login successful", "success")
        return response

    return render_template("auth/login.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if g.current_user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email, is_deleted=False).first()
        if not user or not user.is_active:
            flash("Invalid email", "danger")
            return render_template("auth/forgot_password.html")

        try:
            sent = send_password_reset_email(user)
        except Exception:
            current_app.logger.exception("Password reset email failed.")
            sent = False

        if not sent:
            flash("Password reset email could not be sent. Please contact support.", "danger")
            return render_template("auth/forgot_password.html")

        flash("Password reset link sent to your email.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if g.current_user:
        return redirect(url_for("main.dashboard"))

    user, error = verify_password_reset_token(token)
    if error:
        flash(error, "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        password_errors = validate_password(password)
        if password_errors:
            for item in password_errors:
                flash(item, "danger")
            return render_template("auth/reset_password.html", token=token)

        user.set_password(password)
        db.session.commit()
        flash("Password reset successful", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(redirect(url_for("main.home")))
    response.delete_cookie("ziptask_token")
    flash("Logged out successfully.", "success")
    return response
