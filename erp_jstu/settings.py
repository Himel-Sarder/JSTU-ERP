"""
Django settings for the JSTU ERP (ERP-JSTU).

Jamalpur Science and Technology University - Enterprise Resource Planning System
Reference: JSTU_ERP_Project_Proposal.docx (Sections 8, 10 and 13).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
# In production, export these instead of editing the file:
#   JSTU_SECRET_KEY, JSTU_DEBUG=0, JSTU_ALLOWED_HOSTS="erp.jstu.edu.bd,www.jstu.edu.bd"
SECRET_KEY = os.environ.get(
    "JSTU_SECRET_KEY",
    "django-insecure-jstu-erp-change-this-key-before-production-deploy",
)
DEBUG = os.environ.get("JSTU_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("JSTU_ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # JSTU ERP apps
    "accounts",
    "academics",
    "portal",
    "studentpanel",
    "teacherpanel",
    "adminpanel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Entry gate: e-mail + 6-digit passkey must be cleared before any panel opens
    "accounts.middleware.PasskeyGateMiddleware",
]

ROOT_URLCONF = "erp_jstu.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.university",
                "studentpanel.context_processors.alerts",
            ],
        },
    },
]

WSGI_APPLICATION = "erp_jstu.wsgi.application"

# --------------------------------------------------------------------------
# Database - SQLite for development; switch to PostgreSQL/MySQL in production
# (Proposal section 10 recommends MySQL or PostgreSQL for the data layer.)
# --------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Localisation - Bangladesh
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static & media
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Entry-gate / session policy (Proposal section 13 - Security & Data Privacy)
# --------------------------------------------------------------------------
LOGIN_URL = "accounts:gate"
GATE_SESSION_KEY = "jstu_gate_cleared"
GATE_MAX_ATTEMPTS = 5           # lock the passkey after this many wrong codes
GATE_LOCKOUT_MINUTES = 15       # how long the lock lasts
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "SAMEORIGIN"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# University identity used across every template
# (reaches templates as `jstu` via accounts.context_processors.university)
JSTU = {
    "NAME": "Jamalpur Science and Technology University",
    "SHORT_NAME": "JSTU",
    "LOCATION": "Jamalpur, Bangladesh",
    "SYSTEM": "Enterprise Resource Planning System",
    "OWNER": "ICT Cell, JSTU",
    "LOGO_URL": "https://i.postimg.cc/Yqzj3c8Q/image.png",
}

# --------------------------------------------------------------------------
# Production hardening (Proposal section 13 - HTTPS/TLS)
# These switch on automatically once JSTU_DEBUG=0 is exported, so the
# development server stays usable over plain HTTP without any edits.
# --------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000          # one year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"
    CSRF_TRUSTED_ORIGINS = [
        f"https://{host}" for host in ALLOWED_HOSTS if host not in ("*", "")
    ]
