#!/usr/bin/env python
"""
Скрипт для проверки подключения к БД с таймаутом
Используется для диагностики проблем с зависанием
"""
import os
import sys
from urllib.parse import urlparse
import psycopg2
from psycopg2 import OperationalError
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Подключение превысило таймаут")

def test_connection():
    """Тестирует подключение к БД с таймаутом"""
    # Загружаем переменные окружения
    from dotenv import dotenv_values
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        env_vars = dotenv_values(env_path)
        for k, v in env_vars.items():
            if k and v is not None:
                os.environ[k] = str(v)
    
    # Получаем параметры подключения
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        parsed = urlparse(database_url)
        host = parsed.hostname
        port = parsed.port or 5432
        user = parsed.username
        password = parsed.password
        dbname = parsed.path.lstrip('/')
    else:
        host = os.getenv('SUPABASE_DB_HOST')
        port = int(os.getenv('SUPABASE_DB_PORT', '6543'))
        user = os.getenv('SUPABASE_DB_USER')
        password = os.getenv('SUPABASE_DB_PASSWORD')
        dbname = os.getenv('SUPABASE_DB_NAME')
    
    if not all([host, user, password, dbname]):
        print("❌ Не заданы параметры подключения к БД")
        return False
    
    print(f"🔍 Пытаюсь подключиться к БД: {host}:{port}/{dbname}")
    print(f"   Пользователь: {user}")
    
    # Устанавливаем таймаут через сигнал (10 секунд)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    try:
        # Пытаемся подключиться с таймаутом
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            connect_timeout=10,
            sslmode='require'
        )
        signal.alarm(0)  # Отключаем таймаут
        
        print("✅ Подключение успешно!")
        
        # Проверяем простой запрос
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"   Версия PostgreSQL: {version[:50]}...")
        
        cur.close()
        conn.close()
        return True
        
    except TimeoutError:
        signal.alarm(0)
        print("❌ Подключение превысило таймаут (10 секунд)")
        print("   Возможные причины:")
        print("   - БД недоступна")
        print("   - Проблемы с сетью/файрволом")
        print("   - Неправильный хост/порт")
        return False
        
    except OperationalError as e:
        signal.alarm(0)
        print(f"❌ Ошибка подключения: {e}")
        return False
        
    except Exception as e:
        signal.alarm(0)
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)


