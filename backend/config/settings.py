"""
Django settings for Candidate Intelligence Platform (standalone).

This project is fully self-contained — all pipeline, lc, models, and
storage modules are bundled inside the backend/ directory.

Reads configuration from backend/.env  (copy .env.example → .env).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent   # backend/

# Load .env from the backend directory
load_dotenv(BASE_DIR / ".env")

# ── Security ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key-change-in-production")
DEBUG      = os.getenv("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

# ── Installed apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "corsheaders",
    "candidates",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ── No Django ORM — MongoDB is handled directly via PyMongo ───────────────────
DATABASES = {}

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_METHODS     = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
CORS_ALLOW_HEADERS     = ["*"]

# ── Django REST Framework ──────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

# ── Static ─────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
