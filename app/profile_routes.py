from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from .auth_utils import login_required
from .extensions import db

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        photo = request.files.get("profile_image")

        if not full_name:
            flash("Full name is required.", "danger")
            return render_template("profile/index.html")

        g.current_user.full_name = full_name

        if photo and photo.filename:
            if not allowed_image(photo.filename):
                flash("Profile photo must be JPG, PNG, or WEBP.", "danger")
                return render_template("profile/index.html")

            upload_dir = Path(current_app.config["PROFILE_UPLOAD_FOLDER"])
            upload_dir.mkdir(parents=True, exist_ok=True)
            ext = secure_filename(photo.filename).rsplit(".", 1)[1].lower()
            filename = f"user-{g.current_user.id}-{uuid4().hex}.{ext}"
            photo.save(upload_dir / filename)
            g.current_user.profile_image = f"uploads/profiles/{filename}"

        db.session.commit()
        flash("Profile updated", "success")
        return redirect(url_for("profile.profile"))

    return render_template("profile/index.html")
