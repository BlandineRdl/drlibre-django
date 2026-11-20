from pathlib import Path

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    secret_key: str = Field(min_length=32)
    debug: bool = False
    database_url: PostgresDsn
    redis_url: RedisDsn
    email_host: str
    email_port: int
    default_time_zone: str = "Europe/Paris"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]


env = Settings()
_db = env.database_url.hosts()[0]

SECRET_KEY = env.secret_key
DEBUG = env.debug
ALLOWED_HOSTS = env.allowed_hosts

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (env.database_url.path or "/").lstrip("/"),
        "USER": _db["username"] or "",
        "PASSWORD": _db["password"] or "",
        "HOST": _db["host"] or "",
        "PORT": _db["port"] or 5432,
    }
}

REDIS_URL = str(env.redis_url)

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {"host": env.email_host, "port": env.email_port, "timeout": 10},
    }
}
DEFAULT_FROM_EMAIL = "DrLibre <no-reply@drlibre.localhost>"

LANGUAGE_CODE = "en-us"
TIME_ZONE = env.default_time_zone
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
