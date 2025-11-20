#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов унифицированного API
Включает unit тесты, интеграционные тесты и E2E тесты
"""
import subprocess
import sys
import os
import time
from pathlib import Path

# Добавляем путь к backend
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

def run_command(command, description):
    """Запуск команды с обработкой ошибок"""
    print(f"\n🚀 {description}")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        print("✅ Команда выполнена успешно")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения команды: {e}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def check_services():
    """Проверка доступности сервисов"""
    print("🔍 Проверка доступности сервисов")
    print("=" * 50)
    
    # Проверяем Django сервер
    try:
        import requests
        response = requests.get("http://localhost:8000/admin/", timeout=5)
        if response.status_code == 200:
            print("✅ Django сервер доступен")
        else:
            print("❌ Django сервер недоступен")
            return False
    except Exception as e:
        print(f"❌ Django сервер недоступен: {e}")
        return False
    
    # Проверяем frontend сервер
    try:
        response = requests.get("http://localhost:5173/", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend сервер доступен")
        else:
            print("❌ Frontend сервер недоступен")
            return False
    except Exception as e:
        print(f"❌ Frontend сервер недоступен: {e}")
        return False
    
    return True

def run_django_tests():
    """Запуск Django unit тестов"""
    print("\n🧪 Запуск Django unit тестов")
    print("=" * 50)
    
    # Переходим в директорию backend
    os.chdir(backend_path)
    
    # Запускаем тесты
    command = "python manage.py test --verbosity=2"
    return run_command(command, "Django unit тесты")

def run_integration_tests():
    """Запуск интеграционных тестов"""
    print("\n🔗 Запуск интеграционных тестов")
    print("=" * 50)
    
    # Переходим в директорию tests
    tests_path = Path(__file__).parent
    os.chdir(tests_path)
    
    # Запускаем интеграционные тесты
    command = "python test_unified_api_integration.py"
    return run_command(command, "Интеграционные тесты")

def run_e2e_tests():
    """Запуск E2E тестов"""
    print("\n🌐 Запуск E2E тестов")
    print("=" * 50)
    
    # Переходим в директорию tests
    tests_path = Path(__file__).parent
    os.chdir(tests_path)
    
    # Запускаем E2E тесты
    command = "python test_e2e_unified_api.py"
    return run_command(command, "E2E тесты")

def run_frontend_tests():
    """Запуск frontend тестов"""
    print("\n⚛️  Запуск frontend тестов")
    print("=" * 50)
    
    # Переходим в директорию frontend
    frontend_path = Path(__file__).parent.parent / "frontend"
    os.chdir(frontend_path)
    
    # Проверяем наличие package.json
    if not (frontend_path / "package.json").exists():
        print("❌ package.json не найден в frontend директории")
        return False
    
    # Устанавливаем зависимости если нужно
    if not (frontend_path / "node_modules").exists():
        print("📦 Установка frontend зависимостей...")
        install_command = "npm install"
        if not run_command(install_command, "Установка зависимостей"):
            return False
    
    # Запускаем тесты
    test_command = "npm test -- --run"
    return run_command(test_command, "Frontend тесты")

def run_linting():
    """Запуск линтеров"""
    print("\n🔍 Запуск линтеров")
    print("=" * 50)
    
    # Backend линтинг
    print("Python линтинг:")
    os.chdir(backend_path)
    backend_lint = run_command("python -m flake8 . --exclude=migrations,venv", "Python линтинг")
    
    # Frontend линтинг
    print("\nFrontend линтинг:")
    frontend_path = Path(__file__).parent.parent / "frontend"
    os.chdir(frontend_path)
    frontend_lint = run_command("npm run lint", "Frontend линтинг")
    
    return backend_lint and frontend_lint

def generate_test_report():
    """Генерация отчета о тестировании"""
    print("\n📊 Генерация отчета о тестировании")
    print("=" * 50)
    
    report_content = f"""
# Отчет о тестировании унифицированного API

## Время выполнения: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Выполненные тесты:

### 1. Unit тесты Django
- Тестирование моделей
- Тестирование views
- Тестирование serializers
- Тестирование API endpoints

### 2. Интеграционные тесты
- Тестирование взаимодействия frontend-backend
- Тестирование аутентификации
- Тестирование дашбордов
- Тестирование чата
- Тестирование платежей

### 3. E2E тесты
- Тестирование полного пользовательского сценария
- Тестирование в реальном браузере
- Тестирование производительности

### 4. Frontend тесты
- Тестирование React компонентов
- Тестирование API клиента
- Тестирование хуков

## Рекомендации:

1. Убедитесь, что все сервисы запущены перед тестированием
2. Проверьте настройки окружения
3. Убедитесь, что база данных мигрирована
4. Проверьте доступность внешних сервисов (Supabase, YooKassa)

## Следующие шаги:

1. Исправьте найденные ошибки
2. Добавьте недостающие тесты
3. Улучшите покрытие кода
4. Настройте автоматическое тестирование в CI/CD
"""
    
    # Сохраняем отчет
    report_path = Path(__file__).parent / "test_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ Отчет сохранен в {report_path}")
    return True

def main():
    """Основная функция"""
    print("🚀 Запуск полного тестирования унифицированного API")
    print("=" * 60)
    
    # Сохраняем текущую директорию
    original_dir = os.getcwd()
    
    try:
        # Проверяем доступность сервисов
        if not check_services():
            print("\n❌ Сервисы недоступны. Убедитесь, что:")
            print("   - Django сервер запущен на порту 8000")
            print("   - Frontend сервер запущен на порту 5173")
            print("   - База данных настроена и мигрирована")
            sys.exit(1)
        
        # Запускаем тесты
        test_results = []
        
        # 1. Django unit тесты
        test_results.append(("Django unit тесты", run_django_tests()))
        
        # 2. Интеграционные тесты
        test_results.append(("Интеграционные тесты", run_integration_tests()))
        
        # 3. E2E тесты
        test_results.append(("E2E тесты", run_e2e_tests()))
        
        # 4. Frontend тесты
        test_results.append(("Frontend тесты", run_frontend_tests()))
        
        # 5. Линтинг
        test_results.append(("Линтинг", run_linting()))
        
        # Генерируем отчет
        generate_test_report()
        
        # Выводим результаты
        print("\n📊 Итоговые результаты:")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\nОбщий результат: {passed}/{total} тестов пройдено")
        
        if passed == total:
            print("🎉 Все тесты пройдены успешно!")
            return 0
        else:
            print("⚠️  Некоторые тесты провалены")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        return 1
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        return 1
    finally:
        # Возвращаемся в исходную директорию
        os.chdir(original_dir)

if __name__ == "__main__":
    sys.exit(main())

