from datetime import datetime, timezone
from functools import wraps

import jwt
from flask import current_app, flash, g, redirect, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from .models import User


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + current_app.config["JWT_EXPIRY"],
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def load_user_from_cookie() -> None:
    g.current_user = None
    g.clear_auth_cookie = False
    token = request.cookies.get(current_app.config["JWT_COOKIE_NAME"])
    if not token:
        return

    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        user_id = int(payload["sub"])
        user = User.query.get(user_id)
    except jwt.ExpiredSignatureError:
        current_app.logger.info("Expired auth token for path %s", request.path)
        g.clear_auth_cookie = True
        return
    except (jwt.PyJWTError, KeyError, ValueError):
        current_app.logger.warning("Invalid auth token for path %s", request.path)
        g.clear_auth_cookie = True
        return
    except SQLAlchemyError:
        current_app.logger.exception("Database failure while loading authenticated user.")
        return

    if user and user.is_active and not user.is_deleted and not user.is_frozen:
        g.current_user = user
    else:
        g.clear_auth_cookie = True


def clear_invalid_auth_cookie(response):
    if getattr(g, "clear_auth_cookie", False):
        response.delete_cookie(current_app.config["JWT_COOKIE_NAME"])
    return response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.current_user:
            flash("Please login to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.current_user:
            flash("Please login to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not g.current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped
