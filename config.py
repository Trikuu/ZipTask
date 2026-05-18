import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL must be set")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    return db_url


def env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


class Config:
    BASE_DIR = Path(__file__).resolve().parent
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    }
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    JWT_EXPIRY = timedelta(days=7)
    JWT_COOKIE_NAME = "ziptask_token"
    COOKIE_SECURE = env_bool("COOKIE_SECURE", "true")
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
    DEFAULT_ADMIN_PHONE = os.getenv("DEFAULT_ADMIN_PHONE")
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    PROFILE_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "profiles"
    PROOF_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "proofs"
    PLATFORM_FEE_CREDIT_LIMIT = os.getenv("PLATFORM_FEE_CREDIT_LIMIT", "-100")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}

    @classmethod
    def validate(cls) -> None:
        required = {
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            "SECRET_KEY": cls.SECRET_KEY,
            "DEFAULT_ADMIN_EMAIL": cls.DEFAULT_ADMIN_EMAIL,
            "DEFAULT_ADMIN_PASSWORD": cls.DEFAULT_ADMIN_PASSWORD,
            "DEFAULT_ADMIN_PHONE": cls.DEFAULT_ADMIN_PHONE,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
