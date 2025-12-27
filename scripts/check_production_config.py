#!/usr/bin/env python3
"""
Production Configuration Pre-Deployment Checker

Validates all critical settings before production deployment.
Catches configuration issues BEFORE they cause outages.

Usage:
    python scripts/check_production_config.py

Exit Codes:
    0 - All checks passed
    1 - Configuration errors found
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Добавляем backend в путь для импорта Django настроек
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Загружаем .env перед проверкой
from dotenv import load_dotenv
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ConfigChecker:
    """Проверяет критические настройки для production деплоя"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []

    def error(self, check_name: str, message: str):
        """Регистрирует критическую ошибку"""
        self.errors.append((check_name, message))

    def warning(self, check_name: str, message: str):
        """Регистрирует предупреждение"""
        self.warnings.append((check_name, message))

    def success(self, check_name: str):
        """Регистрирует успешную проверку"""
        self.passed.append(check_name)

    def check_environment_mode(self):
        """Проверка ENVIRONMENT и DEBUG"""
        environment = os.getenv('ENVIRONMENT', '').lower()
        debug = os.getenv('DEBUG', 'True').lower()

        if environment != 'production':
            self.error(
                'ENVIRONMENT',
                f"Must be 'production', found: '{environment}'\n"
                f"Set ENVIRONMENT=production in .env"
            )
            return

        if debug == 'true':
            self.error(
                'DEBUG',
                f"DEBUG must be False in production, found: DEBUG={debug}\n"
                f"Set DEBUG=False in .env"
            )
            return

        self.success('ENVIRONMENT and DEBUG')

    def check_secret_key(self):
        """Проверка SECRET_KEY"""
        secret_key = os.getenv('SECRET_KEY', '')

        if not secret_key:
            self.error(
                'SECRET_KEY',
                "SECRET_KEY is not set in .env\n"
                "Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
            )
            return

        if len(secret_key) < 50:
            self.error(
                'SECRET_KEY',
                f"SECRET_KEY too short: {len(secret_key)} characters (minimum 50)\n"
                "Generate stronger key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
            )
            return

        if secret_key.startswith('django-insecure-'):
            self.error(
                'SECRET_KEY',
                "SECRET_KEY uses default insecure value\n"
                "Generate production key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
            )
            return

        if 'your-secret-key-here' in secret_key.lower() or 'change-in-production' in secret_key.lower():
            self.error(
                'SECRET_KEY',
                "SECRET_KEY appears to be a placeholder value\n"
                "Generate real key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
            )
            return

        self.success('SECRET_KEY')

    def check_database_url(self):
        """Проверка DATABASE_URL"""
        database_url = os.getenv('DATABASE_URL', '')

        if not database_url:
            # Проверяем альтернативные переменные
            supabase_vars = [
                os.getenv('SUPABASE_DB_NAME'),
                os.getenv('SUPABASE_DB_USER'),
                os.getenv('SUPABASE_DB_PASSWORD'),
                os.getenv('SUPABASE_DB_HOST')
            ]
            if not all(supabase_vars):
                self.error(
                    'DATABASE_URL',
                    "DATABASE_URL is not set and SUPABASE_DB_* variables incomplete\n"
                    "Set DATABASE_URL=postgresql://user:pass@host:port/db in .env"
                )
                return
            else:
                self.success('DATABASE (via SUPABASE_DB_*)')
                return

        # Проверяем что это PostgreSQL
        if database_url.startswith('sqlite'):
            self.error(
                'DATABASE_URL',
                f"Production cannot use SQLite database\n"
                f"Current: {database_url[:40]}...\n"
                f"Expected: PostgreSQL (postgresql://...)"
            )
            return

        if not (database_url.startswith('postgres://') or database_url.startswith('postgresql://')):
            self.error(
                'DATABASE_URL',
                f"DATABASE_URL must be PostgreSQL connection string\n"
                f"Current: {database_url[:40]}...\n"
                f"Expected: postgresql://..."
            )
            return

        # Проверяем на localhost
        if 'localhost' in database_url.lower() or '127.0.0.1' in database_url:
            self.warning(
                'DATABASE_URL',
                f"DATABASE_URL points to localhost - unusual for production\n"
                f"Ensure this is intentional for your deployment"
            )
        else:
            self.success('DATABASE_URL')

    def check_allowed_hosts(self):
        """Проверка ALLOWED_HOSTS через EnvConfig"""
        # Импортируем EnvConfig для получения ALLOWED_HOSTS
        try:
            from core.environment import EnvConfig
            env_config = EnvConfig()
            allowed_hosts = env_config.get_allowed_hosts()
        except Exception as e:
            self.error(
                'ALLOWED_HOSTS',
                f"Failed to load ALLOWED_HOSTS: {e}\n"
                f"Check core.environment.EnvConfig"
            )
            return

        if not allowed_hosts or allowed_hosts == ['*']:
            self.error(
                'ALLOWED_HOSTS',
                "ALLOWED_HOSTS not configured or set to ['*']\n"
                "Must specify production domains explicitly"
            )
            return

        # Проверяем на localhost
        for host in allowed_hosts:
            if 'localhost' in host.lower() or '127.0.0.1' in host:
                self.warning(
                    'ALLOWED_HOSTS',
                    f"ALLOWED_HOSTS contains localhost: {host}\n"
                    f"Should contain only production domains"
                )
                return

        self.success('ALLOWED_HOSTS')

    def check_cors_origins(self):
        """Проверка CORS_ALLOWED_ORIGINS"""
        try:
            from core.environment import EnvConfig
            env_config = EnvConfig()
            cors_origins = env_config.get_cors_allowed_origins()
        except Exception as e:
            self.error(
                'CORS_ALLOWED_ORIGINS',
                f"Failed to load CORS_ALLOWED_ORIGINS: {e}\n"
                f"Check core.environment.EnvConfig"
            )
            return

        if not cors_origins:
            self.error(
                'CORS_ALLOWED_ORIGINS',
                "CORS_ALLOWED_ORIGINS is empty\n"
                "Must specify production frontend URL"
            )
            return

        # Проверяем на localhost
        for origin in cors_origins:
            if 'localhost' in origin.lower() or '127.0.0.1' in origin:
                self.error(
                    'CORS_ALLOWED_ORIGINS',
                    f"CORS_ALLOWED_ORIGINS contains localhost: {origin}\n"
                    f"Production must only allow production frontend URL"
                )
                return

        self.success('CORS_ALLOWED_ORIGINS')

    def check_frontend_url(self):
        """Проверка FRONTEND_URL"""
        frontend_url = os.getenv('FRONTEND_URL', '')

        if not frontend_url:
            # EnvConfig автоматически определит URL
            self.warning(
                'FRONTEND_URL',
                "FRONTEND_URL not set - will be auto-detected\n"
                "Recommended to set explicitly for production"
            )
            return

        if 'localhost' in frontend_url.lower() or '127.0.0.1' in frontend_url:
            self.error(
                'FRONTEND_URL',
                f"FRONTEND_URL contains localhost in production\n"
                f"Current: {frontend_url}\n"
                f"Expected: https://the-bot.ru or similar"
            )
            return

        if not frontend_url.startswith('https://'):
            self.warning(
                'FRONTEND_URL',
                f"FRONTEND_URL should use HTTPS in production\n"
                f"Current: {frontend_url}\n"
                f"Expected: https://..."
            )
            return

        self.success('FRONTEND_URL')

    def check_redis(self):
        """Проверка Redis настроек"""
        use_redis_cache = os.getenv('USE_REDIS_CACHE', '').lower()
        use_redis_channels = os.getenv('USE_REDIS_CHANNELS', '').lower()

        # В production Redis должен быть включен (или переменные не заданы для auto-detect)
        if use_redis_cache == 'false' or use_redis_channels == 'false':
            self.warning(
                'REDIS',
                "Redis is disabled in production\n"
                "Redis REQUIRED for Celery (payments) and WebSocket\n"
                "Remove USE_REDIS_* variables for automatic production defaults"
            )
            return

        # Проверяем URL
        redis_url = os.getenv('REDIS_URL', '')
        if redis_url and ('localhost' in redis_url or '127.0.0.1' in redis_url):
            self.warning(
                'REDIS_URL',
                f"REDIS_URL points to localhost\n"
                f"Ensure Redis is accessible in production deployment"
            )
            return

        self.success('REDIS')

    def check_yookassa(self):
        """Проверка YooKassa"""
        shop_id = os.getenv('YOOKASSA_SHOP_ID', '')
        secret_key = os.getenv('YOOKASSA_SECRET_KEY', '')
        webhook_url = os.getenv('YOOKASSA_WEBHOOK_URL', '')

        if not shop_id or not secret_key:
            self.warning(
                'YOOKASSA',
                "YooKassa credentials not set\n"
                "Payment processing will not work"
            )
            return

        if 'your-shop-id' in shop_id.lower() or 'your-secret-key' in secret_key.lower():
            self.error(
                'YOOKASSA',
                "YooKassa credentials appear to be placeholders\n"
                "Set real production credentials"
            )
            return

        # Проверяем webhook URL
        if webhook_url:
            if not webhook_url.startswith('https://'):
                self.warning(
                    'YOOKASSA_WEBHOOK_URL',
                    f"Webhook should use HTTPS\n"
                    f"Current: {webhook_url}"
                )
            if 'localhost' in webhook_url.lower() or '127.0.0.1' in webhook_url:
                self.error(
                    'YOOKASSA_WEBHOOK_URL',
                    f"Webhook URL contains localhost - won't work in production\n"
                    f"Current: {webhook_url}"
                )
                return

        self.success('YOOKASSA')

    def check_vite_env(self):
        """Проверка frontend environment variables"""
        vite_api_url = os.getenv('VITE_DJANGO_API_URL', '')
        vite_ws_url = os.getenv('VITE_WEBSOCKET_URL', '')

        # Проверяем VITE_DJANGO_API_URL
        if vite_api_url:
            if 'localhost' in vite_api_url.lower() or '127.0.0.1' in vite_api_url:
                self.error(
                    'VITE_DJANGO_API_URL',
                    f"Frontend API URL contains localhost\n"
                    f"Current: {vite_api_url}\n"
                    f"Expected: https://the-bot.ru/api or similar"
                )
                return
            if not vite_api_url.startswith('https://'):
                self.warning(
                    'VITE_DJANGO_API_URL',
                    f"Frontend API URL should use HTTPS\n"
                    f"Current: {vite_api_url}"
                )

        # Проверяем VITE_WEBSOCKET_URL
        if vite_ws_url:
            if 'localhost' in vite_ws_url.lower() or '127.0.0.1' in vite_ws_url:
                self.error(
                    'VITE_WEBSOCKET_URL',
                    f"Frontend WebSocket URL contains localhost\n"
                    f"Current: {vite_ws_url}\n"
                    f"Expected: wss://the-bot.ru/ws or similar"
                )
                return
            if not vite_ws_url.startswith('wss://'):
                self.warning(
                    'VITE_WEBSOCKET_URL',
                    f"Frontend WebSocket should use WSS (secure)\n"
                    f"Current: {vite_ws_url}\n"
                    f"Expected: wss://..."
                )

        self.success('VITE Environment Variables')

    def run_all_checks(self):
        """Запускает все проверки"""
        print(f"{Colors.BOLD}=== Production Configuration Validation ==={Colors.END}\n")

        checks = [
            ('Environment Mode', self.check_environment_mode),
            ('Secret Key', self.check_secret_key),
            ('Database URL', self.check_database_url),
            ('Allowed Hosts', self.check_allowed_hosts),
            ('CORS Origins', self.check_cors_origins),
            ('Frontend URL', self.check_frontend_url),
            ('Redis Configuration', self.check_redis),
            ('YooKassa Payment', self.check_yookassa),
            ('Vite Frontend Config', self.check_vite_env),
        ]

        for check_name, check_func in checks:
            print(f"Checking {check_name}...", end=' ')
            try:
                check_func()
                if check_name in [p for p in self.passed]:
                    print(f"{Colors.GREEN}✓{Colors.END}")
                elif check_name in [w[0] for w in self.warnings]:
                    print(f"{Colors.YELLOW}⚠{Colors.END}")
                elif check_name in [e[0] for e in self.errors]:
                    print(f"{Colors.RED}✗{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}✗ (Exception){Colors.END}")
                self.error(check_name, f"Check failed with exception: {e}")

    def print_results(self):
        """Выводит результаты проверок"""
        print(f"\n{Colors.BOLD}=== Results ==={Colors.END}\n")

        # Успешные проверки
        if self.passed:
            print(f"{Colors.GREEN}✓ Passed: {len(self.passed)}{Colors.END}")
            for check in self.passed:
                print(f"  ✓ {check}")
            print()

        # Предупреждения
        if self.warnings:
            print(f"{Colors.YELLOW}⚠ Warnings: {len(self.warnings)}{Colors.END}")
            for check_name, message in self.warnings:
                print(f"  ⚠ {check_name}:")
                for line in message.split('\n'):
                    if line.strip():
                        print(f"    {line}")
            print()

        # Ошибки
        if self.errors:
            print(f"{Colors.RED}✗ Errors: {len(self.errors)}{Colors.END}")
            for check_name, message in self.errors:
                print(f"  ✗ {check_name}:")
                for line in message.split('\n'):
                    if line.strip():
                        print(f"    {line}")
            print()

        # Итог
        if self.errors:
            print(f"{Colors.RED}{Colors.BOLD}FAILED{Colors.END} - Fix errors before deploying to production!")
            return False
        elif self.warnings:
            print(f"{Colors.YELLOW}{Colors.BOLD}PASSED WITH WARNINGS{Colors.END} - Review warnings before deploying")
            return True
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}ALL CHECKS PASSED{Colors.END} - Ready for production deployment")
            return True


def main():
    """Main entry point"""
    # Проверяем что .env существует
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print(f"{Colors.RED}ERROR:{Colors.END} .env file not found at {env_path}")
        print(f"Create .env from .env.example and configure for production")
        return 1

    checker = ConfigChecker()
    checker.run_all_checks()
    success = checker.print_results()

    # Дополнительные рекомендации
    if success:
        print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
        print("  1. Run: python backend/manage.py check --deploy")
        print("  2. Run: python backend/manage.py migrate --check")
        print("  3. Build frontend: cd frontend && npm run build")
        print("  4. Test production build locally before deploying")
        print(f"  5. Review: {PROJECT_ROOT}/docs/PRODUCTION_CHECKLIST.md")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
