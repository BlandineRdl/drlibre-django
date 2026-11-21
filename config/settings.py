from pathlib import Path

from django.utils.csp import CSP
from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.logging import configure_structlog, logging_config

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
    log_level: str = "INFO"
    # True once served behind TLS; localhost stays plain HTTP.
    https_only: bool = False
    # Absolute links in emails, where no request exists to build them from.
    public_base_url: str = "http://localhost:8000"
    # Hourly cap per network address and kind of request; raised for load tests.
    network_hourly_limit: int = Field(default=20, ge=1)


env = Settings()
_db = env.database_url.hosts()[0]

SECRET_KEY = env.secret_key
DEBUG = env.debug
ALLOWED_HOSTS = env.allowed_hosts

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
    "drlibre.audit.infrastructure.django",
    "drlibre.booking.infrastructure.django",
    "drlibre.identity.infrastructure.django",
    "drlibre.notifications.infrastructure.django",
    "drlibre.organisation.infrastructure.django",
    "drlibre.scheduling.infrastructure.django",
    "drlibre.interfaces.web",
]

MIDDLEWARE = [
    "config.middleware.CorrelationIdMiddleware",
    "config.middleware.SameOriginMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "django.middleware.common.CommonMiddleware",
    "drlibre.interfaces.web.auth.SessionMiddleware",
    "drlibre.interfaces.web.views.errors.DomainErrorPagesMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Pico.css draws its search, select and checkbox icons as inline SVG data images.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "frame-ancestors": [CSP.NONE],
}
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

SECURE_SSL_REDIRECT = env.https_only
# Own session cookie (contrib.sessions stays out): HttpOnly, SameSite=Lax, Secure behind TLS.
SESSION_COOKIE_NAME = "drlibre_session"
SESSION_COOKIE_SECURE = env.https_only
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.https_only
SECURE_HSTS_SECONDS = 31_536_000 if env.https_only else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.https_only
# HSTS preload list submission is a domain owner's opt-in, not a code default.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

configure_structlog()
LOGGING = logging_config(env.log_level)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
                "drlibre.interfaces.web.context.shell",
            ],
        },
    }
]

# Slow salted hash for passwords (spec 12.1); Django's hashers work without contrib.auth.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
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

PUBLIC_BASE_URL = env.public_base_url
NETWORK_HOURLY_LIMIT = env.network_hourly_limit
# Prefix of the Redis rate-limit keys; tests swap it for their own.
RATE_LIMIT_PREFIX = "drlibre:rate"
REDIS_URL = str(env.redis_url)
CELERY_BROKER_URL = REDIS_URL
CELERY_TIMEZONE = env.default_time_zone
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False


def smtp_mailers() -> dict[str, dict[str, object]]:
    return {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {"host": env.email_host, "port": env.email_port, "timeout": 10},
        }
    }


MAILERS = smtp_mailers()
DEFAULT_FROM_EMAIL = "DrLibre <no-reply@drlibre.localhost>"

LANGUAGE_CODE = "en-us"
TIME_ZONE = env.default_time_zone
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
