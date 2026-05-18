import logging

from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import Config

from .auth_utils import clear_invalid_auth_cookie, load_user_from_cookie
from .extensions import db, migrate
from .services import bootstrap_admin


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if hasattr(config_class, "validate"):
        config_class.validate()

    configure_logging(app)
    configure_database_engine(app)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models
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
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("postgresql+psycopg://"):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL using the psycopg driver.")


def configure_logging(app: Flask) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app.logger.setLevel(logging.INFO)
