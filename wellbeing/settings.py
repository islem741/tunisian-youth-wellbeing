"""
Django settings for the Tunisian Student Early-Warning & Well-Being Platform.

This is a university exam project. The SECRET_KEY here is a development
placeholder only; in a real deployment it must come from the environment
and DEBUG must be False.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-u(q&)w#zp&#a-#5&qbu(%b(ls)(t10$0z2#0gr&owy386(#rp%",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_bootstrap5",
    "rest_framework",
    "strawberry.django",
    "accounts",
    "cases",
    "support",
    "dashboard",
    "gql",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wellbeing.middleware.RequestCorrelationMiddleware",
]

ROOT_URLCONF = "wellbeing.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.role_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "wellbeing.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "accounts:login"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Domain-specific configuration — Student Engagement Risk Score (SERS).
SERS_WEIGHTS = {
    "absence":    int(os.environ.get("SERS_WEIGHT_ABSENCE",    6)),
    "grade_drop": int(os.environ.get("SERS_WEIGHT_GRADE_DROP", 5)),
    "behavior":   int(os.environ.get("SERS_WEIGHT_BEHAVIOR",   8)),
    "wellbeing":  int(os.environ.get("SERS_WEIGHT_WELLBEING",  10)),
}
HIGH_RISK_THRESHOLD   = int(os.environ.get("HIGH_RISK_THRESHOLD",   65))
MEDIUM_RISK_THRESHOLD = int(os.environ.get("MEDIUM_RISK_THRESHOLD", 40))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation": {
            "()": "wellbeing.middleware.CorrelationFilter",
        },
    },
    "formatters": {
        "structured": {
            "format": (
                "%(asctime)s level=%(levelname)s "
                "correlation_id=%(correlation_id)s "
                "logger=%(name)s %(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["correlation"],
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "wellbeing": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
