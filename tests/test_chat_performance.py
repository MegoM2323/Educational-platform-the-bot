import time
import threading
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.cache import cache
from chat.models import ChatRoom, Message, MessageThread, ChatParticipant
from chat.general_chat_service import GeneralChatService
from materials.cache_utils import ChatCacheManager

User = get_user_model()


class ChatPerformanceTestCase(TransactionTestCase):
    """
    Тесты производительности для general chat forum
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем тестовых пользователей
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='One',
            role=User.Role.TEACHER
        )
        
        self.students = []
        for i in range(50):  # 50 студентов для нагрузочного тестирования
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                first_name=f'Student',
                last_name=f'{i}',
                role=User.Role.STUDENT
            )
            self.students.append(student)
        
        # Создаем общий чат
        self.general_chat = GeneralChatService.get_or_create_general_chat()
        
        # Очищаем кэш перед тестами
        cache.clear()
    
    def tearDown(self):
        """Очистка после тестов"""
        cache.clear()
    
    def test_chat_creation_performance(self):
        """Тест производительности создания чата"""
        start_time = time.time()
        
        # Создаем новый чат
        chat = GeneralChatService.get_or_create_general_chat()
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Проверяем, что создание чата занимает менее 1 секунды
        self.assertLess(creation_time, 1.0, 
                       f"Создание чата заняло {creation_time:.3f} секунд, что больше 1 секунды")
        
        print(f"Время создания чата: {creation_time:.3f} секунд")
    
    def test_message_sending_performance(self):
        """Тест производительности отправки сообщений"""
        # Отправляем 100 сообщений и измеряем время
        start_time = time.time()
        
        for i in range(100):
            GeneralChatService.send_general_message(
                sender=self.teacher,
                content=f'Тестовое сообщение {i}',
                message_type=Message.Type.TEXT
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_message = total_time / 100
        
        # Проверяем, что среднее время отправки сообщения менее 0.1 секунды
        self.assertLess(avg_time_per_message, 0.1, 
                       f"Среднее время отправки сообщения: {avg_time_per_message:.3f} секунд")
        
        print(f"Общее время отправки 100 сообщений: {total_time:.3f} секунд")
        print(f"Среднее время на сообщение: {avg_time_per_message:.3f} секунд")
    
    def test_thread_creation_performance(self):
        """Тест производительности создания тредов"""
        start_time = time.time()
        
        # Создаем 20 тредов
        threads = []
        for i in range(20):
            thread = GeneralChatService.create_thread(
                room=self.general_chat,
                title=f'Тестовый тред {i}',
                created_by=self.teacher
            )
            threads.append(thread)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_thread = total_time / 20
        
        # Проверяем, что среднее время создания треда менее 0.05 секунды
        self.assertLess(avg_time_per_thread, 0.05, 
                       f"Среднее время создания треда: {avg_time_per_thread:.3f} секунд")
        
        print(f"Общее время создания 20 тредов: {total_time:.3f} секунд")
        print(f"Среднее время на тред: {avg_time_per_thread:.3f} секунд")
    
    def test_concurrent_message_sending(self):
        """Тест производительности при одновременной отправке сообщений"""
        results = []
        errors = []
        
        def send_messages(student, message_count):
            """Функция для отправки сообщений в отдельном потоке"""
            try:
                start_time = time.time()
                
                for i in range(message_count):
                    GeneralChatService.send_general_message(
                        sender=student,
                        content=f'Сообщение от {student.username} #{i}',
                        message_type=Message.Type.TEXT
                    )
                
                end_time = time.time()
                results.append({
                    'student': student.username,
                    'time': end_time - start_time,
                    'message_count': message_count
                })
            except Exception as e:
                errors.append(f"Ошибка у {student.username}: {str(e)}")
        
        # Запускаем 10 потоков, каждый отправляет 10 сообщений
        threads = []
        for i in range(10):
            student = self.students[i]
            thread = threading.Thread(
                target=send_messages,
                args=(student, 10)
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
        self.assertEqual(len(errors), 0, f"Ошибки при отправке сообщений: {errors}")
        
        # Проверяем, что все сообщения были отправлены
        total_messages = sum(result['message_count'] for result in results)
        self.assertEqual(total_messages, 100, "Не все сообщения были отправлены")
        
        # Проверяем, что общее время выполнения разумное
        self.assertLess(total_time, 10.0, 
                       f"Общее время выполнения: {total_time:.3f} секунд")
        
        print(f"Общее время выполнения (10 потоков, 100 сообщений): {total_time:.3f} секунд")
        print(f"Среднее время на поток: {total_time / 10:.3f} секунд")
    
    def test_message_retrieval_performance(self):
        """Тест производительности получения сообщений"""
        # Сначала создаем много сообщений
        for i in range(200):
            GeneralChatService.send_general_message(
                sender=self.teacher,
                content=f'Сообщение для теста производительности {i}',
                message_type=Message.Type.TEXT
            )
        
        # Тестируем получение сообщений с пагинацией
        start_time = time.time()
        
        for page in range(10):  # 10 страниц по 20 сообщений
            messages = GeneralChatService.get_general_chat_messages(
                limit=20, 
                offset=page * 20
            )
            self.assertEqual(len(messages), 20)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_page = total_time / 10
        
        # Проверяем, что среднее время получения страницы менее 0.1 секунды
        self.assertLess(avg_time_per_page, 0.1, 
                       f"Среднее время получения страницы: {avg_time_per_page:.3f} секунд")
        
        print(f"Общее время получения 10 страниц: {total_time:.3f} секунд")
        print(f"Среднее время на страницу: {avg_time_per_page:.3f} секунд")
    
    def test_cache_performance(self):
        """Тест производительности кэширования"""
        cache_manager = ChatCacheManager()
        
        # Очищаем кэш
        cache_manager.clear()
        
        # Первый запрос (без кэша)
        start_time = time.time()
        messages1 = GeneralChatService.get_general_chat_messages(limit=20, offset=0)
        first_request_time = time.time() - start_time
        
        # Второй запрос (с кэшем)
        start_time = time.time()
        messages2 = GeneralChatService.get_general_chat_messages(limit=20, offset=0)
        second_request_time = time.time() - start_time
        
        # Проверяем, что кэшированный запрос быстрее
        self.assertLess(second_request_time, first_request_time,
                       f"Кэшированный запрос ({second_request_time:.3f}s) не быстрее обычного ({first_request_time:.3f}s)")
        
        # Проверяем, что результаты одинаковые
        self.assertEqual(len(messages1), len(messages2))
        
        print(f"Время первого запроса (без кэша): {first_request_time:.3f} секунд")
        print(f"Время второго запроса (с кэшем): {second_request_time:.3f} секунд")
        print(f"Ускорение: {first_request_time / second_request_time:.2f}x")
    
    def test_database_query_optimization(self):
        """Тест оптимизации запросов к базе данных"""
        # Создаем много сообщений и тредов
        for i in range(100):
            GeneralChatService.send_general_message(
                sender=self.teacher,
                content=f'Сообщение {i}',
                message_type=Message.Type.TEXT
            )
        
        for i in range(20):
            GeneralChatService.create_thread(
                room=self.general_chat,
                title=f'Тред {i}',
                created_by=self.teacher
            )
        
        # Тестируем количество запросов к БД
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            # Очищаем счетчик запросов
            connection.queries_log.clear()
            
            # Выполняем операции
            messages = GeneralChatService.get_general_chat_messages(limit=50, offset=0)
            threads = GeneralChatService.get_general_chat_threads(limit=10, offset=0)
            
            # Проверяем количество запросов
            query_count = len(connection.queries)
            
            # Должно быть не более 5 запросов для получения сообщений и тредов
            self.assertLessEqual(query_count, 5, 
                               f"Слишком много запросов к БД: {query_count}")
            
            print(f"Количество запросов к БД: {query_count}")
            print(f"Получено сообщений: {len(messages)}")
            print(f"Получено тредов: {len(threads)}")
    
    def test_memory_usage(self):
        """Тест использования памяти"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Создаем много данных
        for i in range(500):
            GeneralChatService.send_general_message(
                sender=self.teacher,
                content=f'Сообщение для теста памяти {i}' * 10,  # Длинные сообщения
                message_type=Message.Type.TEXT
            )
        
        # Получаем данные
        messages = GeneralChatService.get_general_chat_messages(limit=500, offset=0)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Проверяем, что увеличение памяти разумное (менее 50 MB)
        self.assertLess(memory_increase, 50, 
                       f"Увеличение памяти: {memory_increase:.2f} MB")
        
        print(f"Начальное использование памяти: {initial_memory:.2f} MB")
        print(f"Конечное использование памяти: {final_memory:.2f} MB")
        print(f"Увеличение памяти: {memory_increase:.2f} MB")
        print(f"Получено сообщений: {len(messages)}")
