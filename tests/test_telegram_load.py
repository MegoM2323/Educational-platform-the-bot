import time
import threading
import requests
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from applications.telegram_service import TelegramNotificationService
from applications.models import Application

User = get_user_model()


class TelegramLoadTestCase(TransactionTestCase):
    """
    Тесты нагрузки для Telegram интеграции
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.teacher = User.objects.create_user(
            username='teacher_load',
            email='teacher_load@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='Load',
            role=User.Role.TEACHER
        )
        
        # Создаем тестовые заявки
        self.applications = []
        for i in range(100):
            application = Application.objects.create(
                first_name=f'Student{i}',
                last_name=f'Test{i}',
                email=f'student{i}@test.com',
                phone=f'+7900123456{i:02d}',
                role=Application.Role.STUDENT,
                status=Application.Status.PENDING,
                additional_info=f'Test application {i}'
            )
            self.applications.append(application)
    
    def tearDown(self):
        """Очистка после тестов"""
        pass
    
    @patch('applications.telegram_service.requests.post')
    def test_telegram_notification_performance(self, mock_post):
        """Тест производительности отправки уведомлений Telegram"""
        # Настраиваем мок для успешных ответов
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        mock_post.return_value = mock_response
        
        telegram_service = TelegramNotificationService()
        
        start_time = time.time()
        
        # Отправляем 50 уведомлений
        for i in range(50):
            telegram_service.send_application_approved_notification(
                application=self.applications[i],
                credentials={'username': f'student{i}', 'password': 'temp123'}
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_notification = total_time / 50
        
        # Проверяем, что среднее время отправки уведомления менее 0.5 секунды
        self.assertLess(avg_time_per_notification, 0.5, 
                       f"Среднее время отправки уведомления: {avg_time_per_notification:.3f} секунд")
        
        # Проверяем, что все запросы были отправлены
        self.assertEqual(mock_post.call_count, 50)
        
        print(f"Общее время отправки 50 уведомлений: {total_time:.3f} секунд")
        print(f"Среднее время на уведомление: {avg_time_per_notification:.3f} секунд")
        print(f"Количество HTTP запросов: {mock_post.call_count}")
    
    @patch('applications.telegram_service.requests.post')
    def test_concurrent_telegram_notifications(self, mock_post):
        """Тест одновременной отправки уведомлений"""
        # Настраиваем мок с задержкой для имитации реального API
        def mock_post_with_delay(*args, **kwargs):
            time.sleep(0.1)  # Имитируем задержку сети
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
            return mock_response
        
        mock_post.side_effect = mock_post_with_delay
        
        telegram_service = TelegramNotificationService()
        results = []
        errors = []
        
        def send_notification(application, index):
            """Функция для отправки уведомления в отдельном потоке"""
            try:
                start_time = time.time()
                
                telegram_service.send_application_approved_notification(
                    application=application,
                    credentials={'username': f'student{index}', 'password': 'temp123'}
                )
                
                end_time = time.time()
                results.append({
                    'index': index,
                    'time': end_time - start_time
                })
            except Exception as e:
                errors.append(f"Ошибка у заявки {index}: {str(e)}")
        
        # Запускаем 20 потоков, каждый отправляет 1 уведомление
        threads = []
        for i in range(20):
            thread = threading.Thread(
                target=send_notification,
                args=(self.applications[i], i)
            )
            threads.append(thread)
        
        start_time = time.time()
        
        # Запускаем все потоки
        for thread in threads:
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем, что нет ошибок
        self.assertEqual(len(errors), 0, f"Ошибки при отправке уведомлений: {errors}")
        
        # Проверяем, что все уведомления были отправлены
        self.assertEqual(len(results), 20, "Не все уведомления были отправлены")
        
        # Проверяем, что общее время выполнения разумное
        self.assertLess(total_time, 5.0, 
                       f"Общее время выполнения: {total_time:.3f} секунд")
        
        print(f"Общее время выполнения (20 потоков): {total_time:.3f} секунд")
        print(f"Среднее время на поток: {total_time / 20:.3f} секунд")
        print(f"Количество HTTP запросов: {mock_post.call_count}")
    
    @patch('applications.telegram_service.requests.post')
    def test_telegram_error_handling(self, mock_post):
        """Тест обработки ошибок Telegram API"""
        # Настраиваем мок для ошибок
        mock_response = MagicMock()
        mock_response.status_code = 429  # Rate limit
        mock_response.json.return_value = {'ok': False, 'error_code': 429, 'description': 'Too Many Requests'}
        mock_post.return_value = mock_response
        
        telegram_service = TelegramNotificationService()
        
        start_time = time.time()
        
        # Пытаемся отправить уведомления
        success_count = 0
        error_count = 0
        
        for i in range(10):
            try:
                telegram_service.send_application_approved_notification(
                    application=self.applications[i],
                    credentials={'username': f'student{i}', 'password': 'temp123'}
                )
                success_count += 1
            except Exception:
                error_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем, что ошибки обрабатываются корректно
        self.assertEqual(success_count, 0, "Неожиданно успешные отправки")
        self.assertEqual(error_count, 10, "Не все ошибки были обработаны")
        
        print(f"Время обработки ошибок: {total_time:.3f} секунд")
        print(f"Успешных отправок: {success_count}")
        print(f"Ошибок: {error_count}")
    
    @patch('applications.telegram_service.requests.post')
    def test_telegram_rate_limiting(self, mock_post):
        """Тест ограничения скорости отправки"""
        call_times = []
        
        def mock_post_with_timing(*args, **kwargs):
            call_times.append(time.time())
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
            return mock_response
        
        mock_post.side_effect = mock_post_with_timing
        
        telegram_service = TelegramNotificationService()
        
        # Отправляем уведомления с высокой частотой
        start_time = time.time()
        
        for i in range(20):
            telegram_service.send_application_approved_notification(
                application=self.applications[i],
                credentials={'username': f'student{i}', 'password': 'temp123'}
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем, что все запросы были отправлены
        self.assertEqual(len(call_times), 20)
        
        # Проверяем, что время между запросами разумное
        if len(call_times) > 1:
            intervals = [call_times[i] - call_times[i-1] for i in range(1, len(call_times))]
            avg_interval = sum(intervals) / len(intervals)
            
            # Интервал между запросами должен быть не менее 0.01 секунды
            self.assertGreaterEqual(avg_interval, 0.01, 
                                  f"Слишком быстрая отправка: {avg_interval:.3f} секунд между запросами")
        
        print(f"Общее время отправки 20 уведомлений: {total_time:.3f} секунд")
        print(f"Средний интервал между запросами: {avg_interval:.3f} секунд")
    
    def test_telegram_message_processing(self):
        """Тест обработки сообщений Telegram"""
        # Тестируем обработку различных типов сообщений
        test_messages = [
            {'text': 'Простое сообщение'},
            {'text': 'Сообщение с эмодзи 😊'},
            {'text': 'Сообщение с переносами строк\nВторая строка'},
            {'text': 'Сообщение с HTML <b>жирный</b> текст'},
            {'text': 'Очень длинное сообщение ' * 100},
        ]
        
        start_time = time.time()
        
        for i, message in enumerate(test_messages):
            # Имитируем обработку сообщения
            processed_message = self._process_telegram_message(message)
            self.assertIsNotNone(processed_message)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_message = total_time / len(test_messages)
        
        # Проверяем, что обработка сообщений быстрая
        self.assertLess(avg_time_per_message, 0.01, 
                       f"Среднее время обработки сообщения: {avg_time_per_message:.3f} секунд")
        
        print(f"Общее время обработки {len(test_messages)} сообщений: {total_time:.3f} секунд")
        print(f"Среднее время на сообщение: {avg_time_per_message:.3f} секунд")
    
    def _process_telegram_message(self, message):
        """Имитация обработки сообщения Telegram"""
        # Простая обработка текста
        text = message.get('text', '')
        
        # Очистка HTML тегов
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Ограничение длины
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + '...'
        
        return {
            'original': text,
            'processed': clean_text,
            'length': len(clean_text)
        }
    
    def test_telegram_memory_usage(self):
        """Тест использования памяти при работе с Telegram"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Создаем много уведомлений
        notifications = []
        for i in range(1000):
            notification = {
                'application_id': i,
                'message': f'Уведомление {i}' * 10,  # Длинные сообщения
                'timestamp': time.time()
            }
            notifications.append(notification)
        
        # Обрабатываем уведомления
        processed_notifications = []
        for notification in notifications:
            processed = self._process_telegram_message({'text': notification['message']})
            processed_notifications.append(processed)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Проверяем, что увеличение памяти разумное (менее 20 MB)
        self.assertLess(memory_increase, 20, 
                       f"Увеличение памяти: {memory_increase:.2f} MB")
        
        print(f"Начальное использование памяти: {initial_memory:.2f} MB")
        print(f"Конечное использование памяти: {final_memory:.2f} MB")
        print(f"Увеличение памяти: {memory_increase:.2f} MB")
        print(f"Обработано уведомлений: {len(processed_notifications)}")
