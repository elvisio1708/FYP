"""Application configuration.

Everything here can be overridden with environment variables, so nothing secret
or machine-specific needs to live in the repository.

    SECRET_KEY      signs the session cookie (set this in production)
    DATABASE_PATH   path to the SQLite file (default: backend/instance/app.db)
    COOKIE_SECURE   set to 1 when served over HTTPS
"""
import os
import secrets
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"


def _load_secret_key() -> str:
    """Use SECRET_KEY if set; otherwise create and reuse a local dev key.

    The dev key is stored in instance/ (git-ignored) so logins survive restarts.
    """
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    INSTANCE_DIR.mkdir(exist_ok=True)
    key_file = INSTANCE_DIR / ".secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.write_text(key)
    return key


class Config:
    SECRET_KEY = _load_secret_key()
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(INSTANCE_DIR / "app.db"))
    MAX_CONTENT_LENGTH = 64 * 1024  # requests are small JSON bodies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    JSON_SORT_KEYS = False
