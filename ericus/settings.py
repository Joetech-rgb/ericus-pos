"""
Django settings for ericus project.
Electrical & Home Appliance POS System
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ─────────────────────────────────────────────────────────────────
# Read from environment variable; fall back to dev key ONLY in development.
# On the client machine, set this in a .env file or as a system env var.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-vny@&2poqu1p2834w-5naq&(%8tex8vj3417z%7cpysv6a@jgk'  # dev only
)

# Set DJANGO_DEBUG=0 in production to disable debug mode
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = ['*']   # Fine for offline/LAN use; restrict to IP if needed


# ─── Applications ─────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Local apps
    'accounts',
    'products',
    'inventory',
    'purchases',
    'sales',
    'customers',
    'wholesale',
    'discounts',
    'expenses',
    'returns',
    'audit',
    'reports',
    'crispy_forms',
    'crispy_bootstrap5',
]


# ─── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',     # ← serves static files without DEBUG=True
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',
    'accounts.middleware.UserSessionMiddleware',
]

ROOT_URLCONF = 'ericus.urls'


# ─── Templates ────────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.shop_profile',
                'accounts.context_processors.users_online',
            ],
        },
    },
]

WSGI_APPLICATION = 'ericus.wsgi.application'


# ─── Database ─────────────────────────────────────────────────────────────────

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ─── Auth ─────────────────────────────────────────────────────────────────────

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ─── Internationalisation ─────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Accra'
USE_I18N = True
USE_TZ = True


# ─── Static Files ─────────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise: compress and cache static files for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ─── Media Files ──────────────────────────────────────────────────────────────

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ─── PIN Settings ─────────────────────────────────────────────────────────────

PIN_MAX_ATTEMPTS = 3
PIN_LOCKOUT_MINUTES = 30


# ─── Session ──────────────────────────────────────────────────────────────────

SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True


# ─── User Online Tracker ──────────────────────────────────────────────────────

USER_ONLINE_TIMEOUT = 5


# ─── Default primary key ──────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─── Currency ─────────────────────────────────────────────────────────────────

CURRENCY_CODE = 'GHS'
CURRENCY_SYMBOL = 'GH₵'


# ─── Crispy Forms ─────────────────────────────────────────────────────────────

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'