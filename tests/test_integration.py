#!/usr/bin/env python3
"""
Скрипт для тестирования интеграции между фронтендом и бекендом
"""
import requests
import json
import sys

# Конфигурация
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

def test_backend_health():
    """Тестирует доступность бекенда"""
    try:
        response = requests.get(f"{BACKEND_URL}/admin/", timeout=5)
        print("✅ Бекенд доступен")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Бекенд недоступен: {e}")
        return False

def test_api_endpoints():
    """Тестирует основные API endpoints"""
    endpoints = [
        "/api/auth/register/",
        "/api/auth/login/",
        "/api/auth/logout/",
        "/api/auth/profile/",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if response.status_code in [200, 405, 401]:  # 405 = Method Not Allowed (но endpoint существует)
                print(f"✅ Endpoint {endpoint} доступен")
            else:
                print(f"⚠️  Endpoint {endpoint} вернул статус {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Endpoint {endpoint} недоступен: {e}")

def test_registration():
    """Тестирует регистрацию пользователя"""
    test_user = {
        "email": "test@example.com",
        "password": "testpassword123",
        "password_confirm": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "phone": "+79991234567",
        "role": "student"
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/register/",
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 201:
            print("✅ Регистрация работает")
            return response.json().get('token')
        else:
            print(f"❌ Ошибка регистрации: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при регистрации: {e}")
        return None

def test_login():
    """Тестирует вход пользователя"""
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login/",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Вход работает")
            return response.json().get('token')
        else:
            print(f"❌ Ошибка входа: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при входе: {e}")
        return None

def test_profile(token):
    """Тестирует получение профиля"""
    if not token:
        print("❌ Нет токена для тестирования профиля")
        return False
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/auth/profile/",
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Получение профиля работает")
            return True
        else:
            print(f"❌ Ошибка получения профиля: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при получении профиля: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование интеграции фронтенд-бекенд")
    print("=" * 50)
    
    # Тестируем доступность бекенда
    if not test_backend_health():
        print("❌ Бекенд недоступен. Убедитесь, что Django сервер запущен.")
        sys.exit(1)
    
    print("\n📋 Тестирование API endpoints:")
    test_api_endpoints()
    
    print("\n👤 Тестирование аутентификации:")
    # Тестируем регистрацию
    token = test_registration()
    
    # Если регистрация не сработала, пробуем вход
    if not token:
        print("Пробуем войти с существующим пользователем...")
        token = test_login()
    
    # Тестируем профиль
    if token:
        test_profile(token)
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    main()
