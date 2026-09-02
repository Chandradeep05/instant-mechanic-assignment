"""
Django settings for Instant Mechanic LiveOps Dashboard.

Security policy:
  - In production (DEBUG=False), SECRET_KEY and ALLOWED_HOSTS MUST be set via environment variables.
  - The application will raise ImproperlyConfigured if these are absent in production.
  - DEBUG defaults to False (fail-closed). Set DEBUG=True explicitly for local development.
"""
import os
import sys
import urllib.parse
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# --- DEBUG ---
# Fail-closed: defaults to False. Must be explicitly set True for local dev.
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# --- SECRET KEY ---
# In production, SECRET_KEY must be provided via environment variable. No hardcoded fallback.
_secret_key_default = 'django-insecure-liveops-dev-only-not-for-production-2026' if DEBUG else None
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', _secret_key_default)
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable is required in production. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(50))\""
    )

# --- ALLOWED HOSTS ---
_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*' if DEBUG else '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()] if _allowed_hosts_env else []

# Auto-detect Render deployment hostname
render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if render_host and render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_host)

# Allow all onrender.com subdomains if deployed on Render or if ALLOWED_HOSTS has wildcard
if render_host or '.onrender.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.onrender.com')

if not ALLOWED_HOSTS and not DEBUG:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS environment variable is required in production. "
        "Example: ALLOWED_HOSTS=instant-mechanic.example.com,api.instant-mechanic.com"
    )

if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

# Application definition
INSTALLED_APPS = [
    'daphne',  # Must be first for ASGI/Channels support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party packages
    'rest_framework',
    'corsheaders',
    'channels',
    'drf_spectacular',

    # Local apps
    'apps.common',
    'apps.customers',
    'apps.mechanics',
    'apps.bookings',
    'apps.dashboard',
    'apps.demo',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Top for CORS
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# --- DATABASE ---
# Supports SQLite (default), PostgreSQL via DATABASE_URL or POSTGRES_* env vars.
# Decodes URL-encoded credentials and handles sslmode for Supabase/AWS RDS.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if os.environ.get('DATABASE_URL', '').strip():
    url = urllib.parse.urlparse(os.environ['DATABASE_URL'].strip())
    query_params = urllib.parse.parse_qs(url.query)

    db_config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': url.path[1:] if url.path.startswith('/') else url.path,
        'USER': urllib.parse.unquote(url.username or ''),
        'PASSWORD': urllib.parse.unquote(url.password or ''),
        'HOST': url.hostname or 'localhost',
        'PORT': url.port or 5432,
        'CONN_MAX_AGE': 60,
    }

    ssl_mode = query_params.get('sslmode', [''])[0]
    if ssl_mode or 'supabase' in (url.hostname or '') or 'amazonaws' in (url.hostname or ''):
        db_config['OPTIONS'] = {'sslmode': ssl_mode or 'require'}

    DATABASES['default'] = db_config

elif os.environ.get('POSTGRES_DB'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'instant_mechanic'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }

# --- CHANNELS LAYER ---
if os.environ.get('REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [os.environ['REDIS_URL']],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'en-in'
# Fixed from UTC: Instant Mechanic is an Indian company. "Today" resets at midnight IST (UTC+5:30).
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- DJANGO REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.common.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# --- API DOCUMENTATION ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'Instant Mechanic LiveOps API',
    'DESCRIPTION': (
        'Real-time operations dashboard API for Instant Mechanic ops team.\n\n'
        '**Note:** Authentication and RBAC are intentionally excluded from this assignment scope. '
        'All operational mutation endpoints must be protected by role-based authentication in production.'
    ),
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# --- CORS ---
CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    cors_allowed = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [o.strip() for o in cors_allowed.split(',') if o.strip()] if cors_allowed else []
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^https://.*\.vercel\.app$",
        r"^http://localhost:\d+$",
    ]

# --- SECURITY HEADERS (production) ---
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Cookie security — only effective over HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS: set to 1 hour initially; increase to 31536000 (1 year) after validating HTTPS works
    # Note: EC2+Nginx handles SSL termination, so SECURE_SSL_REDIRECT should stay False.
    # The proxy-header above signals Django that the original request was HTTPS.
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False  # Do NOT set True until you're confident in your HTTPS setup
    SECURE_SSL_REDIRECT = False  # Nginx/load balancer handles redirect, not Django
