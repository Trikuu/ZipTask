import logging
import os

from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import Config

from .auth_utils import clear_invalid_auth_cookie, load_user_from_cookie
from .extensions import db, migrate
from .services import bootstrap_admin


def create_app(config_class=Config):
    app = Flask(__name__)

    # Load config
    app.config.from_object(config_class)
    app.config["SQLALCHEMY_DATABASE_URI"] = config_class.get_database_uri()

    if hasattr(config_class, "validate"):
        config_class.validate()

    configure_logging(app)
    configure_database_engine(app)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models
    from . import models

    # Register blueprints
    from .admin_routes import admin_bp
    from .auth_routes import auth_bp
    from .chat_routes import chat_bp
    from .main_routes import main_bp
    from .profile_routes import profile_bp
    from .task_routes import task_bp
    from .wallet_routes import wallet_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(admin_bp)

    # Middleware
    app.before_request(load_user_from_cookie)
    app.after_request(clear_invalid_auth_cookie)

    @app.teardown_request
    def rollback_failed_request(exc):
        if exc is not None:
            db.session.rollback()
            app.logger.exception("Request failed and database session was rolled back.", exc_info=exc)
        db.session.remove()

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(exc):
        db.session.rollback()
        app.logger.exception("Database error")
        return "Database temporarily unavailable. Please try again.", 503

    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "database": "connected"})
        except SQLAlchemyError:
            app.logger.exception("Health check database failure")
            return jsonify({"status": "error", "database": "unavailable"}), 503

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        bootstrap_admin()
        print("Admin account is ready.")

    return app


def configure_database_engine(app: Flask) -> None:
    """
    Fix Railway DATABASE_URL automatically.
    """
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise RuntimeError("DATABASE_URL must be set")

    # 🔥 IMPORTANT FIX: Convert Railway URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url


def configure_logging(app: Flask) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app.logger.setLevel(logging.INFO)