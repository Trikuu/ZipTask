from flask import Flask
from sqlalchemy import inspect
import os

from config import Config

from .auth_utils import load_user_from_cookie
from .extensions import db, migrate
from .services import bootstrap_admin


def create_app(config_class=Config):
    app = Flask(__name__)

    # Load config
    app.config.from_object(config_class)

    # ✅ FIX DATABASE URL DRIVER
    db_url = os.getenv("DATABASE_URL")

    if db_url and db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

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

    # Load user before each request
    app.before_request(load_user_from_cookie)

    # CLI command
    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        bootstrap_admin()
        print("Admin account is ready.")

    # Auto bootstrap admin if DB ready
    with app.app_context():
    try:
        if inspect(db.engine).has_table("users"):

            # 🔥 AUTO FIX MISSING COLUMNS
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
                conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE"))
                conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_frozen BOOLEAN DEFAULT FALSE"))
                conn.execute(db.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS has_pending_dues BOOLEAN DEFAULT FALSE"))
                conn.commit()

            bootstrap_admin()

    except Exception as exc:
        app.logger.warning("Admin bootstrap skipped until database is ready: %s", exc)

    return app