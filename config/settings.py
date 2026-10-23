"""Environment-driven Django settings for LogLens."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


def bounded_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


ENVIRONMENT = os.environ.get("DJANGO_ENV", "development").strip().lower()
if ENVIRONMENT not in {"development", "test", "production"}:
    raise ValueError("DJANGO_ENV must be development, test, or production.")
PRODUCTION = ENVIRONMENT == "production"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if PRODUCTION:
        raise ValueError("DJANGO_SECRET_KEY must be set in production.")
    SECRET_KEY = "development-only-secret-key-do-not-use-in-production"
if PRODUCTION and SECRET_KEY.startswith("development-only-"):
    raise ValueError("A non-development DJANGO_SECRET_KEY is required in production.")
if PRODUCTION and len(SECRET_KEY) < 44:
    raise ValueError("DJANGO_SECRET_KEY must contain at least 44 characters in production.")

DEBUG = env_bool("DJANGO_DEBUG", default=False)
if PRODUCTION and DEBUG:
    raise ValueError("DJANGO_DEBUG must be false in production.")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "" if PRODUCTION else "localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]
render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)
if PRODUCTION and not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production.")
if PRODUCTION and "*" in ALLOWED_HOSTS:
    raise ValueError("A wildcard DJANGO_ALLOWED_HOSTS value is not allowed in production.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if render_hostname:
    render_origin = f"https://{render_hostname}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)
if PRODUCTION and not CSRF_TRUSTED_ORIGINS:
    raise ValueError(
        "DJANGO_CSRF_TRUSTED_ORIGINS or RENDER_EXTERNAL_HOSTNAME must be set in production."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.workspaces",
    "apps.ingestion",
    "apps.search",
    "apps.benchmarks",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.loglens_role",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "loglens"),
        "USER": os.environ.get("POSTGRES_USER", "loglens"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("POSTGRES_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}
if PRODUCTION and not DATABASES["default"]["PASSWORD"]:
    raise ValueError("POSTGRES_PASSWORD must be set in production.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(os.environ.get("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PRIVATE_MEDIA_ROOT = Path(
    os.environ.get(
        "PRIVATE_MEDIA_ROOT",
        "/var/lib/loglens/private_media" if PRODUCTION else BASE_DIR / "private_media",
    )
).resolve()
MAX_UPLOAD_SIZE = bounded_int(
    "LOGLENS_MAX_UPLOAD_SIZE", 25 * 1024 * 1024, minimum=1, maximum=50 * 1024 * 1024
)
MAX_UPLOAD_BATCH_SIZE = bounded_int(
    "LOGLENS_MAX_UPLOAD_BATCH_SIZE", 50 * 1024 * 1024, minimum=1, maximum=50 * 1024 * 1024
)
MAX_UPLOAD_COUNT = bounded_int("LOGLENS_MAX_UPLOAD_COUNT", 10, minimum=1, maximum=50)
MAX_DOCX_UNCOMPRESSED_SIZE = bounded_int(
    "LOGLENS_MAX_DOCX_UNCOMPRESSED_SIZE", 100 * 1024 * 1024,
    minimum=1, maximum=500 * 1024 * 1024,
)
MAX_EXTRACTED_CHARACTERS = bounded_int(
    "LOGLENS_MAX_EXTRACTED_CHARACTERS", 5 * 1024 * 1024,
    minimum=1, maximum=50 * 1024 * 1024,
)
MAX_TEXT_SEGMENTS = bounded_int("LOGLENS_MAX_TEXT_SEGMENTS", 100000, minimum=1, maximum=500000)
MAX_PDF_PAGES = bounded_int("LOGLENS_MAX_PDF_PAGES", 1000, minimum=1, maximum=10000)
DOC_CONVERSION_TIMEOUT = bounded_int(
    "LOGLENS_DOC_CONVERSION_TIMEOUT", 60, minimum=1, maximum=300
)
MAX_NAIVE_COMPARISONS = bounded_int(
    "LOGLENS_MAX_NAIVE_COMPARISONS", 5_000_000, minimum=1, maximum=100_000_000
)
MAX_SEARCH_MATCHES = bounded_int(
    "LOGLENS_MAX_SEARCH_MATCHES", 100_000, minimum=1, maximum=1_000_000
)

FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
DATA_UPLOAD_MAX_NUMBER_FILES = MAX_UPLOAD_COUNT
FILE_UPLOAD_PERMISSIONS = 0o640

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

MAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
    if PRODUCTION
    else "django.core.mail.backends.console.EmailBackend",
)
MAIL_OPTIONS = {}
if MAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    MAIL_OPTIONS = {
        "host": os.environ.get("SMTP_HOST", "localhost"),
        "port": int(os.environ.get("SMTP_PORT", "25")),
        "username": os.environ.get("SMTP_USERNAME", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "use_tls": env_bool("SMTP_USE_TLS"),
        "use_ssl": env_bool("SMTP_USE_SSL"),
        "timeout": int(os.environ.get("SMTP_TIMEOUT", "10")),
    }
MAILERS = {"default": {"BACKEND": MAIL_BACKEND, "OPTIONS": MAIL_OPTIONS}}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = bounded_int(
    "CELERY_TASK_SOFT_TIME_LIMIT", 300, minimum=1, maximum=3600
)
CELERY_TASK_TIME_LIMIT = bounded_int(
    "CELERY_TASK_TIME_LIMIT", 330, minimum=2, maximum=3600
)
if CELERY_TASK_SOFT_TIME_LIMIT >= CELERY_TASK_TIME_LIMIT:
    raise ValueError("CELERY_TASK_SOFT_TIME_LIMIT must be less than CELERY_TASK_TIME_LIMIT.")
CELERY_WORKER_CONCURRENCY = bounded_int(
    "CELERY_WORKER_CONCURRENCY", 2, minimum=1, maximum=4
)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", ENVIRONMENT == "test")
CELERY_TASK_EAGER_PROPAGATES = True

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", PRODUCTION)
SECURE_HSTS_SECONDS = int(
    os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000" if PRODUCTION else "0")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD")
if PRODUCTION:
    if not SECURE_SSL_REDIRECT:
        raise ValueError("DJANGO_SECURE_SSL_REDIRECT must be true in production.")
    if SECURE_HSTS_SECONDS < 1:
        raise ValueError("DJANGO_SECURE_HSTS_SECONDS must be positive in production.")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} {levelname} {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"}
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
