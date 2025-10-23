#!/usr/bin/env python
"""
Скрипт для тестирования API регистрации через Supabase
"""
import requests
import json


def test_supabase_registration():
    """Тест регистрации через Supabase API"""
    
    # URL вашего Django сервера
    base_url = "http://localhost:8000"
    
    # Данные для регистрации
    registration_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "password_confirm": "testpassword123",
        "first_name": "Тестовый",
        "last_name": "Пользователь",
        "phone": "+7900123456",
        "role": "student"
    }
    
    print("🚀 Тестирование API регистрации через Supabase")
    print("=" * 60)
    
    try:
        # Тест регистрации
        print("1. Тестирование регистрации...")
        response = requests.post(
            f"{base_url}/api/accounts/supabase/register/",
            json=registration_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Регистрация успешна!")
            print(f"ID пользователя: {data['user']['id']}")
            print(f"Email: {data['user']['email']}")
            
            # Сохраняем токен для дальнейших тестов
            if 'session' in data and 'access_token' in data['session']:
                access_token = data['session']['access_token']
                print(f"Access Token: {access_token[:20]}...")
                
                # Тест получения профиля
                print("\n2. Тестирование получения профиля...")
                profile_response = requests.get(
                    f"{base_url}/api/accounts/supabase/profile/",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                print(f"Статус профиля: {profile_response.status_code}")
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    print("✅ Профиль получен успешно!")
                    print(f"Имя: {profile_data.get('profile', {}).get('full_name', 'Не указано')}")
                    print(f"Роли: {profile_data.get('roles', [])}")
                else:
                    print(f"❌ Ошибка получения профиля: {profile_response.text}")
                
                # Тест обновления профиля
                print("\n3. Тестирование обновления профиля...")
                update_data = {
                    "full_name": "Обновленное Имя",
                    "phone": "+7900999999"
                }
                
                update_response = requests.put(
                    f"{base_url}/api/accounts/supabase/profile/update/",
                    json=update_data,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                print(f"Статус обновления: {update_response.status_code}")
                
                if update_response.status_code == 200:
                    print("✅ Профиль обновлен успешно!")
                else:
                    print(f"❌ Ошибка обновления профиля: {update_response.text}")
                
                # Тест входа
                print("\n4. Тестирование входа...")
                login_data = {
                    "email": "test@example.com",
                    "password": "testpassword123"
                }
                
                login_response = requests.post(
                    f"{base_url}/api/accounts/supabase/login/",
                    json=login_data,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"Статус входа: {login_response.status_code}")
                
                if login_response.status_code == 200:
                    print("✅ Вход выполнен успешно!")
                else:
                    print(f"❌ Ошибка входа: {login_response.text}")
                
                # Тест выхода
                print("\n5. Тестирование выхода...")
                logout_response = requests.post(
                    f"{base_url}/api/accounts/supabase/logout/",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                print(f"Статус выхода: {logout_response.status_code}")
                
                if logout_response.status_code == 200:
                    print("✅ Выход выполнен успешно!")
                else:
                    print(f"❌ Ошибка выхода: {logout_response.text}")
                
            else:
                print("❌ Токен доступа не получен")
                
        else:
            print(f"❌ Ошибка регистрации: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка подключения к серверу")
        print("Убедитесь, что Django сервер запущен на http://localhost:8000")
        print("Запустите сервер командой: python manage.py runserver")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")


def main():
    """Основная функция"""
    print("Тестирование API регистрации через Supabase")
    print("Убедитесь, что:")
    print("1. Django сервер запущен (python manage.py runserver)")
    print("2. Настроены переменные окружения для Supabase")
    print("3. Supabase проект настроен и доступен")
    print()
    
    test_supabase_registration()


if __name__ == "__main__":
    main()
