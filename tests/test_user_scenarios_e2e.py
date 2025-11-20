#!/usr/bin/env python3
"""
E2E тесты для пользовательских сценариев
Проверяет полные пользовательские потоки через unified API
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
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Конфигурация
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"


class UserScenarioE2ETest:
    """
    E2E тесты для пользовательских сценариев
    """
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.frontend_url = FRONTEND_URL
        self.driver = None
        self.auth_tokens = {}
        self.test_users = {
            'student': {
                'email': 'student_e2e@test.com',
                'password': 'testpass123',
                'first_name': 'Студент',
                'last_name': 'E2E'
            },
            'teacher': {
                'email': 'teacher_e2e@test.com',
                'password': 'testpass123',
                'first_name': 'Преподаватель',
                'last_name': 'E2E'
            },
            'parent': {
                'email': 'parent_e2e@test.com',
                'password': 'testpass123',
                'first_name': 'Родитель',
                'last_name': 'E2E'
            }
        }
    
    def setup_driver(self):
        """Настройка Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
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
    
    def create_test_users(self):
        """Создание тестовых пользователей"""
        print("👥 Создание тестовых пользователей")
        
        for role, user_data in self.test_users.items():
            # Регистрация пользователя
            registration_data = {
                'email': user_data['email'],
                'password': user_data['password'],
                'password_confirm': user_data['password'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'phone': '+79991234567',
                'role': role
            }
            
            try:
                response = requests.post(
                    f"{self.backend_url}/api/auth/register/",
                    json=registration_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 201:
                    data = response.json()
                    self.auth_tokens[role] = data.get('token')
                    print(f"✅ Пользователь {role} создан")
                else:
                    # Пробуем войти, если пользователь уже существует
                    login_data = {
                        'email': user_data['email'],
                        'password': user_data['password']
                    }
                    
                    response = requests.post(
                        f"{self.backend_url}/api/auth/login/",
                        json=login_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.auth_tokens[role] = data.get('token')
                        print(f"✅ Пользователь {role} вошел в систему")
                    else:
                        print(f"❌ Ошибка создания/входа пользователя {role}")
                        return False
            except Exception as e:
                print(f"❌ Ошибка при создании пользователя {role}: {e}")
                return False
        
        return True
    
    def test_student_workflow(self):
        """Тест полного workflow студента"""
        print("\n🎓 Тестирование workflow студента")
        
        if 'student' not in self.auth_tokens:
            print("❌ Нет токена студента")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_tokens['student']}",
            "Content-Type": "application/json"
        }
        
        # 1. Получение дашборда студента
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/student/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Дашборд студента получен")
                dashboard_data = response.json()
                print(f"   Материалов: {dashboard_data.get('materials_count', 0)}")
                print(f"   Прогресс: {dashboard_data.get('progress_percentage', 0)}%")
            else:
                print(f"❌ Ошибка получения дашборда: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении дашборда: {e}")
            return False
        
        # 2. Получение назначенных материалов
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/materials/student/assigned/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Назначенные материалы получены")
                materials = response.json()
                print(f"   Количество материалов: {len(materials)}")
            else:
                print(f"❌ Ошибка получения материалов: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении материалов: {e}")
            return False
        
        # 3. Участие в общем чате
        try:
            # Получение общего чата
            response = requests.get(
                f"{self.backend_url}/api/chat/general/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Общий чат получен")
                
                # Отправка сообщения
                message_data = {
                    'content': 'Привет! Я студент E2E тест',
                    'thread_id': None,
                    'parent_message_id': None
                }
                
                response = requests.post(
                    f"{self.backend_url}/api/chat/general/messages/",
                    json=message_data,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 201:
                    print("✅ Сообщение в чат отправлено")
                else:
                    print(f"❌ Ошибка отправки сообщения: {response.status_code}")
                    return False
            else:
                print(f"❌ Ошибка получения чата: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при работе с чатом: {e}")
            return False
        
        return True
    
    def test_teacher_workflow(self):
        """Тест полного workflow преподавателя"""
        print("\n👨‍🏫 Тестирование workflow преподавателя")
        
        if 'teacher' not in self.auth_tokens:
            print("❌ Нет токена преподавателя")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_tokens['teacher']}",
            "Content-Type": "application/json"
        }
        
        # 1. Получение дашборда преподавателя
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/teacher/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Дашборд преподавателя получен")
                dashboard_data = response.json()
                print(f"   Студентов: {dashboard_data.get('total_students', 0)}")
                print(f"   Материалов: {dashboard_data.get('total_materials', 0)}")
            else:
                print(f"❌ Ошибка получения дашборда: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении дашборда: {e}")
            return False
        
        # 2. Создание материала
        try:
            material_data = {
                'title': 'E2E тестовый материал',
                'description': 'Материал для E2E тестирования',
                'content': 'Содержание тестового материала',
                'material_type': 'assignment',
                'subject': 'Математика'
            }
            
            response = requests.post(
                f"{self.backend_url}/api/materials/materials/teacher/create/",
                json=material_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Материал создан")
                material = response.json()
                print(f"   ID материала: {material.get('id')}")
            else:
                print(f"❌ Ошибка создания материала: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при создании материала: {e}")
            return False
        
        # 3. Получение списка студентов
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/teacher/students/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Список студентов получен")
                students = response.json()
                print(f"   Количество студентов: {len(students)}")
            else:
                print(f"❌ Ошибка получения студентов: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении студентов: {e}")
            return False
        
        return True
    
    def test_parent_workflow(self):
        """Тест полного workflow родителя"""
        print("\n👨‍👩‍👧‍👦 Тестирование workflow родителя")
        
        if 'parent' not in self.auth_tokens:
            print("❌ Нет токена родителя")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_tokens['parent']}",
            "Content-Type": "application/json"
        }
        
        # 1. Получение дашборда родителя
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/parent/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Дашборд родителя получен")
                dashboard_data = response.json()
                print(f"   Детей: {dashboard_data.get('total_children', 0)}")
                print(f"   Предметов: {dashboard_data.get('total_subjects', 0)}")
            else:
                print(f"❌ Ошибка получения дашборда: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении дашборда: {e}")
            return False
        
        # 2. Получение информации о детях
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/parent/children/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Информация о детях получена")
                children = response.json()
                print(f"   Количество детей: {len(children)}")
            else:
                print(f"❌ Ошибка получения детей: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении детей: {e}")
            return False
        
        # 3. Создание платежа
        try:
            payment_data = {
                'amount': '5000.00',
                'service_name': 'E2E тестовый платеж',
                'customer_fio': 'Родитель E2E',
                'description': 'Тестовый платеж для E2E тестирования',
                'metadata': {
                    'test': True,
                    'e2e_scenario': 'parent_workflow'
                }
            }
            
            response = requests.post(
                f"{self.backend_url}/api/payments/",
                json=payment_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Платеж создан")
                payment = response.json()
                print(f"   ID платежа: {payment.get('id')}")
                print(f"   Сумма: {payment.get('amount')}")
            else:
                print(f"❌ Ошибка создания платежа: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при создании платежа: {e}")
            return False
        
        return True
    
    def test_cross_user_communication(self):
        """Тест взаимодействия между пользователями"""
        print("\n💬 Тестирование взаимодействия между пользователями")
        
        # Студент отправляет сообщение
        if 'student' not in self.auth_tokens:
            print("❌ Нет токена студента")
            return False
        
        student_headers = {
            "Authorization": f"Token {self.auth_tokens['student']}",
            "Content-Type": "application/json"
        }
        
        try:
            message_data = {
                'content': 'Привет! Это сообщение от студента в E2E тесте',
                'thread_id': None,
                'parent_message_id': None
            }
            
            response = requests.post(
                f"{self.backend_url}/api/chat/general/messages/",
                json=message_data,
                headers=student_headers,
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Студент отправил сообщение")
                student_message = response.json()
                message_id = student_message.get('id')
            else:
                print(f"❌ Ошибка отправки сообщения студентом: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при отправке сообщения студентом: {e}")
            return False
        
        # Преподаватель отвечает на сообщение
        if 'teacher' not in self.auth_tokens:
            print("❌ Нет токена преподавателя")
            return False
        
        teacher_headers = {
            "Authorization": f"Token {self.auth_tokens['teacher']}",
            "Content-Type": "application/json"
        }
        
        try:
            reply_data = {
                'content': 'Привет! Это ответ от преподавателя в E2E тесте',
                'thread_id': None,
                'parent_message_id': message_id
            }
            
            response = requests.post(
                f"{self.backend_url}/api/chat/general/messages/",
                json=reply_data,
                headers=teacher_headers,
                timeout=10
            )
            
            if response.status_code == 201:
                print("✅ Преподаватель ответил на сообщение")
            else:
                print(f"❌ Ошибка ответа преподавателя: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при ответе преподавателя: {e}")
            return False
        
        # Проверяем, что оба сообщения видны
        try:
            response = requests.get(
                f"{self.backend_url}/api/chat/general/messages/",
                headers=student_headers,
                timeout=10
            )
            
            if response.status_code == 200:
                messages_data = response.json()
                messages = messages_data.get('results', [])
                print(f"✅ Получено сообщений в чате: {len(messages)}")
                
                # Ищем наши тестовые сообщения
                student_message_found = False
                teacher_message_found = False
                
                for message in messages:
                    if 'студента в E2E тесте' in message.get('content', ''):
                        student_message_found = True
                    if 'преподавателя в E2E тесте' in message.get('content', ''):
                        teacher_message_found = True
                
                if student_message_found and teacher_message_found:
                    print("✅ Оба сообщения найдены в чате")
                else:
                    print("❌ Не все сообщения найдены в чате")
                    return False
            else:
                print(f"❌ Ошибка получения сообщений: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при получении сообщений: {e}")
            return False
        
        return True
    
    def test_error_scenarios(self):
        """Тест сценариев ошибок"""
        print("\n⚠️  Тестирование сценариев ошибок")
        
        # 1. Попытка доступа без аутентификации
        try:
            response = requests.get(
                f"{self.backend_url}/api/materials/dashboard/student/",
                timeout=10
            )
            
            if response.status_code == 401:
                print("✅ Неаутентифицированный доступ корректно отклонен")
            else:
                print(f"❌ Неожиданный статус для неаутентифицированного доступа: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при тестировании неаутентифицированного доступа: {e}")
            return False
        
        # 2. Попытка доступа к чужим данным
        if 'student' in self.auth_tokens:
            student_headers = {
                "Authorization": f"Token {self.auth_tokens['student']}",
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.get(
                    f"{self.backend_url}/api/materials/dashboard/parent/",
                    headers=student_headers,
                    timeout=10
                )
                
                if response.status_code == 403:
                    print("✅ Доступ к чужим данным корректно отклонен")
                else:
                    print(f"❌ Неожиданный статус для доступа к чужим данным: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Ошибка при тестировании доступа к чужим данным: {e}")
                return False
        
        # 3. Неверные данные при создании платежа
        if 'parent' in self.auth_tokens:
            parent_headers = {
                "Authorization": f"Token {self.auth_tokens['parent']}",
                "Content-Type": "application/json"
            }
            
            try:
                invalid_payment_data = {
                    'amount': 'invalid_amount',
                    'service_name': '',
                    'customer_fio': '',
                    'description': ''
                }
                
                response = requests.post(
                    f"{self.backend_url}/api/payments/",
                    json=invalid_payment_data,
                    headers=parent_headers,
                    timeout=10
                )
                
                if response.status_code == 400:
                    print("✅ Неверные данные платежа корректно отклонены")
                else:
                    print(f"❌ Неожиданный статус для неверных данных платежа: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Ошибка при тестировании неверных данных платежа: {e}")
                return False
        
        return True
    
    def test_performance_scenarios(self):
        """Тест сценариев производительности"""
        print("\n⚡ Тестирование сценариев производительности")
        
        if 'student' not in self.auth_tokens:
            print("❌ Нет токена студента")
            return False
        
        headers = {
            "Authorization": f"Token {self.auth_tokens['student']}",
            "Content-Type": "application/json"
        }
        
        # Тест множественных запросов
        endpoints = [
            "/api/materials/dashboard/student/",
            "/api/materials/materials/student/assigned/",
            "/api/chat/general/",
            "/api/chat/general/messages/"
        ]
        
        total_time = 0
        successful_requests = 0
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    headers=headers,
                    timeout=10
                )
                end_time = time.time()
                
                request_time = end_time - start_time
                total_time += request_time
                
                if response.status_code == 200:
                    successful_requests += 1
                    print(f"✅ {endpoint}: {request_time:.2f}с")
                else:
                    print(f"❌ {endpoint}: {response.status_code} ({request_time:.2f}с)")
            except Exception as e:
                print(f"❌ {endpoint}: Ошибка - {e}")
        
        average_time = total_time / len(endpoints)
        success_rate = (successful_requests / len(endpoints)) * 100
        
        print(f"\n📊 Результаты производительности:")
        print(f"   Успешных запросов: {successful_requests}/{len(endpoints)} ({success_rate:.1f}%)")
        print(f"   Среднее время ответа: {average_time:.2f}с")
        print(f"   Общее время: {total_time:.2f}с")
        
        # Проверяем, что производительность приемлема
        if average_time < 2.0 and success_rate >= 75:
            print("✅ Производительность приемлема")
            return True
        else:
            print("⚠️  Производительность требует улучшения")
            return False
    
    def run_all_scenarios(self):
        """Запуск всех пользовательских сценариев"""
        print("🚀 Запуск E2E тестов пользовательских сценариев")
        print("=" * 60)
        
        # Создаем тестовых пользователей
        if not self.create_test_users():
            print("❌ Не удалось создать тестовых пользователей")
            return False
        
        # Запускаем сценарии
        scenarios = [
            ("Workflow студента", self.test_student_workflow),
            ("Workflow преподавателя", self.test_teacher_workflow),
            ("Workflow родителя", self.test_parent_workflow),
            ("Взаимодействие между пользователями", self.test_cross_user_communication),
            ("Сценарии ошибок", self.test_error_scenarios),
            ("Сценарии производительности", self.test_performance_scenarios)
        ]
        
        passed = 0
        total = len(scenarios)
        
        for scenario_name, scenario_func in scenarios:
            print(f"\n📋 {scenario_name}:")
            try:
                if scenario_func():
                    passed += 1
                    print(f"✅ {scenario_name} - ПРОЙДЕН")
                else:
                    print(f"❌ {scenario_name} - ПРОВАЛЕН")
            except Exception as e:
                print(f"❌ {scenario_name} - ОШИБКА: {e}")
        
        print(f"\n📊 Результаты: {passed}/{total} сценариев пройдено")
        
        if passed == total:
            print("🎉 Все пользовательские сценарии пройдены успешно!")
            return True
        else:
            print("⚠️  Некоторые сценарии провалены")
            return False


def main():
    """Основная функция"""
    e2e_test = UserScenarioE2ETest()
    
    try:
        success = e2e_test.run_all_scenarios()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

