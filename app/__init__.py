from flask import Flask
from sqlalchemy import inspect

from config import Config

from .auth_utils import load_user_from_cookie
from .extensions import db, migrate
from .services import bootstrap_admin


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models
    from .admin_routes import admin_bp
    from .auth_routes import auth_bp
    from .main_routes import main_bp
    from .profile_routes import profile_bp
    from .task_routes import task_bp
    from .wallet_routes import wallet_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(admin_bp)

    app.before_request(load_user_from_cookie)

    @app.cli.command("bootstrap-admin")
    def bootstrap_admin_command():
        bootstrap_admin()
        print("Admin account is ready.")

    with app.app_context():
        try:
            if inspect(db.engine).has_table("users"):
                bootstrap_admin()
        except Exception as exc:
            app.logger.warning("Admin bootstrap skipped until database is ready: %s", exc)

    return app
