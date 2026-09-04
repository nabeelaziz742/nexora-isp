import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY environment variable is required.")


def _csv_env(name, default=""):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


def _bool_env(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = _bool_env("DJANGO_DEBUG", False)
ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS", "127.0.0.1,localhost")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders", "rest_framework", "rest_framework_simplejwt.token_blacklist",
    "accounts", "tenancy", "onboarding", "customers", "network",
    "inventory", "billing", "accounting", "support", "field_operations", "notifications",
    "command_center", "revenue_intelligence", "reports", "communications",
]

MIDDLEWARE = [
    "tenancy.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ["DB_NAME"], "USER": os.environ["DB_USER"], "PASSWORD": os.environ["DB_PASSWORD"],
    "HOST": os.getenv("DB_HOST", "127.0.0.1"), "PORT": os.getenv("DB_PORT", "5432"),
}}

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v25.0")

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
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("tenancy.authentication.TenantJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("ANON_THROTTLE_RATE", "100/minute"),
        "user": os.getenv("USER_THROTTLE_RATE", "1000/hour"),
        "login": os.getenv("LOGIN_THROTTLE_RATE", "5/minute"),
        "copilot": os.getenv("COPILOT_THROTTLE_RATE", "10/minute"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "1"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ------------------------------------------------------------------------------
# CELERY & CELERY BEAT BACKGROUND AUTOMATION
# ------------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
CELERY_TASK_ALWAYS_EAGER = _bool_env("CELERY_TASK_ALWAYS_EAGER", True)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "dispatch-communication-queue": {
        "task": "communications.tasks.dispatch_communication_queue_task",
        "schedule": 60.0,
    },
    "recover-stale-communication-queue": {
        "task": "communications.tasks.recover_stale_processing_task",
        "schedule": 600.0,
    },
    "daily-scan-overdue-invoices": {
        "task": "billing.tasks.scan_overdue_invoices_task",
        "schedule": crontab(hour=1, minute=0),
    },
    "daily-scan-ptp-breaches": {
        "task": "billing.tasks.scan_ptp_breaches_task",
        "schedule": crontab(hour=2, minute=0),
    },
}

# ------------------------------------------------------------------------------
# CACHING (REDIS WITH LOCMEM FALLBACK)
# ------------------------------------------------------------------------------
if os.getenv("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
            "KEY_PREFIX": "nexora",
            "TIMEOUT": 300,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nexora-locmem-cache",
            "KEY_PREFIX": "nexora",
            "TIMEOUT": 300,
        }
    }

# ------------------------------------------------------------------------------
# OBSERVABILITY & STRUCTURED LOGGING
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "tenancy.logging.RequestIDFilter",
        },
    },
    "formatters": {
        "structured": {
            "format": "[%(asctime)s] [%(levelname)s] [req_id=%(request_id)s] [%(name)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "nexora": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

TEST_RUNNER = "config.test_runner.NexoraTestRunner"

CORS_ALLOWED_ORIGINS = _csv_env("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _csv_env("CSRF_TRUSTED_ORIGINS")

# ------------------------------------------------------------------------------
# EMAIL & SMTP DELIVERY CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587" if os.getenv("EMAIL_HOST") == "smtp.gmail.com" else "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _bool_env("EMAIL_USE_TLS", True if (os.getenv("EMAIL_PORT") == "587" or os.getenv("EMAIL_HOST") == "smtp.gmail.com") else False)
EMAIL_USE_SSL = _bool_env("EMAIL_USE_SSL", False)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", os.getenv("EMAIL_HOST_USER") or "no-reply@nexora.local")

# Production security is opt-in through environment variables so local development remains HTTP-friendly.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = _bool_env("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = _bool_env("CSRF_COOKIE_SECURE", not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _bool_env("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = _bool_env("SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

