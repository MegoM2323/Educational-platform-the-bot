#!/usr/bin/env python
"""
Configuration Validation Script for THE_BOT_platform

Проверяет корректность настроек перед deployment.
Использование:
    python backend/check_config.py
    python backend/check_config.py --strict  # Строгая проверка (fail on warnings)
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Добавляем backend в PYTHONPATH
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Загружаем .env перед импортом Django
from dotenv import load_dotenv
project_root = backend_dir.parent
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  .env файл не найден: {env_path}")
    sys.exit(1)

# Теперь импортируем Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings


class ConfigValidator:
    def __init__(self, strict=False):
        self.errors = []
        self.warnings = []
        self.info = []
        self.strict = strict

    def error(self, message):
        """Критическая ошибка"""
        self.errors.append(message)

    def warn(self, message):
        """Предупреждение"""
        self.warnings.append(message)

    def note(self, message):
        """Информационное сообщение"""
        self.info.append(message)

    def check_debug_mode(self):
        """Проверка режима DEBUG"""
        is_debug = settings.DEBUG

        if is_debug:
            self.note(f"🔧 Development режим (DEBUG=True)")
        else:
            self.note(f"🚀 Production режим (DEBUG=False)")

        return not is_debug  # True если production

    def check_secret_key(self, is_production):
        """Проверка SECRET_KEY"""
        secret = settings.SECRET_KEY

        if not secret or len(secret) < 50:
            self.error(f"SECRET_KEY слишком короткий: {len(secret)} символов (минимум 50)")

        if is_production and 'django-insecure-' in secret:
            self.error("Production режим с insecure SECRET_KEY!")

        if is_production:
            self.note(f"✅ SECRET_KEY: {len(secret)} символов (безопасно)")
        else:
            self.note(f"ℹ️  SECRET_KEY: {len(secret)} символов")

    def check_allowed_hosts(self, is_production):
        """Проверка ALLOWED_HOSTS"""
        hosts = settings.ALLOWED_HOSTS

        if not hosts:
            if is_production:
                self.error("ALLOWED_HOSTS пустой в production режиме!")
            else:
                self.warn("ALLOWED_HOSTS пустой")
        elif '*' in hosts:
            if is_production:
                self.error("ALLOWED_HOSTS содержит '*' в production!")
            else:
                self.warn("ALLOWED_HOSTS содержит '*'")
        else:
            self.note(f"✅ ALLOWED_HOSTS: {', '.join(hosts)}")

    def check_database(self):
        """Проверка настроек БД"""
        db_config = settings.DATABASES.get('default', {})

        if not db_config:
            self.error("Отсутствует конфигурация БД!")
            return

        host = db_config.get('HOST', '')
        port = db_config.get('PORT', '')
        name = db_config.get('NAME', '')

        if host and port and name:
            self.note(f"✅ БД: {host}:{port}/{name}")
        else:
            self.warn("Неполная конфигурация БД")

        # Проверка таймаута
        timeout = os.getenv('DB_CONNECT_TIMEOUT', '10')
        self.note(f"   Таймаут подключения: {timeout}s")

    def check_redis(self, is_production):
        """Проверка Redis настроек"""
        use_cache = settings.USE_REDIS_CACHE
        use_channels = settings.USE_REDIS_CHANNELS
        redis_url = os.getenv('REDIS_URL', '')

        if is_production:
            if not use_cache:
                self.warn("Redis Cache отключен в production (рекомендуется включить)")
            else:
                self.note("✅ Redis Cache: Включен")

            if not use_channels:
                self.error("Redis Channels ОБЯЗАТЕЛЕН в production для WebSocket и Celery!")
            else:
                self.note("✅ Redis Channels: Включен")
        else:
            self.note(f"ℹ️  Redis Cache: {'Включен' if use_cache else 'InMemory'}")
            self.note(f"ℹ️  Redis Channels: {'Включен' if use_channels else 'InMemory'}")

        if redis_url:
            parsed = urlparse(redis_url)
            self.note(f"   Redis URL: {parsed.hostname}:{parsed.port or 6379}")

    def check_frontend_urls(self, is_production):
        """Проверка Frontend URLs"""
        frontend_url = settings.FRONTEND_URL

        if is_production:
            if not frontend_url:
                self.error("FRONTEND_URL не задан в production!")
            elif 'localhost' in frontend_url or '127.0.0.1' in frontend_url:
                self.error(f"Production режим с localhost URL: {frontend_url}")
            elif not frontend_url.startswith('https://'):
                self.warn(f"FRONTEND_URL не использует HTTPS: {frontend_url}")
            else:
                self.note(f"✅ FRONTEND_URL: {frontend_url}")
        else:
            self.note(f"ℹ️  FRONTEND_URL: {frontend_url}")

    def check_cors(self, is_production):
        """Проверка CORS настроек"""
        origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        allow_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', False)

        if allow_all:
            if is_production:
                self.error("CORS_ALLOW_ALL_ORIGINS=True в production!")
            else:
                self.note("ℹ️  CORS: Разрешены все origins (dev режим)")
        else:
            localhost_count = sum(1 for o in origins if 'localhost' in o or '127.0.0.1' in o)
            prod_count = len(origins) - localhost_count

            if is_production and localhost_count > 0:
                self.warn(f"CORS содержит {localhost_count} localhost origins в production")

            if is_production:
                self.note(f"✅ CORS: {prod_count} production origins")
            else:
                self.note(f"ℹ️  CORS: {localhost_count} dev + {prod_count} prod origins")

    def check_payment_settings(self, is_production):
        """Проверка настроек платежей"""
        payment_dev_mode = settings.PAYMENT_DEVELOPMENT_MODE
        shop_id = settings.YOOKASSA_SHOP_ID
        secret = settings.YOOKASSA_SECRET_KEY
        webhook = settings.YOOKASSA_WEBHOOK_URL

        if payment_dev_mode:
            amount = settings.DEVELOPMENT_PAYMENT_AMOUNT
            interval = settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES
            self.note(f"💰 Платежи: Development режим ({amount}₽ каждые {interval} минут)")
        else:
            amount = settings.PRODUCTION_PAYMENT_AMOUNT
            interval = settings.PRODUCTION_RECURRING_INTERVAL_WEEKS
            self.note(f"💰 Платежи: Production режим ({amount}₽ каждые {interval} недель)")

        if not shop_id or not secret:
            self.error("YooKassa credentials не настроены!")

        if webhook and is_production:
            if not webhook.endswith('/'):
                self.warn(f"YooKassa webhook должен заканчиваться на '/': {webhook}")
            elif 'localhost' in webhook:
                self.error(f"Production режим с localhost webhook: {webhook}")
            else:
                self.note(f"✅ YooKassa webhook: {webhook}")

    def check_security_settings(self, is_production):
        """Проверка security настроек"""
        if is_production:
            # Проверяем HTTPS enforcement
            if not getattr(settings, 'SECURE_SSL_REDIRECT', False):
                self.warn("SECURE_SSL_REDIRECT отключен в production")

            # Проверяем HSTS
            hsts_seconds = getattr(settings, 'SECURE_HSTS_SECONDS', 0)
            if hsts_seconds == 0:
                self.warn("HSTS отключен в production")
            else:
                self.note(f"✅ HSTS: {hsts_seconds}s")

            # Проверяем secure cookies
            if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
                self.warn("SESSION_COOKIE_SECURE отключен в production")
            if not getattr(settings, 'CSRF_COOKIE_SECURE', False):
                self.warn("CSRF_COOKIE_SECURE отключен в production")

            self.note("✅ Security settings активны")

    def run_checks(self):
        """Запуск всех проверок"""
        print("=" * 60)
        print("THE_BOT_PLATFORM - Configuration Validation")
        print("=" * 60)
        print()

        is_production = self.check_debug_mode()
        self.check_secret_key(is_production)
        self.check_allowed_hosts(is_production)
        self.check_database()
        self.check_redis(is_production)
        self.check_frontend_urls(is_production)
        self.check_cors(is_production)
        self.check_payment_settings(is_production)
        if is_production:
            self.check_security_settings(is_production)

        print()
        print("=" * 60)
        print("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
        print("=" * 60)
        print()

        # Выводим информационные сообщения
        for msg in self.info:
            print(msg)

        if self.warnings:
            print()
            print("⚠️  ПРЕДУПРЕЖДЕНИЯ:")
            for msg in self.warnings:
                print(f"   - {msg}")

        if self.errors:
            print()
            print("❌ ОШИБКИ:")
            for msg in self.errors:
                print(f"   - {msg}")

        print()
        print("=" * 60)

        # Итоговый статус
        if self.errors:
            print("❌ КОНФИГУРАЦИЯ СОДЕРЖИТ КРИТИЧЕСКИЕ ОШИБКИ!")
            return False
        elif self.warnings:
            if self.strict:
                print("⚠️  КОНФИГУРАЦИЯ СОДЕРЖИТ ПРЕДУПРЕЖДЕНИЯ (strict mode)")
                return False
            else:
                print("⚠️  КОНФИГУРАЦИЯ ВАЛИДНА, НО ЕСТЬ ПРЕДУПРЕЖДЕНИЯ")
                return True
        else:
            print("✅ КОНФИГУРАЦИЯ ВАЛИДНА!")
            return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate THE_BOT_platform configuration')
    parser.add_argument('--strict', action='store_true', help='Fail on warnings')
    args = parser.parse_args()

    validator = ConfigValidator(strict=args.strict)
    success = validator.run_checks()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
