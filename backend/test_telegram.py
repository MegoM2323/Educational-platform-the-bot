#!/usr/bin/env python3
"""
Скрипт для тестирования Telegram интеграции
"""
import os
import sys
import django
from pathlib import Path

# Добавляем путь к Django проекту
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from applications.telegram_service import telegram_service
from applications.models import Application
from django.utils import timezone


def test_telegram_connection():
    """Тестирует соединение с Telegram"""
    print("🔍 Тестирование соединения с Telegram...")
    
    is_connected = telegram_service.test_connection()
    
    if is_connected:
        print("✅ Соединение с Telegram успешно!")
        return True
    else:
        print("❌ Не удалось подключиться к Telegram")
        print("Проверьте настройки TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env файле")
        return False


def test_send_message():
    """Тестирует отправку сообщения"""
    print("\n📤 Тестирование отправки сообщения...")
    
    test_message = """
🧪 <b>Тестовое сообщение</b>

Это тестовое сообщение для проверки работы Telegram интеграции.

⏰ <b>Время:</b> {time}
🆔 <b>Тест ID:</b> #test-001
    """.format(time=timezone.now().strftime('%d.%m.%Y в %H:%M'))
    
    result = telegram_service.send_message(test_message)
    
    if result:
        print("✅ Тестовое сообщение отправлено успешно!")
        print(f"Message ID: {result['result']['message_id']}")
        return True
    else:
        print("❌ Не удалось отправить тестовое сообщение")
        return False


def test_application_notification():
    """Тестирует отправку уведомления о заявке"""
    print("\n📋 Тестирование уведомления о заявке...")
    
    # Создаем тестовую заявку
    test_application = Application(
        student_name="Тестовый Ученик",
        parent_name="Тестовый Родитель",
        phone="+7 (999) 123-45-67",
        email="test@example.com",
        grade=9,
        goal="Тестовая цель обучения",
        message="Это тестовое сообщение для проверки интеграции",
        created_at=timezone.now()
    )
    
    result = telegram_service.send_application_notification(test_application)
    
    if result:
        print("✅ Уведомление о заявке отправлено успешно!")
        print(f"Message ID: {result}")
        return True
    else:
        print("❌ Не удалось отправить уведомление о заявке")
        return False


def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования Telegram интеграции\n")
    
    # Проверяем настройки
    from django.conf import settings
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен в .env файле")
        return
    
    if not settings.TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID не настроен в .env файле")
        return
    
    print(f"🤖 Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {settings.TELEGRAM_CHAT_ID}")
    print()
    
    # Запускаем тесты
    tests = [
        test_telegram_connection,
        test_send_message,
        test_application_notification
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте: {e}")
    
    print(f"\n📊 Результаты тестирования: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно! Telegram интеграция работает корректно.")
    else:
        print("⚠️  Некоторые тесты не пройдены. Проверьте настройки Telegram.")


if __name__ == "__main__":
    main()
