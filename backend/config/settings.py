# CRITICAL: Apply Python 3.13 compatibility patch FIRST
# Должен быть импортирован до любых других библиотек
try:
    from config import hyperframe_patch
except ImportError:
    pass

# CRITICAL: Initialize test environment BEFORE any other imports
try:
    from config import test_init  # noqa: F401
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

# Define logs directory early (used in logging configuration later)
_logs_dir = "/app/logs" if os.path.exists("/app") else os.path.join(BASE_DIR, "logs")
try:
    if not os.path.exists(_logs_dir):
        os.makedirs(_logs_dir, exist_ok=True)
except (OSError, PermissionError):
    # If we can't create the directory, fall back to /tmp or a writable location
    _logs_dir = os.path.expanduser("~/.thebot/logs")
    os.makedirs(_logs_dir, exist_ok=True)

# Загружаем переменные окружения из .env (без ошибок на посторонние строки)
# .env в корне проекта; резервно — backend/.env
# КРИТИЧНО: Не перезаписываем ENVIRONMENT если уже установлен (например, pytest-env)
PROJECT_ROOT = BASE_DIR.parent
saved_environment = os.environ.get("ENVIRONMENT")
saved_db_name = os.environ.get("DB_NAME")
saved_db_host = os.environ.get("DB_HOST")
saved_db_user = os.environ.get("DB_USER")
saved_db_password = os.environ.get("DB_PASSWORD")
saved_db_port = os.environ.get("DB_PORT")
saved_db_sslmode = os.environ.get("DB_SSLMODE")

for env_path in (PROJECT_ROOT / ".env", BASE_DIR / ".env"):
    try:
        if env_path.exists():
            for k, v in dotenv_values(env_path).items():
                if k and v is not None and k not in os.environ:
                    os.environ[k] = str(v)
    except Exception:
        # Игнорируем любые ошибки парсинга отдельных строк
        pass

# Восстановить ENVIRONMENT если он был установлен до загрузки .env
# Это критично для pytest (pytest-env устанавливает ENVIRONMENT=test)
if saved_environment is not None:
    os.environ["ENVIRONMENT"] = saved_environment
if saved_db_name is not None:
    os.environ["DB_NAME"] = saved_db_name
if saved_db_host is not None:
    os.environ["DB_HOST"] = saved_db_host
if saved_db_user is not None:
    os.environ["DB_USER"] = saved_db_user
if saved_db_password is not None:
    os.environ["DB_PASSWORD"] = saved_db_password
if saved_db_port is not None:
    os.environ["DB_PORT"] = saved_db_port
if saved_db_sslmode is not None:
    os.environ["DB_SSLMODE"] = saved_db_sslmode

# IMPORTANT: Sentry initialization is DEFERRED to wsgi.py, asgi.py, and manage.py
# This is necessary because Sentry's DjangoIntegration requires Django to be fully initialized,
# including AppRegistry. Early init in settings.py would fail or not capture models properly.
# The init_sentry() function is available for manual initialization if needed.

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
TELEGRAM_DISABLED = os.getenv("ENVIRONMENT", "production").lower() == "test"

# Telegram Link settings (for account linking security)
TELEGRAM_BOT_SECRET = os.getenv("TELEGRAM_BOT_SECRET", "")
TELEGRAM_LINK_TOKEN_TTL_MINUTES = int(os.getenv("TELEGRAM_LINK_TOKEN_TTL_MINUTES", "10"))

# OpenRouter API settings (for study plan generation)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
# Force DEBUG=True in test mode for proper error display
environment = os.getenv("ENVIRONMENT", "production").lower()
if environment == "test":
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
    if SECRET_KEY.startswith("django-insecure-"):
        raise ImproperlyConfigured("SECRET_KEY must not use the default insecure key in production")

# Development warning for missing OpenRouter API key
if DEBUG and not OPENROUTER_API_KEY and environment != "test":
    import warnings

    warnings.warn(
        "\n⚠️  OpenRouter API key not configured.\n"
        "Study plan generation will not work without OPENROUTER_API_KEY.\n"
        "Get your API key from https://openrouter.ai/keys\n"
        "Set OPENROUTER_API_KEY in .env file",
        RuntimeWarning,
        stacklevel=2,
    )

# Security settings for HTTPS behind reverse proxy (nginx)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
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
    X_FRAME_OPTIONS = "DENY"

# Application definition


def _validate_installed_apps_order():
    """
    Validate INSTALLED_APPS order matches dependency graph.

    Raises ImproperlyConfigured if apps are in wrong order relative to their dependencies.
    """
    # Dependency map: app -> list of required apps it depends on
    DEPS = {
        "scheduling": ["materials"],
        "invoices": ["materials", "payments"],
        "assignments": ["materials"],
    }

    positions = {app: idx for idx, app in enumerate(INSTALLED_APPS)}

    for app, dependencies in DEPS.items():
        if app not in positions:
            continue
        app_pos = positions[app]
        for dep in dependencies:
            if dep not in positions:
                raise ImproperlyConfigured(f"App '{app}' depends on '{dep}', but '{dep}' not in INSTALLED_APPS")
            dep_pos = positions[dep]
            if dep_pos > app_pos:
                raise ImproperlyConfigured(
                    f"INSTALLED_APPS order error: '{dep}' (pos {dep_pos}) must come "
                    f"before '{app}' (pos {app_pos}). App '{app}' depends on '{dep}'."
                )


# CRITICAL: INSTALLED_APPS dependency order matters for Django model registration
# Apps are organized by dependency levels (do NOT reorder without understanding implications):
#
# LEVEL 1: Django core & third-party (no dependencies)
#   - All django.contrib.* modules
#   - Third-party libraries (rest_framework, channels, etc.)
#
# LEVEL 2: Custom core app (foundation with no model dependencies)
#   - 'core' - provides base utilities, settings, middleware
#
# LEVEL 3: Data model apps (provide base models for other apps)
#   - 'materials' - defines Subject, Material, Category models
#   - 'accounts' - defines User-related models
#   - 'payments' - defines Payment-related models
#
# LEVEL 4: Dependent apps (import and extend models from Level 3)
#   - 'scheduling' - DEPENDS ON: materials.Subject
#   - 'assignments' - DEPENDS ON: materials.* models
#   - 'invoices' - DEPENDS ON: materials.*, payments.* models
#
# LEVEL 5: Other apps (independent or have limited dependencies)
#   - 'chat', 'reports', 'notifications', 'applications', 'knowledge_graph'
#
# VALIDATION:
#   Function _validate_installed_apps_order() runs on startup and ensures all dependencies
#   are placed correctly. If you move apps, make sure dependent apps come AFTER their deps.
#
# WHEN ADDING NEW APPS:
#   1. Identify what models it imports/depends on
#   2. Place it AFTER all its dependency apps
#   3. Add entry to DEPS dict in _validate_installed_apps_order()
#   4. Run tests to verify: python manage.py makemigrations --dry-run

_BASE_INSTALLED_APPS = [
    # Django core & third-party (no custom dependencies)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",  # API documentation via Swagger/OpenAPI
    "corsheaders",
    "django_filters",
    "channels",  # Django Channels для WebSocket
    # Custom: Core app (foundation)
    "core",
    # Custom: Data model apps (dependencies for apps below)
    "materials",
    "accounts",
    "payments",
    # Custom: Dependent apps (require models from data model apps)
    "scheduling",  # System for booking lessons (must be AFTER materials - imports Subject model)
    "assignments",  # Requires materials models
    "invoices",  # System for billing (must be AFTER materials and payments - imports their models)
    # Custom: Other apps
    "chat",
    "reports",
    "notifications",
    "applications",
    "knowledge_graph",  # Knowledge graphs for learning
]

# Use all apps in all environments
INSTALLED_APPS = _BASE_INSTALLED_APPS

# Validate INSTALLED_APPS order on startup
try:
    _validate_installed_apps_order()
except ImproperlyConfigured as e:
    import sys

    sys.stderr.write(f"ERROR: {e}\n")
    raise

# Add ASGI server for WebSocket support (using Uvicorn instead of Daphne)
# Uvicorn does not require pyOpenSSL and works with Python 3.13
# Daphne is kept in INSTALLED_APPS for compatibility with Django Channels
# Daphne отключен для разработки (проблема с OpenSSL в Python 3.13)
# На production используется отдельный Daphne процесс через systemd
# if environment != "test":
#     INSTALLED_APPS.insert(0, "daphne")  # ASGI server для WebSocket

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # DISABLED FOR TESTING - causing issues
    # 'config.middleware.session_refresh_middleware.SessionRefreshMiddleware',
    # 'config.middleware.session_refresh_middleware.CSRFTokenRefreshMiddleware',
    # 'config.middleware.error_logging_middleware.ErrorLoggingMiddleware',
    # 'config.sentry.SentryMiddleware',
]

ROOT_URLCONF = "config.urls"

# Disable automatic slash appending to prevent 307 redirects on POST requests
# This fixes the issue where Django tries to redirect /api/auth/login to /api/auth/login/
# but can't maintain POST data during redirect
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ============================================================================
# DATABASE CONFIGURATION - POSTGRESQL FOR ALL ENVIRONMENTS
# ============================================================================
#
# Все окружения используют PostgreSQL:
#   1. production:  PostgreSQL (основной сервер)
#   2. development: PostgreSQL (локальный или remote)
#   3. test:        PostgreSQL (отдельная тестовая БД)
#
# Конфигурация через DATABASE_URL или отдельные переменные окружения
# ============================================================================


def _get_database_config() -> dict:
    """
    Выбирает конфигурацию PostgreSQL для всех окружений.

    Используется DATABASE_URL или набор переменных окружения.

    Returns:
        dict: Конфигурация PostgreSQL для Django

    Raises:
        ImproperlyConfigured: Если параметры БД не заданы
    """
    # Настройки таймаутов для предотвращения зависания
    # Database: 30s (fail-fast for broken connections)
    # Nginx: 120s (API proxy_read_timeout)
    # Frontend: 300s (client timeout)
    connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "30"))
    sslmode = os.getenv("DB_SSLMODE", "require")

    # База данных опций с таймаутами
    db_options = {
        "connect_timeout": str(connect_timeout),
    }

    # Добавляем SSL режим если указан
    if sslmode:
        db_options["sslmode"] = sslmode

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in ("postgres", "postgresql"):
            raise ImproperlyConfigured("DATABASE_URL должен быть Postgres URI (postgres:// или postgresql://)")

        # Парсим URL и создаем конфигурацию
        db_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username,
            "PASSWORD": parsed.password,
            "HOST": parsed.hostname,
            "PORT": str(parsed.port or "5432"),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": db_options.copy(),
        }
        return db_config

    # Альтернатива: использовать отдельные DB_* переменные
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")

    if all([name, user, password, host]):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": name,
            "USER": user,
            "PASSWORD": password,
            "HOST": host,
            "PORT": str(port),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": db_options.copy(),
        }

    raise ImproperlyConfigured(
        "Требуется конфигурация БД.\n"
        "Установите DATABASE_URL (postgres://) "
        "или переменные DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT."
    )


# Конфигурация БД с автоматическим выбором на основе ENVIRONMENT
DATABASES = {"default": _get_database_config()}

# Применяем патч для установки таймаутов подключения
# Это нужно делать после определения DATABASES, но до использования
try:
    from django.db.backends.postgresql.base import DatabaseWrapper

    if not hasattr(DatabaseWrapper, "_timeout_patched"):
        _original_get_new_connection = DatabaseWrapper.get_new_connection

        def get_new_connection_with_timeout(self, conn_params):
            """Обертка для установки таймаута подключения"""
            connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "30"))
            # Устанавливаем таймаут в параметрах подключения psycopg2
            if "connect_timeout" not in conn_params:
                conn_params["connect_timeout"] = connect_timeout
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
is_testing = "pytest" in sys.modules or "test" in sys.argv or any("pytest" in arg for arg in sys.argv)
if is_testing and "ENVIRONMENT" not in os.environ:
    os.environ["ENVIRONMENT"] = "test"

current_environment = os.getenv("ENVIRONMENT", "production").lower()
db_config = DATABASES["default"]
db_host = db_config.get("HOST", "")
db_engine = db_config.get("ENGINE", "")

# Проверка 1: Если запущены тесты (pytest или manage.py test)
if is_testing:
    # Тесты ОБЯЗАНЫ использовать ENVIRONMENT=test
    if current_environment != "test":
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

    if "postgresql" in db_engine:
        if (
            "localhost" not in db_host
            and "127.0.0.1" not in db_host
            and "testdb" not in db_config.get("NAME", "").lower()
        ):
            raise ImproperlyConfigured(
                f"\n"
                f"{'='*70}\n"
                f"🚨 ОШИБКА: ТЕСТЫ ИСПОЛЬЗУЮТ ПРОДАКШН БД! 🚨\n"
                f"{'='*70}\n"
                f"\n"
                f"DB ENGINE: {db_engine}\n"
                f"DB HOST: {db_host}\n"
                f"DB NAME: {db_config.get('NAME', 'N/A')}\n"
                f"\n"
                f"Тесты должны использовать локальную тестовую базу данных!\n"
                f"Проверьте переменные окружения DB_HOST и DB_NAME\n"
                f"{'='*70}\n"
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
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Session timeout configuration
# For testing: 2 hours (7200 seconds)
# For production: 24 hours (86400 seconds)
# Can be overridden via SESSION_TIMEOUT env variable
TESTING_SESSION_TIMEOUT = int(os.getenv("TESTING_SESSION_TIMEOUT", "7200"))  # 2 hours for testing
PRODUCTION_SESSION_TIMEOUT = int(os.getenv("PRODUCTION_SESSION_TIMEOUT", "86400"))  # 24 hours
SESSION_COOKIE_AGE = TESTING_SESSION_TIMEOUT if DEBUG else PRODUCTION_SESSION_TIMEOUT

# SESSION_COOKIE_SECURE управляется через условие DEBUG выше
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"  # Allow cookies on redirect from YooKassa (not 'Strict')
SESSION_COOKIE_DOMAIN = env_config.get_session_cookie_domain()

# CRITICAL: Save session on every request to refresh timeout
# This prevents random logouts during navigation
SESSION_SAVE_EVERY_REQUEST = True

# Session expiry behavior
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Session persists even after browser close
SESSION_COOKIE_AGE_ON_REDIRECT = SESSION_COOKIE_AGE  # Keep timeout on redirects

# CSRF settings
CSRF_COOKIE_SAMESITE = "Lax"  # Allow CSRF cookies on redirect from YooKassa
# CSRF_COOKIE_SECURE управляется через условие DEBUG выше
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript access
CSRF_COOKIE_DOMAIN = env_config.get_csrf_cookie_domain()
CSRF_TRUSTED_ORIGINS = env_config.get_csrf_trusted_origins()


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
if environment == "test":
    STATIC_ROOT = Path("/tmp/thebot_test_static")
else:
    STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (user uploads)
MEDIA_URL = "/media/"
if environment == "test":
    MEDIA_ROOT = Path("/tmp/thebot_test_media")
else:
    MEDIA_ROOT = BASE_DIR / "media"

# File Upload Configuration
MAX_FILE_SIZE = 104857600  # 100 MB (100 * 1024 * 1024) - unified across nginx and Django
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_FILE_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_FILE_SIZE

# Email Backend Configuration
# For test environment use in-memory backend (does not send actual emails)
if environment == "test":
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Password hashing configuration
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

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
        raise ValueError("FRONTEND_URL environment variable is required in production")
    CORS_ALLOWED_ORIGINS = [frontend_url]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Используем CORS_ALLOWED_ORIGINS вместо allow all

# Дополнительные CORS настройки для разработки
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# REST Framework settings
# ВАЖНО: TokenAuthentication должен быть ПЕРВЫМ!
# SessionAuthentication требует CSRF для unsafe methods (POST, PATCH, DELETE).
# Если SessionAuthentication первый и запрос приходит с session cookie,
# DRF выполнит CSRF проверку даже если есть Token header.
# С TokenAuthentication первым - запросы с Token header не требуют CSRF.
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        []  # Disable throttles for testing to prevent 429 errors
        if current_environment == "test"
        else [
            "config.throttling.BurstThrottle",  # Global burst protection (10/sec)
        ]
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "50/h",  # Anonymous users: 50 req/hour
        "user": "500/h",  # Authenticated users: 500 req/hour
        "student": "1000/h",  # Students: 1000 req/hour
        "admin": "10000/h",  # Admins: 10000 req/hour (practically unlimited)
        "burst": "10/s",  # Burst protection: 10 req/sec (global)
        "login": "5/m",  # Login attempts: 5 per minute per IP
        "upload": "10/h",  # File uploads: 10 per hour per user
        "search": "30/m",  # Search queries: 30 per minute per user
        "analytics": "100/h",  # Analytics/reports: 100 per hour per user
        "chat_message": "60/m",  # Chat messages: 60 per minute per user
        "chat_room": "5/h",  # Chat room creation: 5 per hour per user
        "assignment_submission": "10/h",  # Assignment submissions: 10 per hour per user
        "report_generation": "10/h",  # Report generation: 10 per hour per user
        "admin_endpoint": "1000/h",  # Admin endpoints: 1000 per hour per admin
    },
}

# Cache settings
# Настройки кэширования
# По умолчанию: Development (DEBUG=True) -> False, Production (DEBUG=False) -> True
# Можно переопределить в .env: USE_REDIS_CACHE=True/False
# КРИТИЧНО: Отключаем Redis для тестов чтобы избежать ConnectionError
USE_REDIS_CACHE = (
    False if current_environment == "test" else os.getenv("USE_REDIS_CACHE", str(not DEBUG)).lower() == "true"
)

if USE_REDIS_CACHE:
    # Используем Redis для кэширования
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        },
        "dashboard": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/2"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        },
        "chat": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/3"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        },
    }
else:
    # Используем локальное кэширование в памяти (для разработки)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        },
        "dashboard": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "dashboard-cache",
        },
        "chat": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "chat-cache",
        },
    }

# Cache timeouts (in seconds)
CACHE_TIMEOUTS = {
    "dashboard_data": 300,  # 5 minutes
    "student_materials": 600,  # 10 minutes
    "teacher_students": 900,  # 15 minutes
    "parent_children": 1200,  # 20 minutes
    "chat_messages": 60,  # 1 minute
    "progress_stats": 300,  # 5 minutes
}

# Rate limiting settings
# Comprehensive API rate limiting with tiered limits and sliding window algorithm
RATE_LIMITING = {
    "ENABLED": True,
    "ALGORITHM": "sliding_window",  # sliding_window | fixed_window | token_bucket
    # Tiered rate limits (per minute)
    "TIERS": {
        "anonymous": {
            "limit": 20,  # 20 requests per minute
            "window": 60,  # 1 minute
            "identifier": "ip",
        },
        "authenticated": {
            "limit": 100,  # 100 requests per minute
            "window": 60,  # 1 minute
            "identifier": "user_id",
        },
        "premium": {
            "limit": 500,  # 500 requests per minute
            "window": 60,  # 1 minute
            "identifier": "user_id",
        },
        "admin": {
            "limit": 99999,  # Effectively unlimited
            "window": 60,
            "identifier": "user_id",
        },
    },
    # Endpoint-specific limits (override tier limits)
    "ENDPOINTS": {
        "login": {
            "limit": 5,  # 5 attempts per minute (brute force protection)
            "window": 60,
            "identifier": "ip",
        },
        "upload": {
            "limit": 10,  # 10 uploads per hour
            "window": 3600,
            "identifier": "user_id",
        },
        "search": {
            "limit": 30,  # 30 searches per minute (DB protection)
            "window": 60,
            "identifier": "user_id",
        },
        "analytics": {
            "limit": 100,  # 100 reports per hour (CPU protection)
            "window": 3600,
            "identifier": "user_id",
        },
        "chat_message": {
            "limit": 60,  # 60 messages per minute (spam protection)
            "window": 60,
            "identifier": "user_id",
        },
        "chat_room": {
            "limit": 5,  # 5 room creations per hour (spam prevention)
            "window": 3600,
            "identifier": "user_id",
        },
        "assignment_submission": {
            "limit": 10,  # 10 submissions per hour
            "window": 3600,
            "identifier": "user_id",
        },
        "report_generation": {
            "limit": 10,  # 10 reports per hour (CPU protection)
            "window": 3600,
            "identifier": "user_id",
        },
    },
    # Bypass settings
    "BYPASS": {
        "admin_users": True,  # Admins/staff bypass rate limiting
        "internal_ips": [],  # IP addresses to bypass (e.g., monitoring)
        "service_accounts": [],  # Service account IDs to bypass
    },
    # Response settings
    "RESPONSE": {
        "include_headers": True,  # Include X-RateLimit-* headers
        "include_retry_after": True,  # Include Retry-After header on 429
        "json_error_format": True,  # Return JSON error on 429 (not HTML)
    },
    # Logging and monitoring
    "LOGGING": {
        "enabled": True,
        "log_violations": True,  # Log when rate limit exceeded
        "log_level": "WARNING",
        "include_details": True,  # Include request details in logs
    },
}

# Backup settings
BACKUP_DIR = os.getenv("BACKUP_DIR", "/tmp/backups")
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "30"))

# System monitoring settings
SYSTEM_MONITORING = {
    "ENABLED": True,
    "METRICS_CACHE_TIMEOUT": 60,  # 1 minute
    "HEALTH_CHECK_TIMEOUT": 30,  # 30 seconds
    "ALERT_THRESHOLDS": {
        "CPU_WARNING": 80,
        "CPU_CRITICAL": 95,
        "MEMORY_WARNING": 80,
        "MEMORY_CRITICAL": 90,
        "DISK_WARNING": 80,
        "DISK_CRITICAL": 90,
        "DB_RESPONSE_WARNING": 1000,  # ms
        "DB_RESPONSE_CRITICAL": 5000,  # ms
    },
}

# Django Channels settings
# По умолчанию: Development (DEBUG=True) -> InMemory, Production (DEBUG=False) -> Redis
# Можно переопределить в .env: USE_REDIS_CHANNELS=True/False
# ВАЖНО: В production Redis КРИТИЧНО необходим для WebSocket на нескольких процессах
# КРИТИЧНО: Отключаем Redis для тестов чтобы избежать ConnectionError
USE_REDIS_CHANNELS = (
    False if current_environment == "test" else os.getenv("USE_REDIS_CHANNELS", str(not DEBUG)).lower() == "true"
)

if USE_REDIS_CHANNELS:
    # Используем Redis для каналов (production)
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")],
                "capacity": 5000,
                "expiry": 60,
            },
        },
    }
else:
    # Используем InMemory для разработки (не требует Redis)
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

# WebSocket Configuration
# Configure WebSocket behavior via environment variables for different environments
# Development: frequent heartbeats, longer timeouts
# Production: less frequent heartbeats, stricter timeouts


def _parse_int_env(key, default, min_val=None, max_val=None):
    """Parse integer environment variable with optional range validation"""
    try:
        value = int(os.getenv(key, str(default)))
        if min_val is not None and value < min_val:
            value = min_val
        if max_val is not None and value > max_val:
            value = max_val
        return value
    except (ValueError, TypeError):
        return default


WEBSOCKET_CONFIG = {
    "HEARTBEAT_INTERVAL": _parse_int_env("WEBSOCKET_HEARTBEAT_INTERVAL", 30, min_val=5, max_val=300),
    "HEARTBEAT_TIMEOUT": _parse_int_env("WEBSOCKET_HEARTBEAT_TIMEOUT", 15, min_val=3, max_val=120),
    "AUTH_TIMEOUT": _parse_int_env("WEBSOCKET_AUTH_TIMEOUT", 15, min_val=5, max_val=120),
    # DoS protection: limit per-message size to prevent memory exhaustion
    # Checked BEFORE json.loads() to avoid CPU-intensive parsing of oversized payloads
    "MESSAGE_SIZE_LIMIT": _parse_int_env("WEBSOCKET_MESSAGE_SIZE_LIMIT", 65536, min_val=100, max_val=1000000),
    "MAX_CONNECTIONS_PER_USER": _parse_int_env("WEBSOCKET_MAX_CONNECTIONS_PER_USER", 5, min_val=1, max_val=100),
    "RECONNECT_BACKOFF_MULTIPLIER": float(os.getenv("WEBSOCKET_RECONNECT_BACKOFF_MULTIPLIER", "2.0")),
    "RECONNECT_MAX_DELAY": _parse_int_env("WEBSOCKET_RECONNECT_MAX_DELAY", 32000, min_val=1000, max_val=300000),
}

# WebSocket settings - environment-aware
WEBSOCKET_URL = env_config.get_websocket_url()
WEBSOCKET_AUTHENTICATION_TIMEOUT = WEBSOCKET_CONFIG["AUTH_TIMEOUT"]  # Derived from config
WEBSOCKET_MESSAGE_MAX_LENGTH = 1024 * 1024  # 1MB

# Payment settings
# PAYMENT_DEVELOPMENT_MODE: режим разработки с минимальными суммами (1 руб) и частыми платежами (10 мин)
# По умолчанию берется из DEBUG, но можно переопределить в .env
# Это позволяет тестировать реальные суммы даже в development, если нужно
PAYMENT_DEVELOPMENT_MODE = os.getenv("PAYMENT_DEVELOPMENT_MODE", str(DEBUG)).lower() == "true"
DEVELOPMENT_PAYMENT_AMOUNT = Decimal(os.getenv("DEVELOPMENT_PAYMENT_AMOUNT", "1.00"))  # 1 рубль в режиме разработки
PRODUCTION_PAYMENT_AMOUNT = Decimal(os.getenv("PRODUCTION_PAYMENT_AMOUNT", "5000.00"))  # 5000 рублей в обычном режиме
DEVELOPMENT_RECURRING_INTERVAL_MINUTES = int(
    os.getenv("DEVELOPMENT_RECURRING_INTERVAL_MINUTES", "10")
)  # 10 минут в режиме разработки
PRODUCTION_RECURRING_INTERVAL_WEEKS = int(
    os.getenv("PRODUCTION_RECURRING_INTERVAL_WEEKS", "1")
)  # 1 неделя в обычном режиме

# Celery settings
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 минут максимум на задачу
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Test environment Celery configuration
if current_environment == "test":
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

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
    current_env = os.getenv("ENVIRONMENT", "production").lower()

    # 1. Проверка ENVIRONMENT - должен быть 'production' при DEBUG=False
    if current_env != "production":
        raise ImproperlyConfigured(
            f"ENVIRONMENT must be 'production' when DEBUG=False.\n"
            f"Current value: ENVIRONMENT={current_env}, DEBUG=False\n"
            f"Expected: ENVIRONMENT=production, DEBUG=False\n"
            f"This prevents accidental production mode with development database."
        )

    # 2. Проверка DATABASE_URL - должен быть задан для production
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Проверяем альтернативный вариант с DB_*
        if not all(
            [
                os.getenv("DB_NAME"),
                os.getenv("DB_USER"),
                os.getenv("DB_PASSWORD"),
                os.getenv("DB_HOST"),
            ]
        ):
            raise ImproperlyConfigured(
                "Production mode requires DATABASE_URL to be set.\n"
                "Either set DATABASE_URL (recommended) or all DB_* variables (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).\n"
                "Production MUST use PostgreSQL."
            )
    elif database_url:
        # Проверяем что это PostgreSQL, а не SQLite
        if database_url.startswith("sqlite"):
            raise ImproperlyConfigured(
                "Production mode cannot use SQLite database.\n"
                f"Current DATABASE_URL: {database_url[:30]}...\n"
                "Expected: PostgreSQL connection string (postgresql://...)"
            )
        # Проверяем что это не localhost
        if "localhost" in database_url.lower() or "127.0.0.1" in database_url:
            import warnings

            warnings.warn(
                f"Production mode using localhost database is unusual.\n"
                f"DATABASE_URL contains localhost or 127.0.0.1\n"
                f"Ensure this is intentional for your deployment.",
                RuntimeWarning,
                stacklevel=2,
            )

    # 3. Проверка Redis - КРИТИЧНО для Celery и рекуррентных платежей
    if not USE_REDIS_CACHE or not USE_REDIS_CHANNELS:
        import warnings

        warnings.warn(
            "Production mode requires Redis for Celery (recurring payments) and WebSocket.\n"
            "Set USE_REDIS_CACHE=True and USE_REDIS_CHANNELS=True in .env\n"
            "Or remove these variables to use automatic defaults.",
            RuntimeWarning,
            stacklevel=2,
        )

    # 4. Проверка FRONTEND_URL - не должен быть localhost
    if FRONTEND_URL and ("localhost" in FRONTEND_URL.lower() or "127.0.0.1" in FRONTEND_URL):
        raise ImproperlyConfigured(
            f"Production mode with localhost FRONTEND_URL is not allowed.\n"
            f"Current value: {FRONTEND_URL}\n"
            f"Expected: https://{env_config.PRODUCTION_DOMAIN} or similar production URL"
        )

    # 5. Проверка ALLOWED_HOSTS - должны быть заданы
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["*"]:
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
        if "localhost" in origin.lower() or "127.0.0.1" in origin:
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
            UserWarning,
        )

    # 8. Информационное сообщение о режиме
    import sys

    if "runserver" in sys.argv or "test" in sys.argv:
        pass  # Не выводим при тестах или runserver
    else:
        print(f"✅ Production mode active (DEBUG=False)")
        print(f"   - Environment: {current_env}")
        print(f"   - Database: {'PostgreSQL' if database_url and 'postgres' in database_url else 'Unknown'}")
        print(f"   - Redis Cache: {'✅ Enabled' if USE_REDIS_CACHE else '❌ Disabled'}")
        print(f"   - Redis Channels: {'✅ Enabled' if USE_REDIS_CHANNELS else '❌ Disabled'}")
        print(
            f"   - Payment Mode: {'💰 Production (5000₽/week)' if not PAYMENT_DEVELOPMENT_MODE else '🧪 Development (1₽/10min)'}"
        )
        print(f"   - Frontend URL: {FRONTEND_URL}")
        print(f"   - CORS Origins: {len(CORS_ALLOWED_ORIGINS)} configured")
        print(f"   - OpenRouter API: {'✅ Configured' if OPENROUTER_API_KEY else '❌ Missing'}")


# ==================== LOGGING CONFIGURATION ====================
# Конфигурация логирования для мониторинга и аудита

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {funcName}:{lineno} - {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{levelname}] {asctime} {name} - {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "audit": {
            "format": "[AUDIT] {asctime} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "verbose",
        },
        "audit_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(_logs_dir, "audit.log"),  # Use dynamic path
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "level": "INFO",
            "formatter": "audit",
        },
        "admin_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(_logs_dir, "admin.log"),  # Use dynamic path
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "level": "INFO",
            "formatter": "simple",
        },
        "celery_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(_logs_dir, "celery.log"),  # Use dynamic path
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "level": "INFO",
            "formatter": "verbose",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(_logs_dir, "error.log"),  # Use dynamic path
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "level": "ERROR",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "audit": {
            "handlers": ["console", "audit_file"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts.staff_views": {
            "handlers": ["console", "admin_file"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts.signals": {
            "handlers": ["console", "audit_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "accounts.retry_logic": {
            "handlers": ["console", "admin_file"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts.views": {
            "handlers": ["console", "audit_file"],
            "level": "INFO",
            "propagate": False,
        },
        "config.middleware.session_refresh_middleware": {
            "handlers": ["console", "audit_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.task": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core.tasks": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        "materials.management.commands.process_subscription_payments": {
            "handlers": ["console", "celery_file"],
            "level": "INFO",
            "propagate": False,
        },
        "chat": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "chat.websocket": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "chat.consumers": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Создаем директорию для логов если её нет
import logging.handlers


# =============================================================================
# WebSocket Configuration Validation
# =============================================================================


def validate_websocket_config():
    """
    Validate WebSocket configuration on Django startup.
    Ensures all timeout and limit values are sensible.
    """
    import logging

    logger = logging.getLogger("django")

    config = WEBSOCKET_CONFIG

    try:
        assert config["HEARTBEAT_INTERVAL"] > 0, "HEARTBEAT_INTERVAL must be > 0"
        assert config["HEARTBEAT_TIMEOUT"] > 0, "HEARTBEAT_TIMEOUT must be > 0"
        assert (
            config["HEARTBEAT_TIMEOUT"] < config["HEARTBEAT_INTERVAL"]
        ), f"HEARTBEAT_TIMEOUT ({config['HEARTBEAT_TIMEOUT']}s) must be < HEARTBEAT_INTERVAL ({config['HEARTBEAT_INTERVAL']}s)"
        assert config["AUTH_TIMEOUT"] > 0, "AUTH_TIMEOUT must be > 0"
        assert config["MESSAGE_SIZE_LIMIT"] > 0, "MESSAGE_SIZE_LIMIT must be > 0"
        assert config["MAX_CONNECTIONS_PER_USER"] > 0, "MAX_CONNECTIONS_PER_USER must be > 0"
        assert config["RECONNECT_BACKOFF_MULTIPLIER"] > 0, "RECONNECT_BACKOFF_MULTIPLIER must be > 0"
        assert config["RECONNECT_MAX_DELAY"] > 0, "RECONNECT_MAX_DELAY must be > 0"

        if DEBUG:
            logger.info(
                f"WebSocket configuration validated:\n"
                f"  - HEARTBEAT_INTERVAL: {config['HEARTBEAT_INTERVAL']}s\n"
                f"  - HEARTBEAT_TIMEOUT: {config['HEARTBEAT_TIMEOUT']}s\n"
                f"  - AUTH_TIMEOUT: {config['AUTH_TIMEOUT']}s\n"
                f"  - MESSAGE_SIZE_LIMIT: {config['MESSAGE_SIZE_LIMIT']} chars\n"
                f"  - MAX_CONNECTIONS_PER_USER: {config['MAX_CONNECTIONS_PER_USER']}\n"
                f"  - RECONNECT_BACKOFF_MULTIPLIER: {config['RECONNECT_BACKOFF_MULTIPLIER']}\n"
                f"  - RECONNECT_MAX_DELAY: {config['RECONNECT_MAX_DELAY']}ms"
            )
        else:
            logger.info("WebSocket configuration validated")

    except AssertionError as e:
        logger.error(f"WebSocket configuration error: {str(e)}")
        raise ImproperlyConfigured(f"WebSocket configuration error: {str(e)}")


# Run validation on startup
try:
    validate_websocket_config()
except ImproperlyConfigured:
    raise


# =============================================================================
# Pachca Chat Integration
# =============================================================================
PACHCA_CHAT_API_TOKEN = os.getenv("PACHCA_CHAT_API_TOKEN", "")
PACHCA_CHAT_CHANNEL_ID = os.getenv("PACHCA_CHAT_CHANNEL_ID", "")
PACHCA_CHAT_BASE_URL = os.getenv("PACHCA_CHAT_BASE_URL", "https://api.pachca.com/api/shared/v1")
