#!/usr/bin/env python
"""
Скрипт для запуска тестов производительности
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

def setup_django():
    """Настройка Django для тестов"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

def run_performance_tests():
    """Запуск тестов производительности"""
    setup_django()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Список тестов производительности
    performance_tests = [
        'tests.test_chat_performance.ChatPerformanceTestCase.test_chat_creation_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_message_sending_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_thread_creation_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_concurrent_message_sending',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_message_retrieval_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_cache_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_database_query_optimization',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_memory_usage',
    ]
    
    print("🚀 Запуск тестов производительности для General Chat Forum")
    print("=" * 60)
    
    results = []
    
    for test in performance_tests:
        print(f"\n📊 Выполнение: {test}")
        print("-" * 40)
        
        try:
            failures = test_runner.run_tests([test], verbosity=2)
            if failures:
                results.append(f"❌ {test} - FAILED")
            else:
                results.append(f"✅ {test} - PASSED")
        except Exception as e:
            results.append(f"💥 {test} - ERROR: {str(e)}")
    
    # Выводим итоговые результаты
    print("\n" + "=" * 60)
    print("📈 РЕЗУЛЬТАТЫ ТЕСТОВ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 60)
    
    for result in results:
        print(result)
    
    # Подсчитываем статистику
    passed = len([r for r in results if "PASSED" in r])
    failed = len([r for r in results if "FAILED" in r])
    errors = len([r for r in results if "ERROR" in r])
    total = len(results)
    
    print(f"\n📊 Статистика:")
    print(f"   Всего тестов: {total}")
    print(f"   ✅ Прошли: {passed}")
    print(f"   ❌ Провалились: {failed}")
    print(f"   💥 Ошибки: {errors}")
    print(f"   📈 Успешность: {(passed/total)*100:.1f}%")
    
    if failed > 0 or errors > 0:
        print(f"\n⚠️  Обнаружены проблемы с производительностью!")
        print("   Рекомендуется проверить:")
        print("   - Настройки кэширования")
        print("   - Индексы базы данных")
        print("   - Оптимизацию запросов")
        sys.exit(1)
    else:
        print(f"\n🎉 Все тесты производительности прошли успешно!")
        print("   Система готова к нагрузочному тестированию.")

if __name__ == '__main__':
    run_performance_tests()
