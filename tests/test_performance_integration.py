#!/usr/bin/env python3
"""
Тесты производительности и нагрузки для интеграции
"""
import pytest
import time
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction
from unittest.mock import patch, MagicMock
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from backend.applications.models import Application
from backend.accounts.models import StudentProfile, ParentProfile, TeacherProfile
from backend.materials.models import Material, MaterialProgress
from backend.chat.models import ChatRoom, Message, MessageThread
from backend.reports.models import StudentReport
from backend.payments.models import Payment, SubjectEnrollment, SubjectPayment

User = get_user_model()


class PerformanceIntegrationTestCase(TransactionTestCase):
    """
    Тесты производительности для интеграции
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаем пользователей
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            role=User.Role.ADMIN
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Мария',
            last_name='Иванова'
        )
        
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            subject='Математика'
        )
        
        # Создаем общий чат
        self.general_chat = ChatRoom.objects.create(
            name='Общий чат',
            room_type=ChatRoom.RoomType.GENERAL
        )
        self.general_chat.participants.add(self.teacher_user)
    
    def test_dashboard_response_time(self):
        """Тест времени отклика дашбордов"""
        # Создаем много студентов и материалов для нагрузки
        students = []
        for i in range(50):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT,
                first_name=f'Студент{i}',
                last_name='Тестов'
            )
            StudentProfile.objects.create(user=student, grade='10')
            students.append(student)
            self.general_chat.participants.add(student)
        
        # Создаем много материалов
        materials = []
        for i in range(20):
            material = Material.objects.create(
                title=f'Материал {i}',
                content=f'Содержание материала {i}',
                material_type=Material.MaterialType.ASSIGNMENT,
                created_by=self.teacher_user
            )
            materials.append(material)
        
        # Тестируем время отклика дашборда преподавателя
        self.client.force_login(self.teacher_user)
        
        start_time = time.time()
        response = self.client.get('/api/dashboard/teacher/')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        response_time = end_time - start_time
        
        # Проверяем, что время отклика приемлемое (менее 2 секунд)
        self.assertLess(response_time, 2.0)
        print(f"Время отклика дашборда преподавателя: {response_time:.3f} секунд")
    
    def test_chat_performance_with_many_messages(self):
        """Тест производительности чата с большим количеством сообщений"""
        # Создаем много сообщений
        messages = []
        for i in range(100):
            message = Message.objects.create(
                content=f'Сообщение {i}',
                sender=self.teacher_user,
                room=self.general_chat
            )
            messages.append(message)
        
        self.client.force_login(self.teacher_user)
        
        # Тестируем время получения сообщений с пагинацией
        start_time = time.time()
        response = self.client.get('/api/chat/general/messages/')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        response_time = end_time - start_time
        
        # Проверяем, что время отклика приемлемое
        self.assertLess(response_time, 1.0)
        print(f"Время отклика чата с 100 сообщениями: {response_time:.3f} секунд")
        
        # Проверяем пагинацию
        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        self.assertEqual(data['count'], 100)
    
    def test_concurrent_message_creation(self):
        """Тест создания сообщений в конкурентном режиме"""
        self.client.force_login(self.teacher_user)
        
        def create_message(message_id):
            """Функция для создания сообщения"""
            message_data = {
                'content': f'Конкурентное сообщение {message_id}',
                'room_id': self.general_chat.id
            }
            response = self.client.post(
                '/api/chat/general/message/',
                data=json.dumps(message_data),
                content_type='application/json'
            )
            return response.status_code == 201
        
        # Создаем сообщения в 10 потоках одновременно
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_message, i) for i in range(20)]
            results = [future.result() for future in futures]
        
        # Проверяем, что все сообщения созданы успешно
        self.assertTrue(all(results))
        
        # Проверяем, что все сообщения действительно созданы
        message_count = Message.objects.filter(
            room=self.general_chat,
            content__startswith='Конкурентное сообщение'
        ).count()
        self.assertEqual(message_count, 20)
    
    def test_database_query_optimization(self):
        """Тест оптимизации запросов к базе данных"""
        # Создаем много связанных данных
        students = []
        for i in range(30):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT,
                first_name=f'Студент{i}',
                last_name='Тестов'
            )
            StudentProfile.objects.create(user=student, grade='10')
            students.append(student)
        
        # Создаем материалы и прогресс
        materials = []
        for i in range(10):
            material = Material.objects.create(
                title=f'Материал {i}',
                content=f'Содержание {i}',
                material_type=Material.MaterialType.ASSIGNMENT,
                created_by=self.teacher_user
            )
            materials.append(material)
            
            # Создаем прогресс для каждого студента
            for student in students:
                MaterialProgress.objects.create(
                    student=student,
                    material=material,
                    status=MaterialProgress.Status.IN_PROGRESS,
                    progress_percentage=50
                )
        
        self.client.force_login(self.teacher_user)
        
        # Тестируем время выполнения запроса с оптимизацией
        start_time = time.time()
        response = self.client.get('/api/dashboard/teacher/')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        response_time = end_time - start_time
        
        # Проверяем, что запрос выполняется быстро даже с большим количеством данных
        self.assertLess(response_time, 3.0)
        print(f"Время отклика с 30 студентами и 10 материалами: {response_time:.3f} секунд")
    
    def test_telegram_integration_performance(self):
        """Тест производительности интеграции с Telegram"""
        # Создаем много заявок
        applications = []
        for i in range(20):
            application = Application.objects.create(
                first_name=f'Пользователь{i}',
                last_name='Тестов',
                email=f'user{i}@test.com',
                phone=f'+7900123456{i:02d}',
                telegram_id=f'12345678{i:02d}',
                applicant_type=Application.ApplicantType.STUDENT,
                grade='10',
                motivation=f'Мотивация {i}'
            )
            applications.append(application)
        
        self.client.force_login(self.admin_user)
        
        # Мокаем Telegram сервис для быстрого ответа
        with patch('backend.applications.application_service.telegram_notification_service') as mock_telegram:
            mock_telegram.send_credentials.return_value = {'ok': True}
            
            # Одобряем все заявки и измеряем время
            start_time = time.time()
            
            for application in applications:
                response = self.client.post(
                    f'/api/applications/{application.id}/approve/',
                    data=json.dumps({'notes': 'Одобрено'}),
                    content_type='application/json'
                )
                self.assertEqual(response.status_code, 200)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Проверяем, что обработка всех заявок выполняется за разумное время
            self.assertLess(total_time, 10.0)
            print(f"Время обработки 20 заявок: {total_time:.3f} секунд")
    
    def test_memory_usage_with_large_datasets(self):
        """Тест использования памяти с большими наборами данных"""
        # Создаем большое количество данных
        students = []
        for i in range(100):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT,
                first_name=f'Студент{i}',
                last_name='Тестов'
            )
            StudentProfile.objects.create(user=student, grade='10')
            students.append(student)
        
        # Создаем много сообщений
        for i in range(500):
            Message.objects.create(
                content=f'Сообщение {i}',
                sender=self.teacher_user,
                room=self.general_chat
            )
        
        self.client.force_login(self.teacher_user)
        
        # Тестируем получение данных
        start_time = time.time()
        response = self.client.get('/api/chat/general/messages/')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        response_time = end_time - start_time
        
        # Проверяем, что время отклика остается приемлемым
        self.assertLess(response_time, 2.0)
        print(f"Время отклика с 500 сообщениями: {response_time:.3f} секунд")
    
    def test_concurrent_dashboard_access(self):
        """Тест одновременного доступа к дашбордам"""
        # Создаем пользователей разных ролей
        students = []
        for i in range(5):
            student = User.objects.create_user(
                username=f'student{i}',
                email=f'student{i}@test.com',
                password='testpass123',
                role=User.Role.STUDENT,
                first_name=f'Студент{i}',
                last_name='Тестов'
            )
            StudentProfile.objects.create(user=student, grade='10')
            students.append(student)
        
        def access_dashboard(user, dashboard_type):
            """Функция для доступа к дашборду"""
            client = Client()
            client.force_login(user)
            
            if dashboard_type == 'student':
                response = client.get('/api/dashboard/student/')
            elif dashboard_type == 'teacher':
                response = client.get('/api/dashboard/teacher/')
            
            return response.status_code == 200
        
        # Тестируем одновременный доступ
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Студенты получают доступ к своим дашбордам
            for student in students:
                futures.append(executor.submit(access_dashboard, student, 'student'))
            
            # Преподаватель получает доступ к своему дашборду
            futures.append(executor.submit(access_dashboard, self.teacher_user, 'teacher'))
            
            results = [future.result() for future in futures]
        
        # Проверяем, что все запросы выполнились успешно
        self.assertTrue(all(results))
        print("Все одновременные запросы к дашбордам выполнены успешно")


class LoadTestingTestCase(TransactionTestCase):
    """
    Тесты нагрузки для проверки стабильности системы
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Мария',
            last_name='Иванова'
        )
        
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            subject='Математика'
        )
        
        self.general_chat = ChatRoom.objects.create(
            name='Общий чат',
            room_type=ChatRoom.RoomType.GENERAL
        )
        self.general_chat.participants.add(self.teacher_user)
    
    def test_high_frequency_message_creation(self):
        """Тест создания сообщений с высокой частотой"""
        self.client.force_login(self.teacher_user)
        
        # Создаем сообщения с высокой частотой
        start_time = time.time()
        success_count = 0
        
        for i in range(50):
            message_data = {
                'content': f'Быстрое сообщение {i}',
                'room_id': self.general_chat.id
            }
            
            response = self.client.post(
                '/api/chat/general/message/',
                data=json.dumps(message_data),
                content_type='application/json'
            )
            
            if response.status_code == 201:
                success_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Проверяем, что большинство сообщений созданы успешно
        self.assertGreater(success_count, 45)  # 90% успешных запросов
        print(f"Создано {success_count}/50 сообщений за {total_time:.3f} секунд")
    
    def test_sustained_load(self):
        """Тест устойчивости к постоянной нагрузке"""
        self.client.force_login(self.teacher_user)
        
        # Выполняем запросы в течение определенного времени
        start_time = time.time()
        request_count = 0
        success_count = 0
        
        while time.time() - start_time < 5:  # 5 секунд нагрузки
            response = self.client.get('/api/dashboard/teacher/')
            request_count += 1
            
            if response.status_code == 200:
                success_count += 1
        
        # Проверяем, что система выдерживает нагрузку
        success_rate = success_count / request_count if request_count > 0 else 0
        self.assertGreater(success_rate, 0.95)  # 95% успешных запросов
        
        print(f"Выполнено {request_count} запросов, успешно: {success_count} ({success_rate:.2%})")


if __name__ == '__main__':
    pytest.main([__file__])
