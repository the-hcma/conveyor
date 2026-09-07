"""Django settings for the Conveyor service.

Environment-driven (12-factor). Local dev reads a `.env` file if present; the
systemd units on the host inject the same variables. See `.env.example` and
AGENTS.md. No secret has a default — a missing required variable fails loudly.
"""

from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = _bool("CONVEYOR_DEBUG")

# A real key must be injected in every non-DEBUG deploy. The insecure fallback
# carries Django's "django-insecure-" marker so `conveyor.apps.core.checks`
# (conveyor.E001, a normal system check run by every `manage.py` command) fails
# when a non-DEBUG process boots on it.
SECRET_KEY = os.environ.get("CONVEYOR_SECRET_KEY") or "django-insecure-local-dev-only"

ALLOWED_HOSTS = _csv("CONVEYOR_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = _csv("CONVEYOR_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "conveyor.apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "conveyor.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "conveyor.wsgi.application"
ASGI_APPLICATION = "conveyor.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        # Re-validate a pooled connection at the start of each request and
        # reconnect if it died (e.g. Postgres restart) instead of serving errors
        # from a dead connection until CONN_MAX_AGE elapses.
        conn_health_checks=True,
    ),
}

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

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
}

# --- Conveyor-specific (consumed in later milestones) -------------------------

# GitHub App webhook shared secret; ingestion rejects any request that fails the
# X-Hub-Signature-256 check against this value (M2).
CONVEYOR_WEBHOOK_SECRET = os.environ.get("CONVEYOR_WEBHOOK_SECRET", "")

# How long a delivery stays in the Postgres hot tier before it is pruned (it
# lives on in Redpanda). ISO-8601-ish "<n>d" / "<n>h"; parsed in M2.
CONVEYOR_HOT_WINDOW = os.environ.get("CONVEYOR_HOT_WINDOW", "14d")

# Redpanda / Kafka bootstrap servers (M3).
CONVEYOR_KAFKA_BOOTSTRAP = os.environ.get("CONVEYOR_KAFKA_BOOTSTRAP", "")
