"""Fast, isolated settings for the Django test suite."""

from .settings import *  # noqa: F403

ENVIRONMENT = "test"
PRODUCTION = False
CELERY_TASK_ALWAYS_EAGER = True


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    },
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

