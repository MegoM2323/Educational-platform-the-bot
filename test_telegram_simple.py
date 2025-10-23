#!/usr/bin/env python3
"""
Простой тест Telegram интеграции
"""
import os
import sys
import requests
from pathlib import Path

# Добавляем путь к Django проекту
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "backend"))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from applications.telegram_service import telegram_service

def test_telegram():
    """Тестирует Telegram интеграцию"""
    print("🔍 Тестирование Telegram интеграции...")
    
    # Проверяем настройки
    from django.conf import settings
    
    print(f"Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"Chat ID: {settings.TELEGRAM_CHAT_ID}")
    
    # Тестируем соединение
    print("\n📡 Тестирование соединения...")
    is_connected = telegram_service.test_connection()
    
    if is_connected:
        print("✅ Соединение с Telegram успешно!")
        
        # Тестируем отправку сообщения
        print("\n📤 Тестирование отправки сообщения...")
        test_message = "🧪 Тестовое сообщение для проверки интеграции"
        
        result = telegram_service.send_message(test_message)
        
        if result:
            print("✅ Сообщение отправлено успешно!")
            print(f"Message ID: {result['result']['message_id']}")
        else:
            print("❌ Не удалось отправить сообщение")
    else:
        print("❌ Не удалось подключиться к Telegram")
        print("Проверьте настройки TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID")

if __name__ == "__main__":
    test_telegram()
