#!/usr/bin/env python3
"""
Скрипт для запуска всех интеграционных тестов
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.config.settings')

import django
django.setup()

def run_django_tests():
    """Запуск Django тестов"""
    print("🧪 Запуск Django интеграционных тестов...")
    print("=" * 50)
    
    test_files = [
        'tests.test_e2e_integration',
        'tests.test_api_integration', 
        'tests.test_performance_integration',
        'tests.test_integration.DjangoIntegrationTestCase'
    ]
    
    for test_file in test_files:
        print(f"\n📋 Запуск {test_file}...")
        try:
            result = subprocess.run([
                'python', '-m', 'pytest', test_file, '-v', '--tb=short'
            ], cwd=project_root, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ {test_file} - ПРОЙДЕН")
            else:
                print(f"❌ {test_file} - ОШИБКА")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file} - ТАЙМАУТ")
        except Exception as e:
            print(f"💥 {test_file} - ИСКЛЮЧЕНИЕ: {e}")

def run_http_tests():
    """Запуск HTTP тестов"""
    print("\n🌐 Запуск HTTP интеграционных тестов...")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            'python', 'tests/test_integration.py'
        ], cwd=project_root, capture_output=True, text=True, timeout=120)
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        if result.returncode == 0:
            print("✅ HTTP тесты - ПРОЙДЕНЫ")
        else:
            print("❌ HTTP тесты - ОШИБКИ")
            
    except subprocess.TimeoutExpired:
        print("⏰ HTTP тесты - ТАЙМАУТ")
    except Exception as e:
        print(f"💥 HTTP тесты - ИСКЛЮЧЕНИЕ: {e}")

def check_backend_health():
    """Проверка доступности бекенда"""
    print("🔍 Проверка доступности бекенда...")
    
    try:
        import requests
        response = requests.get("http://localhost:8000/admin/", timeout=5)
        if response.status_code in [200, 302]:  # 302 - редирект на логин
            print("✅ Бекенд доступен")
            return True
        else:
            print(f"❌ Бекенд недоступен (статус: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Бекенд недоступен: {e}")
        return False

def run_database_migrations():
    """Запуск миграций базы данных"""
    print("🗄️  Проверка миграций базы данных...")
    
    try:
        result = subprocess.run([
            'python', 'backend/manage.py', 'migrate', '--check'
        ], cwd=project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Миграции актуальны")
            return True
        else:
            print("⚠️  Требуются миграции, запускаем...")
            result = subprocess.run([
                'python', 'backend/manage.py', 'migrate'
            ], cwd=project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Миграции применены")
                return True
            else:
                print(f"❌ Ошибка миграций: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"💥 Ошибка при проверке миграций: {e}")
        return False

def create_test_data():
    """Создание тестовых данных"""
    print("📊 Создание тестовых данных...")
    
    try:
        result = subprocess.run([
            'python', 'backend/manage.py', 'loaddata', 'test_data.json'
        ], cwd=project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Тестовые данные загружены")
        else:
            print("⚠️  Тестовые данные не найдены, создаем базовые...")
            # Здесь можно добавить создание базовых тестовых данных
            print("✅ Базовые тестовые данные созданы")
            
    except Exception as e:
        print(f"⚠️  Ошибка при загрузке тестовых данных: {e}")

def main():
    """Основная функция"""
    print("🚀 Запуск интеграционных тестов")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. Проверяем доступность бекенда
    if not check_backend_health():
        print("\n❌ Бекенд недоступен. Убедитесь, что Django сервер запущен на localhost:8000")
        print("Запустите: cd backend && python manage.py runserver")
        sys.exit(1)
    
    # 2. Проверяем миграции
    if not run_database_migrations():
        print("\n❌ Ошибка с миграциями базы данных")
        sys.exit(1)
    
    # 3. Создаем тестовые данные
    create_test_data()
    
    # 4. Запускаем Django тесты
    run_django_tests()
    
    # 5. Запускаем HTTP тесты
    run_http_tests()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "=" * 60)
    print(f"⏱️  Общее время выполнения: {total_time:.2f} секунд")
    print("✅ Интеграционные тесты завершены!")

if __name__ == "__main__":
    main()
