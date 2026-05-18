from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, flash, g, make_response, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .auth_utils import create_token
from .extensions import db
from .models import User
from .services import ensure_wallet, send_password_reset_email, validate_password, verify_password_reset_token

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW = timedelta(minutes=10)


def login_rate_limited(key: str) -> bool:
    now = datetime.now(timezone.utc)
    attempts = [item for item in LOGIN_ATTEMPTS.get(key, []) if now - item < LOGIN_WINDOW]
    LOGIN_ATTEMPTS[key] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def record_login_failure(key: str) -> None:
    LOGIN_ATTEMPTS.setdefault(key, []).append(datetime.now(timezone.utc))


def clear_login_failures(key: str) -> None:
    LOGIN_ATTEMPTS.pop(key, None)


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
        try:
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
        except IntegrityError:
            db.session.rollback()
            current_app.logger.exception("Duplicate signup prevented for email=%s phone=%s", email, phone)
            flash("Email or phone number is already registered.", "danger")
            return render_template("auth/signup.html")
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Database error during signup.")
            flash("Database temporarily unavailable. Please try again.", "danger")
            return render_template("auth/signup.html")
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
        rate_key = f"{request.remote_addr}:{email}"
        if login_rate_limited(rate_key):
            flash("Too many login attempts. Please try again later.", "danger")
            return render_template("auth/login.html")

        try:
            user = User.query.filter_by(email=email).first()
        except SQLAlchemyError:
            current_app.logger.exception("Database error during login lookup.")
            flash("Database temporarily unavailable. Please try again.", "danger")
            return render_template("auth/login.html")

        if not user or not user.check_password(password):
            record_login_failure(rate_key)
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")
        if user.is_deleted or user.is_frozen or user.is_active is False:
            record_login_failure(rate_key)
            flash("Your account is inactive. Please contact admin.", "danger")
            return render_template("auth/login.html")

        clear_login_failures(rate_key)
        token = create_token(user)
        next_url = request.args.get("next") or url_for("admin.panel" if user.is_admin else "main.dashboard")
        response = make_response(redirect(next_url))
        response.set_cookie(
            current_app.config["JWT_COOKIE_NAME"],
            token,
            httponly=True,
            secure=current_app.config["COOKIE_SECURE"],
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )
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
    response = make_response(redirect(url_for("auth.login")))
    response.delete_cookie(current_app.config["JWT_COOKIE_NAME"])
    flash("Logged out successfully.", "success")
    return response
