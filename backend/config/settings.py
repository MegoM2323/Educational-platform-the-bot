# CRITICAL: Apply Python 3.13 compatibility patch FIRST
# Должен быть импортирован до любых других библиотек
try:
    from config import hyperframe_patch
except ImportError:
    pass

from pathlib import Path
import os
import sys
from decimal import Decimal
from dotenv import dotenv_values
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

# Import environment configuration service
from core.environment import EnvConfig

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Загружаем переменные окружения из .env (без ошибок на посторонние строки)
# .env в корне проекта; резервно — backend/.env
# КРИТИЧНО: Не перезаписываем ENVIRONMENT если уже установлен (например, pytest-env)
PROJECT_ROOT = BASE_DIR.parent
_current_environment = os.environ.get('ENVIRONMENT')
for _env_path in (PROJECT_ROOT / ".env", BASE_DIR / ".env"):
    try:
        if _env_path.exists():
            for k, v in dotenv_values(_env_path).items():
                if k and v is not None and k not in os.environ:
                    os.environ[k] = str(v)
    except Exception:
        # Игнорируем любые ошибки парсинга отдельных строк
        pass

# Восстановить ENVIRONMENT если он был установлен до загрузки .env
# Это критично для pytest (pytest-env устанавливает ENVIRONMENT=test)
if _current_environment is not None:
    os.environ['ENVIRONMENT'] = _current_environment

# Initialize Sentry for error tracking (MUST be before any imports of other modules)
try:
    from config.sentry import init_sentry
    init_sentry(sys.modules[__name__])
except Exception as e:
    import sys
    print(f'[Warning] Failed to initialize Sentry: {e}', file=sys.stderr)

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

# Initialize environment configuration (must be after os.environ is populated from .env)
env_config = EnvConfig()

# Frontend URL for payment redirects and frontend configuration
FRONTEND_URL = env_config.get_frontend_url()

# Allowed hosts based on environment (development, production, or test)
ALLOWED_HOSTS = env_config.get_allowed_hosts()

# Telegram Bot settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Backward compatibility / default chat
TELEGRAM_PUBLIC_CHAT_ID = os.getenv("TELEGRAM_PUBLIC_CHAT_ID", TELEGRAM_CHAT_ID)
TELEGRAM_LOG_CHAT_ID = os.getenv("TELEGRAM_LOG_CHAT_ID", TELEGRAM_CHAT_ID)
TELEGRAM_DISABLED = os.getenv('ENVIRONMENT', 'production').lower() == 'test'

# Telegram Link settings (for account linking security)
TELEGRAM_BOT_SECRET = os.getenv("TELEGRAM_BOT_SECRET", "")
TELEGRAM_LINK_TOKEN_TTL_MINUTES = int(os.getenv("TELEGRAM_LINK_TOKEN_TTL_MINUTES", "10"))

# OpenRouter API settings (for study plan generation)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
# Force DEBUG=True in test mode for proper error display
environment = os.getenv('ENVIRONMENT', 'production').lower()
if environment == 'test':
    DEBUG = True
else:
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

# Development warning for missing OpenRouter API key
if DEBUG and not OPENROUTER_API_KEY and environment != 'test':
    import warnings
    warnings.warn(
        "\n⚠️  OpenRouter API key not configured.\n"
        "Study plan generation will not work without OPENROUTER_API_KEY.\n"
        "Get your API key from https://openrouter.ai/keys\n"
        "Set OPENROUTER_API_KEY in .env file",
        RuntimeWarning,
        stacklevel=2
    )

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
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',  # API documentation via Swagger/OpenAPI
    'corsheaders',
    'django_filters',
    'channels',  # Django Channels для WebSocket
    'core',
    'accounts',
    'materials',
    'scheduling',  # Система бронирования расписания (должна быть ПОСЛЕ materials, т.к. импортирует Subject)
    'assignments',
    'chat',
    'reports',
    'notifications',
    'payments',
    'invoices',  # Система выставления счетов (должна быть ПОСЛЕ materials и payments)
    'applications',
    'knowledge_graph',  # Система графов знаний для обучения
]

# Add daphne only if not in test mode (to avoid Twisted SSL issues during testing)
# ВРЕМЕННО ОТКЛЮЧЕНО: проблема совместимости pyOpenSSL 25.3.0 с Python 3.13
# if environment != 'test':
#     INSTALLED_APPS.insert(0, 'daphne')  # ASGI server для WebSocket

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.session_refresh_middleware.SessionRefreshMiddleware',  # Refresh session on every request
    'config.middleware.session_refresh_middleware.CSRFTokenRefreshMiddleware',  # Manage CSRF tokens
    'config.middleware.error_logging_middleware.ErrorLoggingMiddleware',  # Log HTTP errors with traceback
    'config.sentry.SentryMiddleware',  # Sentry middleware for error tracking (must be near end)
]

ROOT_URLCONF = 'config.urls'

# Disable automatic slash appending to prevent 307 redirects on POST requests
# This fixes the issue where Django tries to redirect /api/auth/login to /api/auth/login/
# but can't maintain POST data during redirect
APPEND_SLASH = False

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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


# ============================================================================
# DATABASE CONFIGURATION WITH ENVIRONMENT SEPARATION
# ============================================================================
#
# КРИТИЧЕСКИ ВАЖНАЯ СЕКЦИЯ: Обеспечивает абсолютную изоляцию продакшн БД
# от development и test окружений
#
# Три режима работы (определяются через ENVIRONMENT в .env):
#   1. production:  Supabase PostgreSQL (ТОЛЬКО на продакшн сервере!)
#   2. development: Локальная SQLite БД (backend/db.sqlite3)
#   3. test:        SQLite in-memory (:memory:) - полная изоляция
#
# ЗАЩИТА: При попытке использовать Supabase в dev/test - приложение упадет с ошибкой
#
# ============================================================================

def _build_production_db_config() -> dict:
    """
    Конфигурация продакшн БД: Supabase PostgreSQL.

    ТОЛЬКО для production окружения!
    Используется DATABASE_URL или набор SUPABASE_DB_* переменных.

    Returns:
        dict: Конфигурация PostgreSQL БД для Django

    Raises:
        ImproperlyConfigured: Если параметры БД не заданы
    """
    # Настройки таймаутов для предотвращения зависания
    connect_timeout = int(os.getenv('DB_CONNECT_TIMEOUT', '60'))  # 60 секунд для продакшн
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

        # Парсим URL и создаем конфигурацию
        db_config = {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': str(parsed.port or '5432'),
            'CONN_MAX_AGE': 0,  # Отключаем пул соединений для избежания stale connections
            'OPTIONS': db_options.copy(),
        }
        return db_config

    # Альтернатива: использовать отдельные SUPABASE_DB_* переменные
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
        'Production режим требует настройки БД.\n'
        'Установите DATABASE_URL (postgres URI) '
        'или переменные SUPABASE_DB_NAME, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD, SUPABASE_DB_HOST, SUPABASE_DB_PORT.'
    )


def _build_development_db_config() -> dict:
    """
    Конфигурация development БД: Локальная SQLite.

    Файл БД: backend/db.sqlite3

    ЗАЩИТА: Если обнаружен DATABASE_URL с Supabase - падает с ошибкой!
    Это защищает от случайного повреждения продакшн данных.

    Returns:
        dict: Конфигурация SQLite БД для Django

    Raises:
        ImproperlyConfigured: Если обнаружена попытка использовать продакшн БД
    """
    database_url = os.getenv('DATABASE_URL', '')

    # ЗАЩИТА: Запретить Supabase в development
    if 'supabase' in database_url.lower():
        raise ImproperlyConfigured(
            f"\n"
            f"{'='*70}\n"
            f"🚨 КРИТИЧЕСКАЯ ОШИБКА: Попытка использовать ПРОДАКШН БД в development!\n"
            f"{'='*70}\n"
            f"\n"
            f"Обнаружен DATABASE_URL с Supabase в режиме ENVIRONMENT=development\n"
            f"\n"
            f"DATABASE_URL: {database_url[:50]}...\n"
            f"\n"
            f"РЕШЕНИЕ:\n"
            f"1. Удалите DATABASE_URL из .env (или закомментируйте)\n"
            f"2. Development режим автоматически использует локальную SQLite БД\n"
            f"3. Продакшн БД доступна ТОЛЬКО при ENVIRONMENT=production\n"
            f"\n"
            f"Это защита от случайного повреждения продакшн данных!\n"
            f"{'='*70}\n"
        )

    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'ATOMIC_REQUESTS': True,
    }


def _build_test_db_config() -> dict:
    """
    Конфигурация test БД: SQLite in-memory.

    Полная изоляция от продакшн - каждый тест на чистой БД.
    Используется :memory: для максимальной скорости.

    ЗАЩИТА: Если обнаружен DATABASE_URL с Supabase - падает с ошибкой!

    Returns:
        dict: Конфигурация SQLite in-memory БД для Django

    Raises:
        ImproperlyConfigured: Если обнаружена попытка использовать продакшн БД
    """
    database_url = os.getenv('DATABASE_URL', '')

    # ЗАЩИТА: Запретить Supabase в test
    if 'supabase' in database_url.lower():
        raise ImproperlyConfigured(
            f"\n"
            f"{'='*70}\n"
            f"🚨🚨🚨 КРИТИЧЕСКАЯ ОШИБКА: ТЕСТЫ НА ПРОДАКШН БД! 🚨🚨🚨\n"
            f"{'='*70}\n"
            f"\n"
            f"Обнаружена попытка запуска ТЕСТОВ на ПРОДАКШН Supabase БД!\n"
            f"\n"
            f"DATABASE_URL: {database_url[:50]}...\n"
            f"\n"
            f"ЭТО ПРИВЕДЕТ К УНИЧТОЖЕНИЮ ПРОДАКШН ДАННЫХ!\n"
            f"\n"
            f"РЕШЕНИЕ:\n"
            f"1. Удалите DATABASE_URL из окружения при запуске тестов\n"
            f"2. Используйте: ENVIRONMENT=test pytest\n"
            f"3. Или запускайте через: ./scripts/run_tests.sh\n"
            f"\n"
            f"Тесты должны использовать ТОЛЬКО SQLite in-memory!\n"
            f"{'='*70}\n"
        )

    return {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        },
        'ATOMIC_REQUESTS': True,
    }


def _get_database_config() -> dict:
    """
    Выбирает конфигурацию БД на основе ENVIRONMENT.

    КРИТИЧЕСКАЯ ФУНКЦИЯ: Обеспечивает абсолютную изоляцию продакшн БД от dev/test.

    Режимы:
    - production: Supabase PostgreSQL (DATABASE_URL или SUPABASE_DB_*)
    - development: Локальная SQLite (backend/db.sqlite3)
    - test: SQLite in-memory (:memory:) - полная изоляция

    Returns:
        dict: Конфигурация БД для текущего окружения

    Raises:
        ImproperlyConfigured: При невалидном значении ENVIRONMENT
    """
    environment = os.getenv('ENVIRONMENT', 'production').lower()

    if environment == 'production':
        return _build_production_db_config()
    elif environment == 'development':
        return _build_development_db_config()
    elif environment == 'test':
        return _build_test_db_config()
    else:
        raise ImproperlyConfigured(
            f"❌ ОШИБКА: Недопустимое значение ENVIRONMENT='{environment}'\n"
            f"Допустимые значения: production, development, test\n"
            f"Установите правильное значение в .env файле"
        )


# Конфигурация БД с автоматическим выбором на основе ENVIRONMENT
DATABASES = {
    'default': _get_database_config()
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


# ============================================================================
# ЗАЩИТА ОТ СЛУЧАЙНОГО ИСПОЛЬЗОВАНИЯ ПРОДАКШН БД
# ============================================================================

import sys

# Получаем текущее окружение и конфигурацию БД
# Auto-detect test mode to allow pytest conftest.py to run first
is_testing = 'pytest' in sys.modules or 'test' in sys.argv or any('pytest' in arg for arg in sys.argv)
if is_testing and 'ENVIRONMENT' not in os.environ:
    os.environ['ENVIRONMENT'] = 'test'

current_environment = os.getenv('ENVIRONMENT', 'production').lower()
db_config = DATABASES['default']
db_host = db_config.get('HOST', '')
db_engine = db_config.get('ENGINE', '')

# Проверка 1: Если запущены тесты (pytest или manage.py test)
if is_testing:
    # Тесты ОБЯЗАНЫ использовать ENVIRONMENT=test
    if current_environment != 'test':
        raise ImproperlyConfigured(
            f"\n"
            f"{'='*70}\n"
            f"🚨 ОШИБКА: Тесты запущены без ENVIRONMENT=test\n"
            f"{'='*70}\n"
            f"\n"
            f"Текущее значение: ENVIRONMENT={current_environment or 'не установлено'}\n"
            f"\n"
            f"РЕШЕНИЕ: Установите ENVIRONMENT=test перед запуском тестов\n"
            f"Или используйте скрипт: ./scripts/run_tests.sh\n"
            f"{'='*70}\n"
        )

    # Тесты НЕ ДОЛЖНЫ использовать PostgreSQL или Supabase
    if 'postgresql' in db_engine or 'supabase' in db_host.lower():
        raise ImproperlyConfigured(
            f"\n"
            f"{'='*70}\n"
            f"🚨🚨🚨 КРИТИЧЕСКАЯ ОШИБКА: ТЕСТЫ ИСПОЛЬЗУЮТ ПРОДАКШН БД! 🚨🚨🚨\n"
            f"{'='*70}\n"
            f"\n"
            f"DB ENGINE: {db_engine}\n"
            f"DB HOST: {db_host}\n"
            f"\n"
            f"Тесты должны использовать ТОЛЬКО SQLite in-memory!\n"
            f"Проверьте файл .env и удалите DATABASE_URL\n"
            f"{'='*70}\n"
        )

# Проверка 2: Development режим с Supabase (предупреждение, не ошибка)
if current_environment == 'development' and 'supabase' in db_host.lower():
    import warnings
    warnings.warn(
        f"\n"
        f"{'='*70}\n"
        f"⚠️  WARNING: Development режим использует ПРОДАКШН БД!\n"
        f"{'='*70}\n"
        f"\n"
        f"DB HOST: {db_host}\n"
        f"\n"
        f"РЕКОМЕНДАЦИЯ: Используйте локальную SQLite БД для разработки\n"
        f"Удалите DATABASE_URL из .env для автоматического переключения на SQLite\n"
        f"{'='*70}\n",
        RuntimeWarning,
        stacklevel=2
    )

# Проверка 3: Production режим БЕЗ Supabase (предупреждение)
if current_environment == 'production' and 'supabase' not in db_host.lower() and 'sqlite' not in db_engine:
    import warnings
    warnings.warn(
        f"⚠️  Production режим, но БД не Supabase. HOST: {db_host}",
        RuntimeWarning
    )

# Логирование текущей конфигурации (только в DEBUG режиме)
if DEBUG:
    print(f"\n{'='*70}")
    print(f"🔧 Database Configuration:")
    print(f"{'='*70}")
    print(f"  ENVIRONMENT: {current_environment}")
    print(f"  DB ENGINE: {db_engine}")
    print(f"  DB NAME: {db_config.get('NAME', 'N/A')}")
    if db_host:
        print(f"  DB HOST: {db_host}")
    print(f"{'='*70}\n")


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

# Session timeout configuration
# For testing: 2 hours (7200 seconds)
# For production: 24 hours (86400 seconds)
# Can be overridden via SESSION_TIMEOUT env variable
TESTING_SESSION_TIMEOUT = int(os.getenv('TESTING_SESSION_TIMEOUT', '7200'))  # 2 hours for testing
PRODUCTION_SESSION_TIMEOUT = int(os.getenv('PRODUCTION_SESSION_TIMEOUT', '86400'))  # 24 hours
SESSION_COOKIE_AGE = TESTING_SESSION_TIMEOUT if DEBUG else PRODUCTION_SESSION_TIMEOUT

# SESSION_COOKIE_SECURE управляется через условие DEBUG выше
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # Allow cookies on redirect from YooKassa (not 'Strict')
SESSION_COOKIE_DOMAIN = env_config.get_session_cookie_domain()

# CRITICAL: Save session on every request to refresh timeout
# This prevents random logouts during navigation
SESSION_SAVE_EVERY_REQUEST = True

# Session expiry behavior
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Session persists even after browser close
SESSION_COOKIE_AGE_ON_REDIRECT = SESSION_COOKIE_AGE  # Keep timeout on redirects

# CSRF settings
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow CSRF cookies on redirect from YooKassa
# CSRF_COOKIE_SECURE управляется через условие DEBUG выше
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript access
CSRF_COOKIE_DOMAIN = env_config.get_csrf_cookie_domain()


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

# File Upload Configuration
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# CORS Configuration
if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    _env_cors_origins = env_config.get_cors_allowed_origins()
    if _env_cors_origins:
        CORS_ALLOWED_ORIGINS.extend(_env_cors_origins)
else:
    frontend_url = os.getenv("FRONTEND_URL")
    if not frontend_url:
        raise ValueError(
            "FRONTEND_URL environment variable is required in production"
        )
    CORS_ALLOWED_ORIGINS = [frontend_url]

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
# ВАЖНО: TokenAuthentication должен быть ПЕРВЫМ!
# SessionAuthentication требует CSRF для unsafe methods (POST, PATCH, DELETE).
# Если SessionAuthentication первый и запрос приходит с session cookie,
# DRF выполнит CSRF проверку даже если есть Token header.
# С TokenAuthentication первым - запросы с Token header не требуют CSRF.
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'config.throttling.BurstThrottle',  # Global burst protection (10/sec)
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '50/h',                      # Anonymous users: 50 req/hour
        'user': '500/h',                     # Authenticated users: 500 req/hour
        'student': '1000/h',                 # Students: 1000 req/hour
        'admin': '10000/h',                  # Admins: 10000 req/hour (practically unlimited)
        'burst': '10/s',                     # Burst protection: 10 req/sec (global)
        'login': '5/m',                      # Login attempts: 5 per minute per IP
        'upload': '10/h',                    # File uploads: 10 per hour per user
        'search': '30/m',                    # Search queries: 30 per minute per user
        'analytics': '100/h',                # Analytics/reports: 100 per hour per user
        'chat_message': '60/m',              # Chat messages: 60 per minute per user
        'chat_room': '5/h',                  # Chat room creation: 5 per hour per user
        'assignment_submission': '10/h',     # Assignment submissions: 10 per hour per user
        'report_generation': '10/h',         # Report generation: 10 per hour per user
        'admin_endpoint': '1000/h',          # Admin endpoints: 1000 per hour per admin
    }
}

# Cache settings
# Настройки кэширования
# По умолчанию: Development (DEBUG=True) -> False, Production (DEBUG=False) -> True
# Можно переопределить в .env: USE_REDIS_CACHE=True/False
USE_REDIS_CACHE = os.getenv('USE_REDIS_CACHE', str(not DEBUG)).lower() == 'true'

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

# Rate limiting settings
# Comprehensive API rate limiting with tiered limits and sliding window algorithm
RATE_LIMITING = {
    'ENABLED': True,
    'ALGORITHM': 'sliding_window',  # sliding_window | fixed_window | token_bucket

    # Tiered rate limits (per minute)
    'TIERS': {
        'anonymous': {
            'limit': 20,      # 20 requests per minute
            'window': 60,     # 1 minute
            'identifier': 'ip',
        },
        'authenticated': {
            'limit': 100,     # 100 requests per minute
            'window': 60,     # 1 minute
            'identifier': 'user_id',
        },
        'premium': {
            'limit': 500,     # 500 requests per minute
            'window': 60,     # 1 minute
            'identifier': 'user_id',
        },
        'admin': {
            'limit': 99999,   # Effectively unlimited
            'window': 60,
            'identifier': 'user_id',
        },
    },

    # Endpoint-specific limits (override tier limits)
    'ENDPOINTS': {
        'login': {
            'limit': 5,                      # 5 attempts per minute (brute force protection)
            'window': 60,
            'identifier': 'ip',
        },
        'upload': {
            'limit': 10,                     # 10 uploads per hour
            'window': 3600,
            'identifier': 'user_id',
        },
        'search': {
            'limit': 30,                     # 30 searches per minute (DB protection)
            'window': 60,
            'identifier': 'user_id',
        },
        'analytics': {
            'limit': 100,                    # 100 reports per hour (CPU protection)
            'window': 3600,
            'identifier': 'user_id',
        },
        'chat_message': {
            'limit': 60,                     # 60 messages per minute (spam protection)
            'window': 60,
            'identifier': 'user_id',
        },
        'chat_room': {
            'limit': 5,                      # 5 room creations per hour (spam prevention)
            'window': 3600,
            'identifier': 'user_id',
        },
        'assignment_submission': {
            'limit': 10,                     # 10 submissions per hour
            'window': 3600,
            'identifier': 'user_id',
        },
        'report_generation': {
            'limit': 10,                     # 10 reports per hour (CPU protection)
            'window': 3600,
            'identifier': 'user_id',
        },
    },

    # Bypass settings
    'BYPASS': {
        'admin_users': True,                 # Admins/staff bypass rate limiting
        'internal_ips': [],                  # IP addresses to bypass (e.g., monitoring)
        'service_accounts': [],              # Service account IDs to bypass
    },

    # Response settings
    'RESPONSE': {
        'include_headers': True,             # Include X-RateLimit-* headers
        'include_retry_after': True,         # Include Retry-After header on 429
        'json_error_format': True,           # Return JSON error on 429 (not HTML)
    },

    # Logging and monitoring
    'LOGGING': {
        'enabled': True,
        'log_violations': True,              # Log when rate limit exceeded
        'log_level': 'WARNING',
        'include_details': True,             # Include request details in logs
    },
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
# По умолчанию: Development (DEBUG=True) -> InMemory, Production (DEBUG=False) -> Redis
# Можно переопределить в .env: USE_REDIS_CHANNELS=True/False
# ВАЖНО: В production Redis КРИТИЧНО необходим для WebSocket на нескольких процессах
USE_REDIS_CHANNELS = os.getenv('USE_REDIS_CHANNELS', str(not DEBUG)).lower() == 'true'

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

# WebSocket settings - environment-aware
WEBSOCKET_URL = env_config.get_websocket_url()
WEBSOCKET_AUTHENTICATION_TIMEOUT = 30  # seconds
WEBSOCKET_MESSAGE_MAX_LENGTH = 1024 * 1024  # 1MB

# Payment settings
# PAYMENT_DEVELOPMENT_MODE: режим разработки с минимальными суммами (1 руб) и частыми платежами (10 мин)
# По умолчанию берется из DEBUG, но можно переопределить в .env
# Это позволяет тестировать реальные суммы даже в development, если нужно
PAYMENT_DEVELOPMENT_MODE = os.getenv('PAYMENT_DEVELOPMENT_MODE', str(DEBUG)).lower() == 'true'
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
try:
    from core.celery_config import CELERY_BEAT_SCHEDULE
except ImportError:
    # Celery не установлен - для создания пользователей в production
    CELERY_BEAT_SCHEDULE = {}

# ============================================
# PRODUCTION CONFIGURATION VALIDATION
# ============================================
# Проверяем критические настройки в production режиме
if not DEBUG:
    # Получаем ENVIRONMENT для проверки соответствия
    current_env = os.getenv('ENVIRONMENT', 'production').lower()

    # 1. Проверка ENVIRONMENT - должен быть 'production' при DEBUG=False
    if current_env != 'production':
        raise ImproperlyConfigured(
            f"ENVIRONMENT must be 'production' when DEBUG=False.\n"
            f"Current value: ENVIRONMENT={current_env}, DEBUG=False\n"
            f"Expected: ENVIRONMENT=production, DEBUG=False\n"
            f"This prevents accidental production mode with development database."
        )

    # 2. Проверка DATABASE_URL - должен быть задан для production
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Проверяем альтернативный вариант с SUPABASE_DB_*
        if not all([
            os.getenv('SUPABASE_DB_NAME'),
            os.getenv('SUPABASE_DB_USER'),
            os.getenv('SUPABASE_DB_PASSWORD'),
            os.getenv('SUPABASE_DB_HOST')
        ]):
            raise ImproperlyConfigured(
                "Production mode requires DATABASE_URL to be set.\n"
                "Either set DATABASE_URL (recommended) or all SUPABASE_DB_* variables.\n"
                "Production MUST use PostgreSQL (Supabase), NOT SQLite."
            )
    elif database_url:
        # Проверяем что это PostgreSQL, а не SQLite
        if database_url.startswith('sqlite'):
            raise ImproperlyConfigured(
                "Production mode cannot use SQLite database.\n"
                f"Current DATABASE_URL: {database_url[:30]}...\n"
                "Expected: PostgreSQL connection string (postgresql://...)"
            )
        # Проверяем что это не localhost
        if 'localhost' in database_url.lower() or '127.0.0.1' in database_url:
            import warnings
            warnings.warn(
                f"Production mode using localhost database is unusual.\n"
                f"DATABASE_URL contains localhost or 127.0.0.1\n"
                f"Ensure this is intentional for your deployment.",
                RuntimeWarning,
                stacklevel=2
            )

    # 3. Проверка Redis - КРИТИЧНО для Celery и рекуррентных платежей
    if not USE_REDIS_CACHE or not USE_REDIS_CHANNELS:
        import warnings
        warnings.warn(
            "Production mode requires Redis for Celery (recurring payments) and WebSocket.\n"
            "Set USE_REDIS_CACHE=True and USE_REDIS_CHANNELS=True in .env\n"
            "Or remove these variables to use automatic defaults.",
            RuntimeWarning,
            stacklevel=2
        )

    # 4. Проверка FRONTEND_URL - не должен быть localhost
    if FRONTEND_URL and ('localhost' in FRONTEND_URL.lower() or '127.0.0.1' in FRONTEND_URL):
        raise ImproperlyConfigured(
            f"Production mode with localhost FRONTEND_URL is not allowed.\n"
            f"Current value: {FRONTEND_URL}\n"
            f"Expected: https://{env_config.PRODUCTION_DOMAIN} or similar production URL"
        )

    # 5. Проверка ALLOWED_HOSTS - должны быть заданы
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['*']:
        raise ImproperlyConfigured(
            "ALLOWED_HOSTS must be properly configured in production.\n"
            "Current value: [] or ['*']\n"
            f"Expected: ['{env_config.PRODUCTION_DOMAIN}', 'www.{env_config.PRODUCTION_DOMAIN}', ...]"
        )

    # 6. Проверка CORS_ALLOWED_ORIGINS - не должен быть пустым или содержать localhost
    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured(
            "CORS_ALLOWED_ORIGINS must be configured in production.\n"
            "Current value: []\n"
            f"Expected: ['https://{env_config.PRODUCTION_DOMAIN}']"
        )

    # Проверяем что нет localhost в CORS
    for origin in CORS_ALLOWED_ORIGINS:
        if 'localhost' in origin.lower() or '127.0.0.1' in origin:
            raise ImproperlyConfigured(
                f"CORS_ALLOWED_ORIGINS contains localhost origin in production.\n"
                f"Found: {origin}\n"
                f"Production CORS must only allow production frontend URL."
            )

    # 7. Проверка OpenRouter API key - предупреждение (не критично для основного функционала)
    if not OPENROUTER_API_KEY:
        import warnings
        warnings.warn(
            "OPENROUTER_API_KEY is not set in production mode. "
            "Study plan generation will be unavailable. "
            "Get your API key from https://openrouter.ai/keys",
            UserWarning
        )

    # 8. Информационное сообщение о режиме
    import sys
    if 'runserver' in sys.argv or 'test' in sys.argv:
        pass  # Не выводим при тестах или runserver
    else:
        print(f"✅ Production mode active (DEBUG=False)")
        print(f"   - Environment: {current_env}")
        print(f"   - Database: {'PostgreSQL' if database_url and 'postgres' in database_url else 'Unknown'}")
        print(f"   - Redis Cache: {'✅ Enabled' if USE_REDIS_CACHE else '❌ Disabled'}")
        print(f"   - Redis Channels: {'✅ Enabled' if USE_REDIS_CHANNELS else '❌ Disabled'}")
        print(f"   - Payment Mode: {'💰 Production (5000₽/week)' if not PAYMENT_DEVELOPMENT_MODE else '🧪 Development (1₽/10min)'}")
        print(f"   - Frontend URL: {FRONTEND_URL}")
        print(f"   - CORS Origins: {len(CORS_ALLOWED_ORIGINS)} configured")
        print(f"   - OpenRouter API: {'✅ Configured' if OPENROUTER_API_KEY else '❌ Missing'}")


# ==================== LOGGING CONFIGURATION ====================
# Конфигурация логирования для мониторинга и аудита

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {funcName}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '[{levelname}] {asctime} {name} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'audit': {
            'format': '[AUDIT] {asctime} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose'
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/audit.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'level': 'INFO',
            'formatter': 'audit'
        },
        'admin_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/admin.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'level': 'INFO',
            'formatter': 'simple'
        },
        'celery_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/celery.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'level': 'INFO',
            'formatter': 'verbose'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'level': 'ERROR',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False
        },
        'accounts.staff_views': {
            'handlers': ['console', 'admin_file'],
            'level': 'INFO',
            'propagate': False
        },
        'accounts.signals': {
            'handlers': ['console', 'audit_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'accounts.retry_logic': {
            'handlers': ['console', 'admin_file'],
            'level': 'INFO',
            'propagate': False
        },
        'accounts.views': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False
        },
        'config.middleware.session_refresh_middleware': {
            'handlers': ['console', 'audit_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'celery': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False
        },
        'celery.task': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False
        },
        'core.tasks': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False
        },
        'materials.management.commands.process_subscription_payments': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}

# Создаем директорию для логов если её нет
import logging.handlers
_logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(_logs_dir):
    os.makedirs(_logs_dir, exist_ok=True)

# =============================================================================
# Pachca Forum Integration
# =============================================================================
PACHCA_FORUM_API_TOKEN = os.getenv('PACHCA_FORUM_API_TOKEN', '')
PACHCA_FORUM_CHANNEL_ID = os.getenv('PACHCA_FORUM_CHANNEL_ID', '')
PACHCA_FORUM_BASE_URL = os.getenv('PACHCA_FORUM_BASE_URL', 'https://api.pachca.com/api/shared/v1')
