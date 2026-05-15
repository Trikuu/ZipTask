from flask import Flask
import os

from config import Config
from .auth_utils import load_user_from_cookie
from .extensions import db
from .services import bootstrap_admin


def create_app(config_class=Config):
    app = Flask(__name__)

    # Load config
    app.config.from_object(config_class)

    # Database URL (simple, no driver tricks)
    db_url = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    # Init DB
    db.init_app(app)

    # Import models (IMPORTANT for create_all)
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

    # ✅ CLEAN DB SETUP (NO MIGRATIONS)
    with app.app_context():
        db.create_all()
        bootstrap_admin()

    return app