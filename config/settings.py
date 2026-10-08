"""
Django settings for the Teepresso platform.

Teepresso is an enterprise Web-to-Print & Corporate Gifting e-commerce platform
(built to the PRINTPROX specification, modelled on printmine.in).

SAFE BY DEFAULT
---------------
Dev runs on SQLite with DEBUG on. Every risky third-party integration is OFF by
default and only turns on when you set its env var with real credentials. Nothing
fakes a payment, sends a WhatsApp/SMS, or files an E-Way Bill until YOU enable it.

For production set: DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS,
and the POSTGRES_* / REDIS_URL vars. See deploy/README and RUN_AND_DEPLOY.md.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core -----------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-change-me-in-production"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED", "").split(",") if o.strip()
]

# --- Applications ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # local apps
    "core",
    "accounts",
    "products",
    "cart",
    "orders",
    "payments",
    "quotations",
    "blogs",
    "cms",
    "notifications",
    "dashboard",
    "storefront",
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
    "core.middleware.ActivityLogMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database -------------------------------------------------------------
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "teepresso"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Auth -----------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "storefront:index"

# --- I18N / TZ ------------------------------------------------------------
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- Static / Media -------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 2 weeks
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# --- Cache & Celery (Redis when REDIS_URL is set) -------------------------
REDIS_URL = os.environ.get("REDIS_URL", "")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": REDIS_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = not REDIS_URL  # run inline in dev (safe, no broker needed)

# --- Email (console backend by default => safe, prints to terminal) -------
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Teepresso <hello@teepresso.in>")

# ==========================================================================
# Business rules / brand (configurable)
# ==========================================================================
TEEPRESSO = {
    "BRAND": "Teepresso",
    "TAGLINE": "Corporate Gifting & Web-to-Print",
    "GST_RATE": 18,              # %
    "FREE_SHIP_OVER": 999,       # ₹ — free shipping threshold
    "SHIP_FLAT": 79,             # ₹ — flat shipping below threshold
    "EWAY_THRESHOLD": 50000,     # ₹ — E-Way Bill auto-trigger
    "BULK_FOLLOWUP_QTY": 300,    # pieces — bulk follow-up trigger
    "DELIVERY_DAYS": "5–7 days",
    "SUPPORT_PHONE": "+919999999999",   # used for wa.me links
    "SUPPORT_EMAIL": "support@teepresso.in",
    "CURRENCY": "₹",
}

# ==========================================================================
# SAFE-BY-DEFAULT integration switches. Each defaults to OFF. The site runs
# fully without any of these. Turn one ON only with real credentials.
# ==========================================================================
INTEGRATIONS = {
    # Direct UPI (PhonePe / Google Pay / Paytm / any UPI app + QR). This is a
    # "collect" flow: the customer pays your business VPA and submits the UPI
    # reference (UTR). The order is NEVER auto-marked paid — a staff member
    # confirms receipt against the bank/UPI statement. Safe to keep ON.
    "UPI": os.environ.get("UPI", "1") == "1",
    # Online card/UPI capture via Razorpay. OFF => checkout records an UNPAID
    # ENQUIRY (never a fake "paid" order). ON only with a real gateway connected.
    "RAZORPAY": os.environ.get("RAZORPAY", "0") == "1",
    # WhatsApp: 'link' = safe wa.me click-links | 'api' = Business API.
    "WHATSAPP_MODE": os.environ.get("WHATSAPP_MODE", "link"),
    # SMS: OFF => OTP/alerts are logged only (printed) instead of really sent.
    "SMS_API": os.environ.get("SMS_API", "0") == "1",
    # E-Way Bill: OFF => over-threshold orders FLAGGED for manual filing.
    "EWAY_API": os.environ.get("EWAY_API", "0") == "1",
    # OTP at registration / forgot-password. OFF => OTP shown on screen (dev).
    "OTP_VERIFY": os.environ.get("OTP_VERIFY", "0") == "1",
}

RAZORPAY = {
    "KEY_ID": os.environ.get("RAZORPAY_KEY_ID", ""),
    "KEY_SECRET": os.environ.get("RAZORPAY_KEY_SECRET", ""),
}

# --------------------------------------------------------------------------
# Business UPI account — where direct UPI payments are collected.
#
# The VPA (Virtual Payment Address, e.g. "yourbusiness@okhdfcbank") is NOT a
# secret — it is a public "receive money" handle, like an email address. But it
# MUST be correct and MUST live here in server config (env var), never typed by
# the customer, so no one can swap it for their own account. See UPI_PAYMENTS_
# GUIDE.md for how to obtain and safely wire your real VPA.
#
# The default below ("teepresso@upi") is an obvious placeholder that lets the UI
# render in dev; it is not a real account and cannot receive money. Set the env
# var BUSINESS_UPI_VPA to go live.
# --------------------------------------------------------------------------
_UPI_PLACEHOLDER = "teepresso@upi"
BUSINESS_UPI = {
    "VPA": os.environ.get("BUSINESS_UPI_VPA", _UPI_PLACEHOLDER).strip(),
    "PAYEE_NAME": os.environ.get("BUSINESS_UPI_NAME", TEEPRESSO["BRAND"]).strip(),
    # Optional GST/merchant code shown on the payment note; purely cosmetic.
    "MERCHANT_CODE": os.environ.get("BUSINESS_UPI_MCC", "").strip(),
}
# True while the placeholder is in use — templates show a "demo VPA" banner.
BUSINESS_UPI["IS_PLACEHOLDER"] = BUSINESS_UPI["VPA"] in ("", _UPI_PLACEHOLDER)
WHATSAPP = {
    "TOKEN": os.environ.get("WHATSAPP_TOKEN", ""),
    "PHONE_ID": os.environ.get("WHATSAPP_PHONE_ID", ""),
}

# --- Production hardening (auto-applied when DEBUG is off) -----------------
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
