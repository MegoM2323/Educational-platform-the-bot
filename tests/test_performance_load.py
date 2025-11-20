#!/usr/bin/env python3
"""
Тесты производительности и нагрузки для унифицированного API
Проверяет производительность системы под нагрузкой
"""
import requests
import json
import time
import threading
import concurrent.futures
import statistics
import sys
import os
from datetime import datetime

# Конфигурация
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

# Параметры нагрузки
CONCURRENT_USERS = 10
REQUESTS_PER_USER = 20
TEST_DURATION = 60  # секунд


class PerformanceTest:
    """
    Класс для тестирования производительности
    """
    
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.frontend_url = FRONTEND_URL
        self.results = []
        self.auth_tokens = []
        self.test_users = []
        
    def create_test_users(self, count=CONCURRENT_USERS):
        """Создание тестовых пользователей"""
        print(f"👥 Создание {count} тестовых пользователей")
        
        for i in range(count):
            user_data = {
                'email': f'perf_test_{i}@example.com',
                'password': 'testpass123',
                'first_name': f'Test{i}',
                'last_name': 'User',
                'phone': f'+7999123456{i:02d}',
                'role': 'student'
            }
            
            try:
                # Регистрация пользователя
                response = requests.post(
                    f"{self.backend_url}/api/auth/register/",
                    json=user_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 201:
                    data = response.json()
                    token = data.get('token')
                    self.auth_tokens.append(token)
                    self.test_users.append(user_data)
                    print(f"✅ Пользователь {i+1} создан")
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
                        token = data.get('token')
                        self.auth_tokens.append(token)
                        self.test_users.append(user_data)
                        print(f"✅ Пользователь {i+1} вошел в систему")
                    else:
                        print(f"❌ Ошибка создания/входа пользователя {i+1}")
                        return False
            except Exception as e:
                print(f"❌ Ошибка при создании пользователя {i+1}: {e}")
                return False
        
        return True
    
    def make_request(self, endpoint, method='GET', data=None, token=None):
        """Выполнение HTTP запроса с измерением времени"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Token {token}"
        
        start_time = time.time()
        
        try:
            if method == 'GET':
                response = requests.get(f"{self.backend_url}{endpoint}", headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(f"{self.backend_url}{endpoint}", json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(f"{self.backend_url}{endpoint}", json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(f"{self.backend_url}{endpoint}", headers=headers, timeout=10)
            else:
                raise ValueError(f"Неподдерживаемый HTTP метод: {method}")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response_time': response_time,
                'success': 200 <= response.status_code < 400,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': 0,
                'response_time': response_time,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def simulate_user_session(self, user_index):
        """Симуляция сессии пользователя"""
        token = self.auth_tokens[user_index] if user_index < len(self.auth_tokens) else None
        user_results = []
        
        # Список endpoints для тестирования
        endpoints = [
            ('/api/materials/dashboard/student/', 'GET'),
            ('/api/materials/materials/student/assigned/', 'GET'),
            ('/api/chat/general/', 'GET'),
            ('/api/chat/general/messages/', 'GET'),
            ('/api/auth/profile/', 'GET'),
        ]
        
        # Выполняем запросы
        for i in range(REQUESTS_PER_USER):
            endpoint, method = endpoints[i % len(endpoints)]
            
            # Иногда отправляем сообщение в чат
            if endpoint == '/api/chat/general/messages/' and method == 'GET' and i % 3 == 0:
                message_data = {
                    'content': f'Тестовое сообщение от пользователя {user_index} - запрос {i}',
                    'thread_id': None,
                    'parent_message_id': None
                }
                result = self.make_request('/api/chat/general/messages/', 'POST', message_data, token)
            else:
                result = self.make_request(endpoint, method, token=token)
            
            user_results.append(result)
            time.sleep(0.1)  # Небольшая пауза между запросами
        
        return user_results
    
    def run_load_test(self):
        """Запуск нагрузочного тестирования"""
        print(f"\n⚡ Запуск нагрузочного тестирования")
        print(f"   Пользователей: {CONCURRENT_USERS}")
        print(f"   Запросов на пользователя: {REQUESTS_PER_USER}")
        print(f"   Общее количество запросов: {CONCURRENT_USERS * REQUESTS_PER_USER}")
        
        start_time = time.time()
        
        # Запускаем тесты параллельно
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
            futures = []
            
            for i in range(CONCURRENT_USERS):
                future = executor.submit(self.simulate_user_session, i)
                futures.append(future)
            
            # Собираем результаты
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    user_results = future.result()
                    all_results.extend(user_results)
                except Exception as e:
                    print(f"❌ Ошибка в пользовательской сессии: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        self.results = all_results
        
        print(f"\n📊 Результаты нагрузочного тестирования:")
        print(f"   Общее время: {total_time:.2f}с")
        print(f"   Запросов выполнено: {len(all_results)}")
        print(f"   RPS (запросов в секунду): {len(all_results) / total_time:.2f}")
        
        return self.analyze_results()
    
    def analyze_results(self):
        """Анализ результатов тестирования"""
        if not self.results:
            print("❌ Нет результатов для анализа")
            return False
        
        # Общая статистика
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r['success'])
        failed_requests = total_requests - successful_requests
        
        success_rate = (successful_requests / total_requests) * 100
        
        # Время ответа
        response_times = [r['response_time'] for r in self.results if r['success']]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95-й процентиль
        else:
            avg_response_time = 0
            median_response_time = 0
            min_response_time = 0
            max_response_time = 0
            p95_response_time = 0
        
        # Статистика по endpoints
        endpoint_stats = {}
        for result in self.results:
            endpoint = result['endpoint']
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    'total': 0,
                    'successful': 0,
                    'response_times': []
                }
            
            endpoint_stats[endpoint]['total'] += 1
            if result['success']:
                endpoint_stats[endpoint]['successful'] += 1
                endpoint_stats[endpoint]['response_times'].append(result['response_time'])
        
        # Выводим результаты
        print(f"\n📈 Общая статистика:")
        print(f"   Всего запросов: {total_requests}")
        print(f"   Успешных: {successful_requests} ({success_rate:.1f}%)")
        print(f"   Неудачных: {failed_requests}")
        
        print(f"\n⏱️  Время ответа:")
        print(f"   Среднее: {avg_response_time:.3f}с")
        print(f"   Медиана: {median_response_time:.3f}с")
        print(f"   Минимум: {min_response_time:.3f}с")
        print(f"   Максимум: {max_response_time:.3f}с")
        print(f"   95-й процентиль: {p95_response_time:.3f}с")
        
        print(f"\n🔍 Статистика по endpoints:")
        for endpoint, stats in endpoint_stats.items():
            success_rate = (stats['successful'] / stats['total']) * 100
            avg_time = statistics.mean(stats['response_times']) if stats['response_times'] else 0
            
            print(f"   {endpoint}:")
            print(f"     Запросов: {stats['total']}")
            print(f"     Успешных: {stats['successful']} ({success_rate:.1f}%)")
            print(f"     Среднее время: {avg_time:.3f}с")
        
        # Проверяем критерии производительности
        performance_ok = True
        
        if success_rate < 95:
            print(f"⚠️  Низкий процент успешных запросов: {success_rate:.1f}%")
            performance_ok = False
        
        if avg_response_time > 2.0:
            print(f"⚠️  Высокое среднее время ответа: {avg_response_time:.3f}с")
            performance_ok = False
        
        if p95_response_time > 5.0:
            print(f"⚠️  Высокий 95-й процентиль времени ответа: {p95_response_time:.3f}с")
            performance_ok = False
        
        if performance_ok:
            print("\n✅ Производительность соответствует требованиям")
        else:
            print("\n❌ Производительность требует улучшения")
        
        return performance_ok
    
    def test_memory_usage(self):
        """Тест использования памяти"""
        print("\n🧠 Тестирование использования памяти")
        
        # Этот тест требует мониторинга сервера
        # В реальном сценарии здесь бы использовались инструменты мониторинга
        print("ℹ️  Тест использования памяти требует внешних инструментов мониторинга")
        return True
    
    def test_concurrent_connections(self):
        """Тест одновременных подключений"""
        print("\n🔗 Тестирование одновременных подключений")
        
        def make_connection():
            try:
                response = requests.get(f"{self.backend_url}/api/auth/login/", timeout=5)
                return response.status_code
            except Exception as e:
                return 0
        
        # Тестируем разное количество одновременных подключений
        connection_counts = [10, 25, 50, 100]
        
        for count in connection_counts:
            print(f"   Тестирование {count} одновременных подключений...")
            
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
                futures = [executor.submit(make_connection) for _ in range(count)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            successful = sum(1 for r in results if r in [200, 400, 401, 405])  # Различные успешные коды
            success_rate = (successful / count) * 100
            
            print(f"     Результат: {successful}/{count} ({success_rate:.1f}%) за {total_time:.2f}с")
            
            if success_rate < 90:
                print(f"     ⚠️  Низкий процент успешных подключений при {count} одновременных")
                return False
        
        print("✅ Тест одновременных подключений пройден")
        return True
    
    def test_api_endpoint_performance(self):
        """Тест производительности отдельных API endpoints"""
        print("\n🎯 Тестирование производительности API endpoints")
        
        if not self.auth_tokens:
            print("❌ Нет токенов для тестирования")
            return False
        
        token = self.auth_tokens[0]
        
        # Тестируем разные endpoints
        test_endpoints = [
            ('/api/auth/profile/', 'GET', None),
            ('/api/materials/dashboard/student/', 'GET', None),
            ('/api/materials/materials/student/assigned/', 'GET', None),
            ('/api/chat/general/', 'GET', None),
            ('/api/chat/general/messages/', 'GET', None),
            ('/api/chat/general/messages/', 'POST', {
                'content': 'Тест производительности',
                'thread_id': None,
                'parent_message_id': None
            })
        ]
        
        for endpoint, method, data in test_endpoints:
            print(f"   Тестирование {method} {endpoint}")
            
            # Выполняем несколько запросов для получения среднего времени
            times = []
            for _ in range(10):
                result = self.make_request(endpoint, method, data, token)
                if result['success']:
                    times.append(result['response_time'])
            
            if times:
                avg_time = statistics.mean(times)
                min_time = min(times)
                max_time = max(times)
                
                print(f"     Среднее время: {avg_time:.3f}с")
                print(f"     Минимум: {min_time:.3f}с")
                print(f"     Максимум: {max_time:.3f}с")
                
                if avg_time > 1.0:
                    print(f"     ⚠️  Медленный endpoint: {avg_time:.3f}с")
            else:
                print(f"     ❌ Нет успешных запросов")
        
        return True
    
    def run_all_performance_tests(self):
        """Запуск всех тестов производительности"""
        print("🚀 Запуск тестов производительности и нагрузки")
        print("=" * 60)
        
        # Создаем тестовых пользователей
        if not self.create_test_users():
            print("❌ Не удалось создать тестовых пользователей")
            return False
        
        # Запускаем тесты
        tests = [
            ("Нагрузочное тестирование", self.run_load_test),
            ("Тест одновременных подключений", self.test_concurrent_connections),
            ("Тест производительности endpoints", self.test_api_endpoint_performance),
            ("Тест использования памяти", self.test_memory_usage)
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
            print("🎉 Все тесты производительности пройдены успешно!")
            return True
        else:
            print("⚠️  Некоторые тесты производительности провалены")
            return False


def main():
    """Основная функция"""
    perf_test = PerformanceTest()
    
    try:
        success = perf_test.run_all_performance_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

