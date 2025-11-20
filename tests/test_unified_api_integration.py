#!/usr/bin/env python3
"""
Интеграционные тесты для унифицированного API клиента
Проверяет полную интеграцию между frontend и backend через unified API
"""
import pytest
import requests
import json
import sys
import os
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
import time

# Добавляем путь к backend для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.applications.models import Application
from backend.accounts.models import StudentProfile, ParentProfile, TeacherProfile
from backend.materials.models import Material, MaterialProgress
from backend.chat.models import ChatRoom, Message, MessageThread
from backend.reports.models import StudentReport
from backend.payments.models import Payment, SubjectEnrollment, SubjectPayment

User = get_user_model()

# Конфигурация
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"


class UnifiedAPIIntegrationTestCase(TestCase):
    """
    Интеграционные тесты для унифицированного API клиента
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
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Иван',
            last_name='Петров'
        )
        
        self.parent_user = User.objects.create_user(
            username='parent',
            email='parent@test.com',
            password='testpass123',
            role=User.Role.PARENT,
            first_name='Петр',
            last_name='Петров'
        )
        
        self.teacher_user = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER,
            first_name='Мария',
            last_name='Иванова'
        )
        
        # Создаем профили
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            grade='10'
        )
        
        self.parent_profile = ParentProfile.objects.create(
            user=self.parent_user
        )
        
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            subject='Математика'
        )
        
        # Связываем родителя и ребенка
        self.parent_profile.children.add(self.student_user)
        
        # Создаем материалы
        self.material = Material.objects.create(
            title='Тест по математике',
            content='Содержание теста',
            material_type=Material.MaterialType.ASSIGNMENT,
            created_by=self.teacher_user
        )
        
        # Создаем общий чат
        self.general_chat = ChatRoom.objects.create(
            name='Общий чат',
            room_type=ChatRoom.RoomType.GENERAL
        )
        self.general_chat.participants.add(self.student_user, self.teacher_user)
    
    def test_unified_api_authentication_flow(self):
        """Тест полного цикла аутентификации через unified API"""
        # 1. Вход пользователя
        login_data = {
            'email': 'student@test.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], 'student@test.com')
        
        # 2. Использование токена для доступа к защищенному ресурсу
        token = data['token']
        response = self.client.get(
            '/api/auth/profile/',
            HTTP_AUTHORIZATION=f'Token {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        profile_data = response.json()
        self.assertEqual(profile_data['email'], 'student@test.com')
        
        # 3. Выход
        response = self.client.post(
            '/api/auth/logout/',
            HTTP_AUTHORIZATION=f'Token {token}'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_unified_api_dashboard_integration(self):
        """Тест интеграции дашбордов через unified API"""
        # Тест дашборда студента
        self.client.force_login(self.student_user)
        
        response = self.client.get('/api/materials/dashboard/student/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('materials_count', data)
        self.assertIn('completed_materials', data)
        self.assertIn('progress_percentage', data)
        
        # Тест дашборда преподавателя
        self.client.force_login(self.teacher_user)
        
        response = self.client.get('/api/materials/dashboard/teacher/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('total_students', data)
        self.assertIn('total_materials', data)
        self.assertIn('pending_reports', data)
        
        # Тест дашборда родителя
        self.client.force_login(self.parent_user)
        
        response = self.client.get('/api/materials/dashboard/parent/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('total_children', data)
        self.assertIn('total_subjects', data)
        self.assertIn('pending_payments', data)
    
    def test_unified_api_chat_integration(self):
        """Тест интеграции чата через unified API"""
        self.client.force_login(self.student_user)
        
        # 1. Получение общего чата
        response = self.client.get('/api/chat/general/')
        self.assertEqual(response.status_code, 200)
        
        # 2. Получение сообщений
        response = self.client.get('/api/chat/general/messages/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('results', data)
        self.assertIn('count', data)
        
        # 3. Отправка сообщения
        message_data = {
            'content': 'Тестовое сообщение через unified API',
            'thread_id': None,
            'parent_message_id': None
        }
        response = self.client.post(
            '/api/chat/general/messages/',
            data=json.dumps(message_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        message = response.json()
        self.assertEqual(message['content'], 'Тестовое сообщение через unified API')
        self.assertEqual(message['sender_id'], self.student_user.id)
    
    def test_unified_api_payment_integration(self):
        """Тест интеграции платежей через unified API"""
        # Создаем зачисление на предмет
        subject_enrollment = SubjectEnrollment.objects.create(
            student=self.student_user,
            teacher=self.teacher_user,
            subject='Математика',
            status=SubjectEnrollment.Status.ACTIVE
        )
        
        self.client.force_login(self.parent_user)
        
        # 1. Создание платежа
        payment_data = {
            'amount': '1000.00',
            'service_name': 'Обучение по математике',
            'customer_fio': 'Петр Петров',
            'description': 'Оплата за месяц обучения',
            'metadata': {
                'subject_enrollment_id': subject_enrollment.id,
                'student_id': self.student_user.id
            }
        }
        
        response = self.client.post(
            '/api/payments/',
            data=json.dumps(payment_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        payment = response.json()
        self.assertEqual(payment['amount'], '1000.00')
        self.assertEqual(payment['service_name'], 'Обучение по математике')
        
        # 2. Получение платежа
        response = self.client.get(f'/api/payments/{payment["id"]}/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Получение статуса платежа
        response = self.client.get(f'/api/payments/{payment["id"]}/status/')
        self.assertEqual(response.status_code, 200)
    
    def test_unified_api_application_integration(self):
        """Тест интеграции заявок через unified API"""
        # 1. Создание заявки
        application_data = {
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'email': 'test@example.com',
            'phone': '+79001234567',
            'telegram_id': '123456789',
            'applicant_type': 'student',
            'grade': '10',
            'motivation': 'Хочу учиться через unified API'
        }
        
        response = self.client.post(
            '/api/applications/create/',
            data=json.dumps(application_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        application = response.json()
        self.assertEqual(application['email'], 'test@example.com')
        self.assertEqual(application['applicant_type'], 'student')
        
        # 2. Получение заявок (только для админа)
        self.client.force_login(self.admin_user)
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, 200)
        
        applications = response.json()
        self.assertGreater(len(applications), 0)
        
        # 3. Обновление статуса заявки
        response = self.client.patch(
            f'/api/applications/{application["id"]}/status/',
            data=json.dumps({
                'status': 'approved',
                'notes': 'Одобрено через unified API'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_unified_api_error_handling(self):
        """Тест обработки ошибок в unified API"""
        # 1. Неверные данные при входе
        invalid_login_data = {
            'email': 'nonexistent@test.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(
            '/api/auth/login/',
            data=json.dumps(invalid_login_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # 2. Несуществующий endpoint
        response = self.client.get('/api/nonexistent/')
        self.assertEqual(response.status_code, 404)
        
        # 3. Неверный метод для endpoint
        response = self.client.delete('/api/materials/dashboard/student/')
        self.assertEqual(response.status_code, 405)
        
        # 4. Доступ без аутентификации
        response = self.client.get('/api/materials/dashboard/student/')
        self.assertEqual(response.status_code, 401)
    
    def test_unified_api_permission_restrictions(self):
        """Тест ограничений доступа в unified API"""
        # 1. Студент не может получить данные родителя
        self.client.force_login(self.student_user)
        response = self.client.get('/api/materials/dashboard/parent/')
        self.assertEqual(response.status_code, 403)
        
        # 2. Родитель не может получить данные преподавателя
        self.client.force_login(self.parent_user)
        response = self.client.get('/api/materials/dashboard/teacher/')
        self.assertEqual(response.status_code, 403)
        
        # 3. Преподаватель не может получить данные родителя
        self.client.force_login(self.teacher_user)
        response = self.client.get('/api/materials/dashboard/parent/')
        self.assertEqual(response.status_code, 403)
    
    def test_unified_api_response_format(self):
        """Тест формата ответов unified API"""
        self.client.force_login(self.student_user)
        
        response = self.client.get('/api/materials/dashboard/student/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Проверяем структуру ответа
        self.assertIsInstance(data, dict)
        self.assertIn('materials_count', data)
        self.assertIn('completed_materials', data)
        self.assertIn('progress_percentage', data)
        self.assertIn('recent_materials', data)
        self.assertIn('upcoming_deadlines', data)
        
        # Проверяем типы данных
        self.assertIsInstance(data['materials_count'], int)
        self.assertIsInstance(data['completed_materials'], int)
        self.assertIsInstance(data['progress_percentage'], (int, float))
        self.assertIsInstance(data['recent_materials'], list)
        self.assertIsInstance(data['upcoming_deadlines'], list)


def test_frontend_backend_communication():
    """Тест реального взаимодействия frontend и backend"""
    try:
        # Проверяем доступность backend
        response = requests.get(f"{BACKEND_URL}/admin/", timeout=5)
        if response.status_code != 200:
            print("❌ Backend недоступен")
            return False
        
        print("✅ Backend доступен")
        
        # Тестируем API endpoints
        endpoints = [
            "/api/auth/login/",
            "/api/materials/dashboard/student/",
            "/api/chat/general/",
            "/api/payments/",
            "/api/applications/"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
                if response.status_code in [200, 401, 403, 405]:  # 401/403/405 - нормальные ответы для неаутентифицированных запросов
                    print(f"✅ Endpoint {endpoint} доступен")
                else:
                    print(f"⚠️  Endpoint {endpoint} вернул статус {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Endpoint {endpoint} недоступен: {e}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к backend: {e}")
        return False


def test_unified_api_performance():
    """Тест производительности unified API"""
    try:
        # Создаем тестового пользователя
        login_data = {
            'email': 'student@test.com',
            'password': 'testpass123'
        }
        
        # Тестируем время ответа
        start_time = time.time()
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login/",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        if response.status_code == 200 and response_time < 2.0:  # Менее 2 секунд
            print(f"✅ API отвечает быстро: {response_time:.2f}с")
            return True
        else:
            print(f"⚠️  API медленный: {response_time:.2f}с")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка тестирования производительности: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование унифицированного API")
    print("=" * 50)
    
    # Тестируем доступность backend
    if not test_frontend_backend_communication():
        print("❌ Backend недоступен. Убедитесь, что Django сервер запущен.")
        sys.exit(1)
    
    print("\n⚡ Тестирование производительности:")
    test_unified_api_performance()
    
    print("\n✅ Тестирование завершено!")


if __name__ == "__main__":
    main()

