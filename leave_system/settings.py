import os
import dj_database_url
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-eye-hospital-leave-system-change-in-production-2024')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
    'https://web-production-777c4.up.railway.app',
    'http://web-production-777c4.up.railway.app',
    'https://hr.micei.org',
    'http://hr.micei.org',
    'https://www.hr.micei.org',
    'http://www.hr.micei.org',
]

# Explicit CSRF cookie age (1 year) — prevents Safari ITP from expiring it early
CSRF_COOKIE_AGE = 31449600

# Secure cookies — True in production (any non-DEBUG environment), False for local dev
CSRF_COOKIE_SECURE    = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

# SameSite=Lax fixes CSRF 403 on mobile browsers (avoids over-blocking POST requests)
CSRF_COOKIE_SAMESITE    = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'

# Timeout sessions after 8 hours of inactivity (enterprise: reduces hijack window)
SESSION_COOKIE_AGE = 28800

# HTTPS security headers — only meaningful when behind the Railway HTTPS proxy
SECURE_PROXY_SSL_HEADER     = ('HTTP_X_FORWARDED_PROTO', 'https') if not DEBUG else None
SECURE_HSTS_SECONDS         = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'

# Read early so INSTALLED_APPS and storage can be configured conditionally
CLOUDINARY_URL = config('CLOUDINARY_URL', default=None)

_cloudinary_apps = ['cloudinary_storage', 'cloudinary'] if (CLOUDINARY_URL and CLOUDINARY_URL.startswith('cloudinary://')) else []

INSTALLED_APPS = [
    'anymail',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    *_cloudinary_apps,
    'accounts',
    'leaves',
    'dashboard',
    'discipline',
    'contracts',
    'notifications',
    'appraisals',
    'payroll',
    'recognition',
    'recruitment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'leave_system.urls'

_TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.cached.Loader', _TEMPLATE_LOADERS)
            ] if not DEBUG else _TEMPLATE_LOADERS,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'notifications.context_processors.notifications_ctx',
                'dashboard.context_processors.system_settings_ctx',
            ],
        },
    },
]

WSGI_APPLICATION = 'leave_system.wsgi.application'

DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Cloudinary (media file storage) ─────────────────────────────────────────
# Set CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name in Railway env vars.
# Without it, falls back to local media storage (dev only).
if CLOUDINARY_URL and CLOUDINARY_URL.startswith('cloudinary://'):
    from urllib.parse import urlparse as _urlparse
    _c = _urlparse(CLOUDINARY_URL)
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': _c.hostname,
        'API_KEY':    _c.username,
        'API_SECRET': _c.password,
    }
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Email Configuration ─────────────────────────────────────────────────────
# Set EMAIL_NOTIFICATIONS_ENABLED=True and configure SMTP env vars to send emails.
# For local dev, emails are printed to the console when DEBUG=True.
EMAIL_NOTIFICATIONS_ENABLED = config('EMAIL_NOTIFICATIONS_ENABLED', default=False, cast=bool)

_resend_key = config('RESEND_API_KEY', default='')

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif _resend_key:
    EMAIL_BACKEND = 'anymail.backends.resend.EmailBackend'
else:
    # SMTP fallback (Hostinger Business Email or any SMTP provider)
    EMAIL_BACKEND  = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST     = config('EMAIL_HOST',     default='smtp.hostinger.com')
    EMAIL_PORT     = config('EMAIL_PORT',     default=587, cast=int)
    EMAIL_USE_TLS  = config('EMAIL_USE_TLS',  default=True, cast=bool)
    EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

ANYMAIL = {
    'RESEND_API_KEY': _resend_key,
}

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='AEF HRM <pm@hr.micei.org>')
# Public URL used in email notification links
SITE_URL = config('SITE_URL', default='https://hr.micei.org')

# ── WhatsApp / Twilio Configuration ─────────────────────────────────────────
# Set WHATSAPP_NOTIFICATIONS_ENABLED=True and configure Twilio env vars.
# TWILIO_WHATSAPP_FROM: your Twilio WhatsApp sender (e.g. whatsapp:+14155238886)
WHATSAPP_NOTIFICATIONS_ENABLED = config('WHATSAPP_NOTIFICATIONS_ENABLED', default=False, cast=bool)
TWILIO_ACCOUNT_SID   = config('TWILIO_ACCOUNT_SID',   default='')
TWILIO_AUTH_TOKEN    = config('TWILIO_AUTH_TOKEN',     default='')
TWILIO_WHATSAPP_FROM = config('TWILIO_WHATSAPP_FROM',  default='whatsapp:+14155238886')

# ── Authentication ───────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
