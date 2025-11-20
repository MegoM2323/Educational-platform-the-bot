#!/usr/bin/env python3
"""
Интеграционные тесты для API endpoints
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json

from backend.applications.models import Application
from backend.accounts.models import StudentProfile, ParentProfile, TeacherProfile
from backend.materials.models import Material, MaterialProgress
from backend.chat.models import ChatRoom, Message, MessageThread
from backend.reports.models import StudentReport
from backend.payments.models import Payment, SubjectEnrollment, SubjectPayment

User = get_user_model()


class APIEndpointsIntegrationTestCase(TestCase):
    """
    Интеграционные тесты для всех API endpoints
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
    
    def test_application_api_endpoints(self):
        """Тест API endpoints для заявок"""
        # 1. Подача заявки
        application_data = {
            'first_name': 'Тест',
            'last_name': 'Пользователь',
            'email': 'test@example.com',
            'phone': '+79001234567',
            'telegram_id': '123456789',
            'applicant_type': Application.ApplicantType.STUDENT,
            'grade': '10',
            'motivation': 'Хочу учиться'
        }
        
        response = self.client.post(
            '/api/applications/submit/',
            data=json.dumps(application_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        application = Application.objects.get(email='test@example.com')
        
        # 2. Получение списка заявок (только для админа)
        self.client.force_login(self.admin_user)
        response = self.client.get('/api/applications/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Получение конкретной заявки
        response = self.client.get(f'/api/applications/{application.id}/')
        self.assertEqual(response.status_code, 200)
        
        # 4. Одобрение заявки
        with patch('backend.applications.application_service.telegram_notification_service') as mock_telegram:
            mock_telegram.send_credentials.return_value = {'ok': True}
            
            response = self.client.post(
                f'/api/applications/{application.id}/approve/',
                data=json.dumps({'notes': 'Одобрено'}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
    
    def test_student_dashboard_api_endpoints(self):
        """Тест API endpoints для дашборда студента"""
        self.client.force_login(self.student_user)
        
        # 1. Получение данных дашборда
        response = self.client.get('/api/dashboard/student/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('materials', data)
        self.assertIn('progress', data)
        self.assertIn('user', data)
        
        # 2. Получение назначенных материалов
        response = self.client.get('/api/materials/student/assigned/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Получение прогресса по материалам
        response = self.client.get('/api/materials/student/progress/')
        self.assertEqual(response.status_code, 200)
    
    def test_parent_dashboard_api_endpoints(self):
        """Тест API endpoints для дашборда родителя"""
        self.client.force_login(self.parent_user)
        
        # 1. Получение данных дашборда
        response = self.client.get('/api/dashboard/parent/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('children', data)
        self.assertIn('payments', data)
        self.assertIn('reports', data)
        
        # 2. Получение информации о детях
        response = self.client.get('/api/dashboard/parent/children/')
        self.assertEqual(response.status_code, 200)
        
        children_data = response.json()
        self.assertEqual(len(children_data), 1)
        self.assertEqual(children_data[0]['first_name'], 'Иван')
        
        # 3. Получение отчетов
        response = self.client.get('/api/dashboard/parent/reports/')
        self.assertEqual(response.status_code, 200)
    
    def test_teacher_dashboard_api_endpoints(self):
        """Тест API endpoints для дашборда преподавателя"""
        self.client.force_login(self.teacher_user)
        
        # 1. Получение данных дашборда
        response = self.client.get('/api/dashboard/teacher/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('students', data)
        self.assertIn('materials', data)
        self.assertIn('reports', data)
        
        # 2. Получение студентов
        response = self.client.get('/api/dashboard/teacher/students/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Получение материалов
        response = self.client.get('/api/materials/teacher/')
        self.assertEqual(response.status_code, 200)
        
        # 4. Распределение материала
        distribution_data = {
            'material_id': self.material.id,
            'student_ids': [self.student_user.id]
        }
        response = self.client.post(
            '/api/materials/teacher/distribute/',
            data=json.dumps(distribution_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_chat_api_endpoints(self):
        """Тест API endpoints для чата"""
        # Вход студента
        self.client.force_login(self.student_user)
        
        # 1. Получение общего чата
        response = self.client.get('/api/chat/general/')
        self.assertEqual(response.status_code, 200)
        
        # 2. Получение сообщений
        response = self.client.get('/api/chat/general/messages/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Отправка сообщения
        message_data = {
            'content': 'Тестовое сообщение',
            'room_id': self.general_chat.id
        }
        response = self.client.post(
            '/api/chat/general/message/',
            data=json.dumps(message_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        message = Message.objects.get(content='Тестовое сообщение')
        
        # 4. Ответ в ветке
        reply_data = {
            'content': 'Ответ на сообщение',
            'parent_message_id': message.id
        }
        response = self.client.post(
            f'/api/chat/general/thread/{message.id}/',
            data=json.dumps(reply_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
    
    def test_reports_api_endpoints(self):
        """Тест API endpoints для отчетов"""
        self.client.force_login(self.teacher_user)
        
        # 1. Создание отчета
        report_data = {
            'student_id': self.student_user.id,
            'report_type': StudentReport.ReportType.PROGRESS,
            'title': 'Тестовый отчет',
            'content': 'Содержание отчета',
            'metrics': {
                'attendance': 95,
                'homework_completion': 90,
                'test_scores': 85
            }
        }
        
        response = self.client.post(
            '/api/reports/create/',
            data=json.dumps(report_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # 2. Получение отчетов преподавателя
        response = self.client.get('/api/reports/teacher/')
        self.assertEqual(response.status_code, 200)
        
        reports = response.json()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]['title'], 'Тестовый отчет')
        
        # 3. Вход родителя и получение отчетов
        self.client.force_login(self.parent_user)
        response = self.client.get('/api/dashboard/parent/reports/')
        self.assertEqual(response.status_code, 200)
        
        parent_reports = response.json()
        self.assertEqual(len(parent_reports), 1)
        self.assertEqual(parent_reports[0]['title'], 'Тестовый отчет')
    
    def test_payment_api_endpoints(self):
        """Тест API endpoints для платежей"""
        # Создаем зачисление на предмет
        subject_enrollment = SubjectEnrollment.objects.create(
            student=self.student_user,
            teacher=self.teacher_user,
            subject='Математика',
            status=SubjectEnrollment.Status.ACTIVE
        )
        
        self.client.force_login(self.parent_user)
        
        # 1. Инициация платежа
        payment_data = {
            'subject_id': subject_enrollment.id,
            'amount': 1000
        }
        
        response = self.client.post(
            f'/api/dashboard/parent/payment/{subject_enrollment.id}/',
            data=json.dumps(payment_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 2. Получение истории платежей
        response = self.client.get('/api/dashboard/parent/payments/')
        self.assertEqual(response.status_code, 200)
    
    def test_authentication_api_endpoints(self):
        """Тест API endpoints для аутентификации"""
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
        
        # 2. Получение профиля
        token = data['token']
        response = self.client.get(
            '/api/auth/profile/',
            HTTP_AUTHORIZATION=f'Token {token}'
        )
        self.assertEqual(response.status_code, 200)
        
        profile_data = response.json()
        self.assertEqual(profile_data['email'], 'student@test.com')
        self.assertEqual(profile_data['role'], 'student')
        
        # 3. Выход
        response = self.client.post(
            '/api/auth/logout/',
            HTTP_AUTHORIZATION=f'Token {token}'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_permission_restrictions(self):
        """Тест ограничений доступа по ролям"""
        # 1. Студент не может получить данные родителя
        self.client.force_login(self.student_user)
        response = self.client.get('/api/dashboard/parent/')
        self.assertEqual(response.status_code, 403)
        
        # 2. Родитель не может получить данные преподавателя
        self.client.force_login(self.parent_user)
        response = self.client.get('/api/dashboard/teacher/')
        self.assertEqual(response.status_code, 403)
        
        # 3. Преподаватель не может получить данные родителя
        self.client.force_login(self.teacher_user)
        response = self.client.get('/api/dashboard/parent/')
        self.assertEqual(response.status_code, 403)
        
        # 4. Неаутентифицированный пользователь не может получить данные
        self.client.logout()
        response = self.client.get('/api/dashboard/student/')
        self.assertEqual(response.status_code, 401)
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        # 1. Неверные данные при создании отчета
        self.client.force_login(self.teacher_user)
        
        invalid_report_data = {
            'student_id': 99999,  # Несуществующий студент
            'report_type': 'invalid_type',
            'title': '',
            'content': ''
        }
        
        response = self.client.post(
            '/api/reports/create/',
            data=json.dumps(invalid_report_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        # 2. Несуществующий endpoint
        response = self.client.get('/api/nonexistent/')
        self.assertEqual(response.status_code, 404)
        
        # 3. Неверный метод для endpoint
        response = self.client.delete('/api/dashboard/student/')
        self.assertEqual(response.status_code, 405)


if __name__ == '__main__':
    pytest.main([__file__])
