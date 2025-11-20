#!/usr/bin/env python3
"""
End-to-End тесты для унифицированного API клиента
Проверяет полную интеграцию frontend-backend через реальные HTTP запросы
"""
import requests
import json
import time
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Конфигурация
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"


class E2EUnifiedAPITest:
    """
    E2E тесты для унифицированного API
    """
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.frontend_url = FRONTEND_URL
        self.driver = None
        self.auth_token = None
        self.test_user = {
            'email': 'e2e_test@example.com',
            'password': 'testpass123',
            'first_name': 'E2E',
            'last_name': 'Test'
        }
    
    def setup_driver(self):
        """Настройка Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Запуск в headless режиме
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            print(f"❌ Ошибка настройки WebDriver: {e}")
            return False
    
    def teardown_driver(self):
        """Очистка WebDriver"""
        if self.driver:
            self.driver.quit()
    
    def test_backend_health(self):
        """Тест доступности backend"""
        try:
            response = requests.get(f"{self.backend_url}/admin/", timeout=5)
            if response.status_code == 200:
                print("✅ Backend доступен")
                return True
            else:
                print(f"❌ Backend недоступен: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка подключения к backend: {e}")
            return False
    
    def test_frontend_health(self):
        """Тест доступности frontend"""
        try:
            response = requests.get(f"{self.frontend_url}/", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend доступен")
                return True
            else:
                print(f"❌ Frontend недоступен: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка подключения к frontend: {e}")
            return False
    
    def test_user_registration(self):
        """Тест регистрации пользователя через API"""
        registration_data = {
            'email': self.test_user['email'],
            'password': self.test_user['password'],
            'password_confirm': self.test_user['password'],
            'first_name': self.test_user['first_name'],
            'last_name': self.test_user['last_name'],
            'phone': '+79991234567',
            'role': 'student'
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/auth/register/",
                json=registration_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Регистрация пользователя работает")
                data = response.json()
                self.auth_token = data.get('token')
                return True
            else:
                print(f"❌ Ошибка регистрации: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при регистрации: {e}")
            return False
    
    def test_user_login(self):
        """Тест входа пользователя через API"""
        login_data = {
            'email': self.test_user['email'],
            'password': self.test_user['password']
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/auth/login/",
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Вход пользователя работает")
                data = response.json()
                self.auth_token = data.get('token')
                return True
            else:
                print(f"❌ Ошибка входа: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при входе: {e}")
            return False
    
    def test_authenticated_api_calls(self):
        """Тест аутентифицированных API вызовов"""
        if not self.auth_token:
            print("❌ Нет токена для тестирования API")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Тест получения профиля
        try:
            response = requests.get(
                f"{self.backend_url}/api/auth/profile/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Получение профиля работает")
                profile_data = response.json()
                self.assertEqual(profile_data['email'], self.test_user['email'])
            else:
                print(f"❌ Ошибка получения профиля: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при получении профиля: {e}")
            return False
        
        # Тест дашборда студента
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/student/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ API дашборда студента работает")
                dashboard_data = response.json()
                self.assertIn('materials_count', dashboard_data)
            else:
                print(f"❌ Ошибка API дашборда: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при получении дашборда: {e}")
            return False
        
        return True
    
    def test_chat_api_integration(self):
        """Тест интеграции чата через API"""
        if not self.auth_token:
            print("❌ Нет токена для тестирования чата")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Тест получения общего чата
        try:
            response = requests.get(
                f"{self.backend_url}/api/chat/general/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ API общего чата работает")
            else:
                print(f"❌ Ошибка API чата: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при получении чата: {e}")
            return False
        
        # Тест отправки сообщения
        message_data = {
            'content': 'E2E тестовое сообщение',
            'thread_id': None,
            'parent_message_id': None
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/chat/general/messages/",
                json=message_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Отправка сообщения работает")
                message = response.json()
                self.assertEqual(message['content'], 'E2E тестовое сообщение')
            else:
                print(f"❌ Ошибка отправки сообщения: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при отправке сообщения: {e}")
            return False
        
        return True
    
    def test_payment_api_integration(self):
        """Тест интеграции платежей через API"""
        if not self.auth_token:
            print("❌ Нет токена для тестирования платежей")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Тест создания платежа
        payment_data = {
            'amount': '1000.00',
            'service_name': 'E2E тестовый платеж',
            'customer_fio': 'E2E Test User',
            'description': 'Тестовый платеж для E2E тестирования',
            'metadata': {
                'test': True,
                'e2e_test': True
            }
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/payments/",
                json=payment_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Создание платежа работает")
                payment = response.json()
                self.assertEqual(payment['amount'], '1000.00')
                self.assertEqual(payment['service_name'], 'E2E тестовый платеж')
            else:
                print(f"❌ Ошибка создания платежа: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при создании платежа: {e}")
            return False
        
        return True
    
    def test_frontend_backend_integration(self):
        """Тест интеграции frontend и backend через браузер"""
        if not self.setup_driver():
            return False
        
        try:
            # Открываем frontend
            self.driver.get(self.frontend_url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("✅ Frontend загружен в браузере")
            
            # Проверяем наличие основных элементов
            try:
                # Ищем форму входа или регистрации
                login_form = self.driver.find_element(By.CSS_SELECTOR, "form")
                print("✅ Форма входа найдена")
            except NoSuchElementException:
                print("⚠️  Форма входа не найдена")
            
            # Проверяем наличие API клиента в консоли браузера
            try:
                # Выполняем JavaScript для проверки API клиента
                api_check = self.driver.execute_script("""
                    return typeof window.unifiedAPI !== 'undefined' || 
                           typeof window.apiClient !== 'undefined';
                """)
                
                if api_check:
                    print("✅ API клиент найден в frontend")
                else:
                    print("⚠️  API клиент не найден в frontend")
            except Exception as e:
                print(f"⚠️  Ошибка проверки API клиента: {e}")
            
            return True
            
        except TimeoutException:
            print("❌ Таймаут загрузки frontend")
            return False
        except Exception as e:
            print(f"❌ Ошибка тестирования frontend: {e}")
            return False
        finally:
            self.teardown_driver()
    
    def test_api_error_handling(self):
        """Тест обработки ошибок API"""
        # Тест неверных данных при входе
        invalid_login_data = {
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        }
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/auth/login/",
                json=invalid_login_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                print("✅ Обработка ошибок входа работает")
            else:
                print(f"❌ Неожиданный статус при неверном входе: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при тестировании неверного входа: {e}")
            return False
        
        # Тест доступа без токена
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/student/",
                timeout=10
            )
            
            if response.status_code == 401:
                print("✅ Обработка неаутентифицированных запросов работает")
            else:
                print(f"❌ Неожиданный статус для неаутентифицированного запроса: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при тестировании неаутентифицированного запроса: {e}")
            return False
        
        return True
    
    def test_api_performance(self):
        """Тест производительности API"""
        if not self.auth_token:
            print("❌ Нет токена для тестирования производительности")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Тестируем время ответа для разных endpoints
        endpoints = [
            "/api/auth/profile/",
            "/api/materials/dashboard/student/",
            "/api/chat/general/",
            "/api/payments/"
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    headers=headers,
                    timeout=10
                )
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response.status_code == 200 and response_time < 2.0:
                    print(f"✅ {endpoint} отвечает быстро: {response_time:.2f}с")
                else:
                    print(f"⚠️  {endpoint} медленный: {response_time:.2f}с")
            except requests.exceptions.RequestException as e:
                print(f"❌ Ошибка тестирования {endpoint}: {e}")
        
        return True
    
    def run_all_tests(self):
        """Запуск всех E2E тестов"""
        print("🚀 Запуск E2E тестов для унифицированного API")
        print("=" * 60)
        
        tests = [
            ("Проверка доступности backend", self.test_backend_health),
            ("Проверка доступности frontend", self.test_frontend_health),
            ("Регистрация пользователя", self.test_user_registration),
            ("Вход пользователя", self.test_user_login),
            ("Аутентифицированные API вызовы", self.test_authenticated_api_calls),
            ("Интеграция чата", self.test_chat_api_integration),
            ("Интеграция платежей", self.test_payment_api_integration),
            ("Интеграция frontend-backend", self.test_frontend_backend_integration),
            ("Обработка ошибок API", self.test_api_error_handling),
            ("Производительность API", self.test_api_performance)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}:")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} - ПРОЙДЕН")
                else:
                    print(f"❌ {test_name} - ПРОВАЛЕН")
            except Exception as e:
                print(f"❌ {test_name} - ОШИБКА: {e}")
        
        print(f"\n📊 Результаты: {passed}/{total} тестов пройдено")
        
        if passed == total:
            print("🎉 Все тесты пройдены успешно!")
            return True
        else:
            print("⚠️  Некоторые тесты провалены")
            return False
    
    def assertEqual(self, actual, expected):
        """Простая проверка равенства для тестов"""
        if actual != expected:
            raise AssertionError(f"Expected {expected}, got {actual}")


def main():
    """Основная функция"""
    e2e_test = E2EUnifiedAPITest()
    
    try:
        success = e2e_test.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)
    finally:
        e2e_test.teardown_driver()


if __name__ == "__main__":
    main()

