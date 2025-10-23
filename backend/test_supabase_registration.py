#!/usr/bin/env python
"""
Простой тест для проверки регистрации через Supabase
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append('/home/mego/Python Projects/THE_BOT_platform/backend')

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.supabase_service import supabase_auth_service


def test_supabase_connection():
    """Тест подключения к Supabase"""
    try:
        # Проверяем настройки
        print("Проверка настроек Supabase...")
        print(f"SUPABASE_URL: {supabase_auth_service.url}")
        print(f"SUPABASE_KEY: {'*' * 20}...{supabase_auth_service.key[-4:] if supabase_auth_service.key else 'НЕ УСТАНОВЛЕН'}")
        
        if not supabase_auth_service.url or not supabase_auth_service.key:
            print("❌ Ошибка: SUPABASE_URL или SUPABASE_KEY не установлены")
            print("Создайте файл .env в папке backend/ с необходимыми переменными")
            return False
        
        print("✅ Настройки Supabase корректны")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке настроек: {e}")
        return False


def test_registration():
    """Тест регистрации пользователя"""
    try:
        print("\nТестирование регистрации...")
        
        # Данные для тестового пользователя
        test_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "user_data": {
                "full_name": "Тестовый Пользователь",
                "role": "student"
            }
        }
        
        result = supabase_auth_service.sign_up(
            email=test_data["email"],
            password=test_data["password"],
            user_data=test_data["user_data"]
        )
        
        if result["success"]:
            print("✅ Регистрация прошла успешно")
            print(f"ID пользователя: {result['user']['id']}")
            return True
        else:
            print(f"❌ Ошибка регистрации: {result.get('error', 'Неизвестная ошибка')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании регистрации: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование Supabase интеграции")
    print("=" * 50)
    
    # Проверяем подключение
    if not test_supabase_connection():
        print("\n❌ Тест не пройден: проблемы с настройками")
        return
    
    # Тестируем регистрацию
    if test_registration():
        print("\n✅ Все тесты пройдены успешно!")
        print("\nТеперь вы можете использовать API endpoints:")
        print("- POST /api/accounts/supabase/register/")
        print("- POST /api/accounts/supabase/login/")
        print("- GET /api/accounts/supabase/profile/")
    else:
        print("\n❌ Тест регистрации не пройден")


if __name__ == "__main__":
    main()
