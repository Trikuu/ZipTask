import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


class Config:
    BASE_DIR = Path(__file__).resolve().parent

    # 🔐 Security
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY

    # 🔥 DATABASE (FINAL FIX)
    DATABASE_URL = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be set")

    # Convert Railway URL automatically
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    }

    # 📦 App Config
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    JWT_EXPIRY = timedelta(days=7)
    JWT_COOKIE_NAME = "ziptask_token"
    COOKIE_SECURE = env_bool("COOKIE_SECURE", "true")

    # 👤 Admin
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
    DEFAULT_ADMIN_PHONE = os.getenv("DEFAULT_ADMIN_PHONE")

    # 💳 Payments
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

    # 📁 Uploads
    PROFILE_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "profiles"
    PROOF_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "proofs"

    # 💰 Platform
    PLATFORM_FEE_CREDIT_LIMIT = os.getenv("PLATFORM_FEE_CREDIT_LIMIT", "-100")

    # 📧 Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = env_bool("MAIL_USE_TLS", "true")

    @classmethod
    def validate(cls) -> None:
        required = {
            "DATABASE_URL": cls.DATABASE_URL,
            "SECRET_KEY": cls.SECRET_KEY,
            "DEFAULT_ADMIN_EMAIL": cls.DEFAULT_ADMIN_EMAIL,
            "DEFAULT_ADMIN_PASSWORD": cls.DEFAULT_ADMIN_PASSWORD,
            "DEFAULT_ADMIN_PHONE": cls.DEFAULT_ADMIN_PHONE,
        }

        missing = [name for name, value in required.items() if not value]

        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")