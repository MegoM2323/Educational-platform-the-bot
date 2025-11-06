from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Загружаем переменные окружения из .env файла в корне проекта
# .env файл находится на уровень выше (в корне проекта)
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")
# Также пробуем загрузить из текущей директории (на случай, если .env в backend/)
load_dotenv(BASE_DIR / ".env", override=False)

# Поддержка импортов как без префикса `backend.*`, так и с ним в тестах
import sys, importlib
for _mod in ("accounts","applications","materials","assignments","chat","reports","notifications","payments","core"):
    try:
        # Двусторонние алиасы импортов
        sys.modules.setdefault(f"backend.{_mod}", importlib.import_module(_mod))
        sys.modules.setdefault(_mod, importlib.import_module(_mod))
        # Критично: алиасы для подмодуля models, чтобы Django видел один и тот же модуль
        sys.modules.setdefault(f"backend.{_mod}.models", importlib.import_module(f"{_mod}.models"))
    except Exception:
        pass

# YooKasa settings
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_WEBHOOK_URL = os.getenv("YOOKASSA_WEBHOOK_URL")

# Frontend URL for payment redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0', '5.129.249.206', 'the-bot.ru', 'www.the-bot.ru']  # Добавлен публичный IP сервера и домены

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
DEBUG = True




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

# Используем Supabase как основную базу данных
# Для разработки используем SQLite, для продакшена - Supabase PostgreSQL
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'postgres',
            'USER': 'postgres.sobptsqfzgycmauglqzk',
            'PASSWORD': os.getenv('SUPABASE_DB_PASSWORD', 'your-supabase-password'),
            'HOST': 'aws-0-eu-central-1.pooler.supabase.com',
            'PORT': '6543',
        }
    }


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
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

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
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Только для разработки

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
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')],
        },
    },
}

# WebSocket settings
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', 'ws://localhost:8000/ws/')
WEBSOCKET_AUTHENTICATION_TIMEOUT = 30  # seconds
WEBSOCKET_MESSAGE_MAX_LENGTH = 1024 * 1024  # 1MB
