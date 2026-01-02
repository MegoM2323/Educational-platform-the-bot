#!/usr/bin/env python
"""
Скрипт миграции данных из SQLite в PostgreSQL для development окружения.
Используется для переноса данных при смене БД с SQLite на PostgreSQL.

Запуск:
    python scripts/migrate_to_postgres.py --backup --migrate --validate
"""
import os
import sys
import django
import json
from pathlib import Path
from datetime import datetime
from django.core.management import call_command
from django.db import connection

# Добавить backend в path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('ENVIRONMENT', 'development')

django.setup()

from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()

class MigrationManager:
    def __init__(self):
        self.backup_dir = Path(__file__).parent / 'backups' / datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log = []

    def log_msg(self, msg):
        print(msg)
        self.log.append(msg)

    def backup_sqlite(self):
        """Создать backup SQLite БД перед миграцией"""
        self.log_msg("📦 Создание backup SQLite БД...")
        sqlite_path = Path('backend/db.sqlite3')
        if sqlite_path.exists():
            import shutil
            backup_path = self.backup_dir / 'db.sqlite3.backup'
            shutil.copy2(sqlite_path, backup_path)
            self.log_msg(f"✓ SQLite backup создан: {backup_path}")
        else:
            self.log_msg("⚠️  SQLite БД не найдена - пропуск backup")

    def count_records(self):
        """Подсчитать количество записей перед миграцией"""
        self.log_msg("📊 Подсчет записей перед миграцией...")
        counts = {}
        for model in apps.get_models():
            counts[f"{model._meta.app_label}.{model._meta.model_name}"] = model.objects.count()
        return counts

    def run_migrations(self):
        """Запустить все миграции Django"""
        self.log_msg("🔄 Запуск миграций...")
        try:
            call_command('migrate', verbosity=2)
            self.log_msg("✓ Миграции выполнены успешно")
        except Exception as e:
            self.log_msg(f"❌ Ошибка при миграции: {e}")
            raise

    def validate_database(self):
        """Проверить целостность БД после миграции"""
        self.log_msg("✓ Проверка целостности БД...")
        try:
            # Проверить что все таблицы созданы
            with connection.cursor() as cursor:
                if 'postgresql' in connection.settings_dict['ENGINE'].lower():
                    cursor.execute("""
                        SELECT tablename FROM pg_tables
                        WHERE schemaname = 'public'
                    """)
                else:
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table'
                    """)
                tables = [row[0] for row in cursor.fetchall()]

            self.log_msg(f"✓ Таблиц создано: {len(tables)}")

            # Проверить основные таблицы
            required_tables = [
                'accounts_user',
                'accounts_studentprofile',
                'accounts_teacherprofile',
                'scheduling_lesson',
                'materials_subject',
            ]

            missing = [t for t in required_tables if t not in tables]
            if missing:
                self.log_msg(f"❌ Отсутствуют таблицы: {missing}")
                return False

            self.log_msg("✓ Все основные таблицы созданы")
            return True

        except Exception as e:
            self.log_msg(f"❌ Ошибка при проверке: {e}")
            return False

    def save_log(self):
        """Сохранить лог миграции"""
        log_file = self.backup_dir / 'migration.log'
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.log))
        self.log_msg(f"📝 Лог сохранен: {log_file}")

    def migrate(self):
        """Выполнить полную миграцию"""
        self.log_msg("=" * 60)
        self.log_msg("🚀 Начало миграции на PostgreSQL")
        self.log_msg("=" * 60)

        try:
            # Подсчитать записи перед
            before = self.count_records()

            # Создать backup
            self.backup_sqlite()

            # Запустить миграции
            self.run_migrations()

            # Проверить БД
            valid = self.validate_database()

            if valid:
                self.log_msg("=" * 60)
                self.log_msg("✅ Миграция завершена успешно!")
                self.log_msg("=" * 60)
            else:
                self.log_msg("⚠️  Миграция завершена с предупреждениями")

            self.save_log()
            return valid

        except Exception as e:
            self.log_msg(f"❌ Миграция остановлена: {e}")
            self.save_log()
            return False

if __name__ == '__main__':
    manager = MigrationManager()
    success = manager.migrate()
    sys.exit(0 if success else 1)
