import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Set UTF-8 encoding in OS environment if supported
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Load .env file safely
try:
    load_dotenv(BASE_DIR / '.env')
except Exception:
    pass

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-softobrocashbook-dev-secret-key-2026')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

hosts_str = os.getenv('ALLOWED_HOSTS', '*')
if hosts_str == '*' or not hosts_str:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [h.strip() for h in hosts_str.split(',') if h.strip()]

# Ensure current production domains are always allowed
for h in ['cashbook.softobro.com', '.softobro.com', 'localhost', '127.0.0.1']:
    if h not in ALLOWED_HOSTS and '*' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(h)

CSRF_TRUSTED_ORIGINS = [
    'https://cashbook.softobro.com',
    'http://cashbook.softobro.com',
    'https://*.softobro.com',
]

AUTH_USER_MODEL = 'accounts.User'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',

    # Project Apps
    'accounts.apps.AccountsConfig',
    'core.apps.CoreConfig',
    'subscriptions.apps.SubscriptionsConfig',
    'payments.apps.PaymentsConfig',
    'tenants.apps.TenantsConfig',
    'businesses.apps.BusinessesConfig',
    'cashbooks.apps.CashbooksConfig',
    'transactions.apps.TransactionsConfig',
    'reports.apps.ReportsConfig',
    'notifications.apps.NotificationsConfig',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tenants.middleware.TenantMiddleware',
]

ROOT_URLCONF = 'softobrocashbook.urls'

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
                'core.context_processors.site_settings',
                'notifications.context_processors.notification_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'softobrocashbook.wsgi.application'

# Database configuration
CENTRAL_DB_ENGINE = os.getenv('CENTRAL_DB_ENGINE', 'django.db.backends.postgresql')

# Resolve 'localhost' to '127.0.0.1' to force IPv4 — cPanel servers often resolve
# 'localhost' to ::1 (IPv6) which is blocked by pg_hba.conf on shared hosting.
_central_db_host = os.getenv('CENTRAL_DB_HOST', '127.0.0.1').strip()
if _central_db_host.lower() == 'localhost':
    _central_db_host = '127.0.0.1'

DATABASES = {
    'default': {
        'ENGINE': CENTRAL_DB_ENGINE,
        'NAME': os.getenv('CENTRAL_DB_NAME', 'softobrocashbook_central'),
        'USER': os.getenv('CENTRAL_DB_USER', 'postgres'),
        'PASSWORD': os.getenv('CENTRAL_DB_PASSWORD', 'postgres'),
        'HOST': _central_db_host,
        'PORT': os.getenv('CENTRAL_DB_PORT', '5432'),
        'OPTIONS': {
            # Ensure TCP connections use IPv4 on cPanel/shared hosting
            'connect_timeout': 10,
        },
    }
}

DATABASE_ROUTERS = ['tenants.router.TenantDatabaseRouter']

# Tenant provisioning parameters - automatically sanitize placeholders from .env
_t_host = os.getenv('TENANT_DB_HOST', '').strip()
if not _t_host or _t_host.lower() in ('localhost', 'none', ''):
    TENANT_DB_HOST = _central_db_host  # already resolved to 127.0.0.1 if was localhost
else:
    TENANT_DB_HOST = _t_host
# Always force IPv4 — cPanel resolves 'localhost' to ::1 which is rejected by pg_hba.conf
if TENANT_DB_HOST.lower() == 'localhost':
    TENANT_DB_HOST = '127.0.0.1'

_t_port = os.getenv('TENANT_DB_PORT', '').strip()
TENANT_DB_PORT = int(_t_port if _t_port.isdigit() else os.getenv('CENTRAL_DB_PORT', 5432))

_t_user = os.getenv('TENANT_DB_SUPER_USER', '').strip()
if not _t_user or _t_user in ('your_postgres_admin', 'postgres'):
    TENANT_DB_SUPER_USER = os.getenv('CENTRAL_DB_USER', 'postgres')
else:
    TENANT_DB_SUPER_USER = _t_user

_t_pass = os.getenv('TENANT_DB_SUPER_PASSWORD', '').strip()
if not _t_pass or _t_pass in ('your_postgres_admin_password', 'postgres'):
    TENANT_DB_SUPER_PASSWORD = os.getenv('CENTRAL_DB_PASSWORD', 'postgres')
else:
    TENANT_DB_SUPER_PASSWORD = _t_pass

TENANT_DB_PREFIX = os.getenv('TENANT_DB_PREFIX', 'scb_tenant_')

# Safe Fernet encryption key - auto-derive valid 32 url-safe base64 key if .env key is malformed
_raw_enc_key = os.getenv('ENCRYPTION_KEY', '').strip()
if _raw_enc_key:
    try:
        from cryptography.fernet import Fernet
        Fernet(_raw_enc_key.encode())
        ENCRYPTION_KEY = _raw_enc_key
    except Exception:
        import base64, hashlib
        ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(_raw_enc_key.encode()).digest()).decode()
else:
    ENCRYPTION_KEY = 'b5q3L9DVOgq27l6htokTAYMt3nC3R3pzZu1WonV18mk='

# bKash manual payment details
BKASH_COMPANY_NUMBER = os.getenv('BKASH_COMPANY_NUMBER', '01712345678')
BKASH_ACCOUNT_TYPE = os.getenv('BKASH_ACCOUNT_TYPE', 'Merchant / Personal')
BKASH_INSTRUCTIONS = os.getenv(
    'BKASH_INSTRUCTIONS',
    'Please send money or payment to the bKash number provided. After sending, enter your TrxID below for instant verification.'
)

# Site parameters
SITE_NAME = os.getenv('SITE_NAME', 'SoftobroCashBook')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@softobrocashbook.com')
SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '+880 1700-000000')
CURRENCY_SYMBOL = '\u09f3'  # Bengali Taka symbol ৳

# Authentication & Passwords
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard_redirect'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings (for mobile app)
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS — allow React Native app and the web dashboard
CORS_ALLOWED_ORIGINS = [
    'https://cashbook.softobro.com',
    'http://localhost:8081',   # Expo / Metro bundler
    'http://localhost:3000',
    'http://127.0.0.1:8000',
]
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL', 'False').lower() in ('true', '1')
CORS_ALLOW_CREDENTIALS = True

# DRF Spectacular API docs
SPECTACULAR_SETTINGS = {
    'TITLE': 'SoftobroCashBook API',
    'DESCRIPTION': 'REST API for the SoftobroCashBook mobile application (React Native). Provides JWT auth, dashboard, businesses, cashbooks, transactions, subscriptions, and notifications.',
    'VERSION': 'v1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Logging Configuration
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': str(LOGS_DIR / 'django_error.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
