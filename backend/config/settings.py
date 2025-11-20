from pathlib import Path
import os
from decimal import Decimal
from dotenv import dotenv_values
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Загружаем переменные окружения из .env (без ошибок на посторонние строки)
# .env в корне проекта; резервно — backend/.env
PROJECT_ROOT = BASE_DIR.parent
for _env_path in (PROJECT_ROOT / ".env", BASE_DIR / ".env"):
    try:
        if _env_path.exists():
            for k, v in dotenv_values(_env_path).items():
                if k and v is not None and k not in os.environ:
                    os.environ[k] = str(v)
    except Exception:
        # Игнорируем любые ошибки парсинга отдельных строк
        pass

# (Удалено) Опасный ранний импорт модулей приложений.
# Ранее здесь создавались двусторонние алиасы импортов для `backend.*` и без префикса,
# что приводило к выполнению кода моделей до инициализации реестра приложений Django.
# Это вызывало ошибку: "Model ... isn't in an application in INSTALLED_APPS".
# Если необходима обратная совместимость путей импортов, её следует решать вне settings
# и без раннего импорта моделей.

# YooKasa settings
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_WEBHOOK_URL = os.getenv("YOOKASSA_WEBHOOK_URL")

# Frontend URL for payment redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '5.129.249.206', 'the-bot.ru', 'www.the-bot.ru']  # Добавлен публичный IP сервера и домены

# Telegram Bot settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Backward compatibility / default chat
TELEGRAM_PUBLIC_CHAT_ID = os.getenv("TELEGRAM_PUBLIC_CHAT_ID", TELEGRAM_CHAT_ID)
TELEGRAM_LOG_CHAT_ID = os.getenv("TELEGRAM_LOG_CHAT_ID", TELEGRAM_CHAT_ID)

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sobptsqfzgycmauglqzk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNvYnB0c3Fmemd5Y21hdWdscXprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjEyMDYxNzEsImV4cCI6MjA3Njc4MjE3MX0.OTJTYuazN2AEbcFlnHrt5ux7w-syOB90lTx3FLT2s4k")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Production security validation
if not DEBUG:
    if len(SECRET_KEY) < 50:
        raise ImproperlyConfigured(
            "SECRET_KEY must be at least 50 characters in production. "
            "Generate a secure key using: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
        )
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured("ALLOWED_HOSTS must be set in production")
    if SECRET_KEY.startswith('django-insecure-'):
        raise ImproperlyConfigured("SECRET_KEY must not use the default insecure key in production")

# Security settings for HTTPS behind reverse proxy (nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Production security settings (only when DEBUG=False)
if not DEBUG:
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # SSL/HTTPS enforcement
    SECURE_SSL_REDIRECT = True

    # Secure cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Additional security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# Application definition

INSTALLED_APPS = [
    'daphne',  # ASGI server для WebSocket
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'channels',  # Django Channels для WebSocket
    'core',
    'accounts',
    'materials',
    'assignments',
    'chat',
    'reports',
    'notifications',
    'payments',
    'applications',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

def _build_db_from_env() -> dict:
    """Собирает конфиг БД из переменных окружения.

    Поддерживает два варианта:
    1) DATABASE_URL (postgres URI)
    2) Набор SUPABASE_DB_{NAME,USER,PASSWORD,HOST,PORT}

    Если параметры не заданы — выбрасывает ImproperlyConfigured с понятным сообщением.
    """
    # Настройки таймаутов для предотвращения зависания
    connect_timeout = int(os.getenv('DB_CONNECT_TIMEOUT', '10'))  # 10 секунд по умолчанию
    sslmode = os.getenv('DB_SSLMODE', 'require')
    
    # База данных опций с таймаутами
    db_options = {
        'connect_timeout': str(connect_timeout),
    }
    
    # Добавляем SSL режим если указан
    if sslmode:
        db_options['sslmode'] = sslmode
    
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in ('postgres', 'postgresql'):
            raise ImproperlyConfigured('DATABASE_URL должен быть Postgres URI (postgres:// или postgresql://)')
        
        # Если в URL уже есть параметры, добавляем timeout
        db_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': str(parsed.port or '5432'),
            'CONN_MAX_AGE': 0,  # Отключаем пул соединений
            'OPTIONS': db_options.copy(),
        }
        return db_config

    name = os.getenv('SUPABASE_DB_NAME')
    user = os.getenv('SUPABASE_DB_USER')
    password = os.getenv('SUPABASE_DB_PASSWORD')
    host = os.getenv('SUPABASE_DB_HOST')
    port = os.getenv('SUPABASE_DB_PORT')

    if all([name, user, password, host]):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': name,
            'USER': user,
            'PASSWORD': password,
            'HOST': host,
            'PORT': str(port or '6543'),
            'CONN_MAX_AGE': 0,  # Отключаем пул соединений
            'OPTIONS': db_options.copy(),
        }

    raise ImproperlyConfigured(
        'Не заданы параметры подключения к БД. Установите DATABASE_URL (postgres URI) '
        'или переменные SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, SUPABASE_DB_HOST, SUPABASE_DB_PORT.'
    )


# Всегда используем PostgreSQL (Supabase) во всех средах
DATABASES = {
    'default': _build_db_from_env(),
}

# Применяем патч для установки таймаутов подключения
# Это нужно делать после определения DATABASES, но до использования
try:
    from django.db.backends.postgresql.base import DatabaseWrapper
    
    if not hasattr(DatabaseWrapper, '_timeout_patched'):
        _original_get_new_connection = DatabaseWrapper.get_new_connection
        
        def get_new_connection_with_timeout(self, conn_params):
            """Обертка для установки таймаута подключения"""
            connect_timeout = int(os.getenv('DB_CONNECT_TIMEOUT', '10'))
            # Устанавливаем таймаут в параметрах подключения psycopg2
            if 'connect_timeout' not in conn_params:
                conn_params['connect_timeout'] = connect_timeout
            return _original_get_new_connection(self, conn_params)
        
        DatabaseWrapper.get_new_connection = get_new_connection_with_timeout
        DatabaseWrapper._timeout_patched = True
except (ImportError, AttributeError):
    # Если не удалось применить патч, продолжаем без него
    pass


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 hours
# SESSION_COOKIE_SECURE управляется через условие DEBUG выше
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # Allow cookies on redirect from YooKassa (not 'Strict')
SESSION_COOKIE_DOMAIN = '.the-bot.ru' if not DEBUG else None  # Allow cookies across subdomains in production
SESSION_SAVE_EVERY_REQUEST = True

# CSRF settings
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow CSRF cookies on redirect from YooKassa
# CSRF_COOKIE_SECURE управляется через условие DEBUG выше
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript access
CSRF_COOKIE_DOMAIN = '.the-bot.ru' if not DEBUG else None  # Allow cookies across subdomains in production


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://5.129.249.206",
    "https://5.129.249.206",
    "https://the-bot.ru",
    "https://www.the-bot.ru",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Используем CORS_ALLOWED_ORIGINS вместо allow all

# Дополнительные CORS настройки для разработки
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Cache settings
# Настройки кэширования
USE_REDIS_CACHE = os.getenv('USE_REDIS_CACHE', 'False').lower() == 'true'

if USE_REDIS_CACHE:
    # Используем Redis для кэширования
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        },
        'dashboard': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/2'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        },
        'chat': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/3'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    # Используем локальное кэширование в памяти (для разработки)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        },
        'dashboard': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'dashboard-cache',
        },
        'chat': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'chat-cache',
        }
    }

# Cache timeouts (in seconds)
CACHE_TIMEOUTS = {
    'dashboard_data': 300,  # 5 minutes
    'student_materials': 600,  # 10 minutes
    'teacher_students': 900,  # 15 minutes
    'parent_children': 1200,  # 20 minutes
    'chat_messages': 60,  # 1 minute
    'progress_stats': 300,  # 5 minutes
}

# Backup settings
BACKUP_DIR = os.getenv('BACKUP_DIR', '/tmp/backups')
MAX_BACKUPS = int(os.getenv('MAX_BACKUPS', '30'))

# System monitoring settings
SYSTEM_MONITORING = {
    'ENABLED': True,
    'METRICS_CACHE_TIMEOUT': 60,  # 1 minute
    'HEALTH_CHECK_TIMEOUT': 30,  # 30 seconds
    'ALERT_THRESHOLDS': {
        'CPU_WARNING': 80,
        'CPU_CRITICAL': 95,
        'MEMORY_WARNING': 80,
        'MEMORY_CRITICAL': 90,
        'DISK_WARNING': 80,
        'DISK_CRITICAL': 90,
        'DB_RESPONSE_WARNING': 1000,  # ms
        'DB_RESPONSE_CRITICAL': 5000,  # ms
    }
}

# Django Channels settings
# Используем Redis для production, InMemory для разработки (если Redis недоступен)
USE_REDIS_CHANNELS = os.getenv('USE_REDIS_CHANNELS', 'False').lower() == 'true'

if USE_REDIS_CHANNELS:
    # Используем Redis для каналов (production)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')],
            },
        },
    }
else:
    # Используем InMemory для разработки (не требует Redis)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# WebSocket settings
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', 'ws://localhost:8000/ws/')
WEBSOCKET_AUTHENTICATION_TIMEOUT = 30  # seconds
WEBSOCKET_MESSAGE_MAX_LENGTH = 1024 * 1024  # 1MB

# Payment settings
# PAYMENT_DEVELOPMENT_MODE: режим разработки с минимальными суммами (1 руб) и частыми платежами (10 мин)
# Используется с live API ключом YooKassa, но с маленькими суммами для безопасности
PAYMENT_DEVELOPMENT_MODE = os.getenv('PAYMENT_DEVELOPMENT_MODE', 'False').lower() == 'true'
DEVELOPMENT_PAYMENT_AMOUNT = Decimal(os.getenv('DEVELOPMENT_PAYMENT_AMOUNT', '1.00'))  # 1 рубль в режиме разработки
PRODUCTION_PAYMENT_AMOUNT = Decimal(os.getenv('PRODUCTION_PAYMENT_AMOUNT', '5000.00'))  # 5000 рублей в обычном режиме
DEVELOPMENT_RECURRING_INTERVAL_MINUTES = int(os.getenv('DEVELOPMENT_RECURRING_INTERVAL_MINUTES', '10'))  # 10 минут в режиме разработки
PRODUCTION_RECURRING_INTERVAL_WEEKS = int(os.getenv('PRODUCTION_RECURRING_INTERVAL_WEEKS', '1'))  # 1 неделя в обычном режиме

# Celery settings
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'))
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'))
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 минут максимум на задачу
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Импортируем расписание периодических задач
from core.celery_config import CELERY_BEAT_SCHEDULE
