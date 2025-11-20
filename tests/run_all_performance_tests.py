#!/usr/bin/env python
"""
Скрипт для запуска всех тестов производительности
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

def run_all_performance_tests():
    """Запуск всех тестов производительности"""
    setup_django()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Список всех тестов производительности
    all_performance_tests = [
        # Тесты производительности чата
        'tests.test_chat_performance.ChatPerformanceTestCase.test_chat_creation_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_message_sending_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_thread_creation_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_concurrent_message_sending',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_message_retrieval_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_cache_performance',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_database_query_optimization',
        'tests.test_chat_performance.ChatPerformanceTestCase.test_memory_usage',
        
        # Тесты нагрузки Telegram
        'tests.test_telegram_load.TelegramLoadTestCase.test_telegram_notification_performance',
        'tests.test_telegram_load.TelegramLoadTestCase.test_concurrent_telegram_notifications',
        'tests.test_telegram_load.TelegramLoadTestCase.test_telegram_error_handling',
        'tests.test_telegram_load.TelegramLoadTestCase.test_telegram_rate_limiting',
        'tests.test_telegram_load.TelegramLoadTestCase.test_telegram_message_processing',
        'tests.test_telegram_load.TelegramLoadTestCase.test_telegram_memory_usage',
    ]
    
    print("🚀 Запуск всех тестов производительности")
    print("=" * 80)
    print("📊 Тестируемые компоненты:")
    print("   • General Chat Forum")
    print("   • Telegram Integration")
    print("   • Database Optimization")
    print("   • Caching Strategy")
    print("   • Memory Usage")
    print("=" * 80)
    
    results = []
    test_categories = {
        'Chat Performance': [],
        'Telegram Load': [],
        'Other': []
    }
    
    for test in all_performance_tests:
        if 'test_chat_performance' in test:
            category = 'Chat Performance'
        elif 'test_telegram_load' in test:
            category = 'Telegram Load'
        else:
            category = 'Other'
        
        test_categories[category].append(test)
    
    # Запускаем тесты по категориям
    for category, tests in test_categories.items():
        if not tests:
            continue
            
        print(f"\n📈 {category}")
        print("-" * 50)
        
        for test in tests:
            print(f"\n🔍 Выполнение: {test.split('.')[-1]}")
            
            try:
                failures = test_runner.run_tests([test], verbosity=1)
                if failures:
                    results.append(f"❌ {test} - FAILED")
                    print(f"   ❌ FAILED")
                else:
                    results.append(f"✅ {test} - PASSED")
                    print(f"   ✅ PASSED")
            except Exception as e:
                results.append(f"💥 {test} - ERROR: {str(e)}")
                print(f"   💥 ERROR: {str(e)}")
    
    # Выводим итоговые результаты
    print("\n" + "=" * 80)
    print("📈 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТОВ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 80)
    
    # Группируем результаты по категориям
    for category, tests in test_categories.items():
        if not tests:
            continue
            
        category_results = [r for r in results if any(t in r for t in tests)]
        passed = len([r for r in category_results if "PASSED" in r])
        failed = len([r for r in category_results if "FAILED" in r])
        errors = len([r for r in category_results if "ERROR" in r])
        total = len(category_results)
        
        print(f"\n📊 {category}:")
        print(f"   Всего тестов: {total}")
        print(f"   ✅ Прошли: {passed}")
        print(f"   ❌ Провалились: {failed}")
        print(f"   💥 Ошибки: {errors}")
        if total > 0:
            print(f"   📈 Успешность: {(passed/total)*100:.1f}%")
    
    # Общая статистика
    passed = len([r for r in results if "PASSED" in r])
    failed = len([r for r in results if "FAILED" in r])
    errors = len([r for r in results if "ERROR" in r])
    total = len(results)
    
    print(f"\n🎯 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего тестов: {total}")
    print(f"   ✅ Прошли: {passed}")
    print(f"   ❌ Провалились: {failed}")
    print(f"   💥 Ошибки: {errors}")
    print(f"   📈 Общая успешность: {(passed/total)*100:.1f}%")
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    
    if failed > 0 or errors > 0:
        print("   ⚠️  Обнаружены проблемы с производительностью!")
        print("   🔧 Рекомендуется проверить:")
        print("      • Настройки кэширования Redis")
        print("      • Индексы базы данных")
        print("      • Оптимизацию запросов ORM")
        print("      • Конфигурацию Telegram API")
        print("      • Ограничения памяти и CPU")
        
        if failed > 0:
            print(f"\n   📋 Провалившиеся тесты:")
            for result in results:
                if "FAILED" in result:
                    print(f"      • {result.split(' - ')[0].split('.')[-1]}")
        
        if errors > 0:
            print(f"\n   🐛 Тесты с ошибками:")
            for result in results:
                if "ERROR" in result:
                    print(f"      • {result.split(' - ')[0].split('.')[-1]}")
        
        sys.exit(1)
    else:
        print("   🎉 Все тесты производительности прошли успешно!")
        print("   ✅ Система готова к продакшену")
        print("   🚀 Рекомендуется провести дополнительное нагрузочное тестирование")
        
        # Дополнительные рекомендации для продакшена
        print(f"\n🏭 РЕКОМЕНДАЦИИ ДЛЯ ПРОДАКШЕНА:")
        print("   • Настройте мониторинг производительности")
        print("   • Используйте CDN для статических файлов")
        print("   • Настройте автоматическое масштабирование")
        print("   • Реализуйте резервное копирование данных")
        print("   • Настройте логирование и алерты")

if __name__ == '__main__':
    run_all_performance_tests()
