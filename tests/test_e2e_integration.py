#!/usr/bin/env python3
"""
End-to-end интеграционные тесты для полного workflow платформы
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


class E2EApplicationWorkflowTestCase(TestCase):
    """
    End-to-end тесты для полного workflow подачи и одобрения заявок
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаем администратора
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            role=User.Role.ADMIN
        )
        
        # Создаем тестовую заявку студента
        self.student_application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan@test.com',
            'phone': '+79001234567',
            'telegram_id': '123456789',
            'applicant_type': Application.ApplicantType.STUDENT,
            'grade': '10',
            'motivation': 'Хочу изучать программирование',
            'parent_first_name': 'Петр',
            'parent_last_name': 'Петров',
            'parent_email': 'petr@test.com',
            'parent_phone': '+79007654321',
            'parent_telegram_id': '987654321'
        }
        
        # Создаем тестовую заявку преподавателя
        self.teacher_application_data = {
            'first_name': 'Мария',
            'last_name': 'Иванова',
            'email': 'maria@test.com',
            'phone': '+79005555555',
            'telegram_id': '555555555',
            'applicant_type': Application.ApplicantType.TEACHER,
            'subject': 'Математика',
            'experience': '5 лет опыта преподавания'
        }
    
    def test_complete_student_application_workflow(self):
        """Тест полного workflow подачи и одобрения заявки студента"""
        # 1. Подача заявки студента
        response = self.client.post(
            '/api/applications/submit/',
            data=json.dumps(self.student_application_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        application = Application.objects.get(email='ivan@test.com')
        self.assertEqual(application.status, Application.Status.PENDING)
        
        # 2. Вход администратора
        self.client.force_login(self.admin_user)
        
        # 3. Одобрение заявки с моком Telegram
        with patch('backend.applications.application_service.telegram_notification_service') as mock_telegram:
            mock_telegram.send_credentials.return_value = {'ok': True}
            mock_telegram.send_parent_link.return_value = {'ok': True}
            
            response = self.client.post(
                f'/api/applications/{application.id}/approve/',
                data=json.dumps({'notes': 'Заявка одобрена'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Проверяем, что заявка одобрена
            application.refresh_from_db()
            self.assertEqual(application.status, Application.Status.APPROVED)
            
            # Проверяем, что созданы пользователи
            student_user = User.objects.get(email='ivan@test.com')
            parent_user = User.objects.get(email='petr@test.com')
            
            self.assertEqual(student_user.role, User.Role.STUDENT)
            self.assertEqual(parent_user.role, User.Role.PARENT)
            
            # Проверяем профили
            self.assertTrue(hasattr(student_user, 'student_profile'))
            self.assertTrue(hasattr(parent_user, 'parent_profile'))
            
            # Проверяем связь родитель-ребенок
            self.assertIn(student_user, parent_user.parent_profile.children.all())
            
            # Проверяем, что отправлены уведомления
            self.assertEqual(mock_telegram.send_credentials.call_count, 2)  # студент + родитель
            self.assertEqual(mock_telegram.send_parent_link.call_count, 1)
    
    def test_complete_teacher_application_workflow(self):
        """Тест полного workflow подачи и одобрения заявки преподавателя"""
        # 1. Подача заявки преподавателя
        response = self.client.post(
            '/api/applications/submit/',
            data=json.dumps(self.teacher_application_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        application = Application.objects.get(email='maria@test.com')
        
        # 2. Вход администратора
        self.client.force_login(self.admin_user)
        
        # 3. Одобрение заявки
        with patch('backend.applications.application_service.telegram_notification_service') as mock_telegram:
            mock_telegram.send_credentials.return_value = {'ok': True}
            
            response = self.client.post(
                f'/api/applications/{application.id}/approve/',
                data=json.dumps({'notes': 'Заявка одобрена'}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Проверяем, что создан пользователь-преподаватель
            teacher_user = User.objects.get(email='maria@test.com')
            self.assertEqual(teacher_user.role, User.Role.TEACHER)
            self.assertTrue(hasattr(teacher_user, 'teacher_profile'))
            self.assertEqual(teacher_user.teacher_profile.subject, 'Математика')


class E2EDashboardWorkflowTestCase(TestCase):
    """
    End-to-end тесты для полных workflow дашбордов всех ролей
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаем пользователей разных ролей
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
    
    def test_student_dashboard_workflow(self):
        """Тест полного workflow дашборда студента"""
        # Вход студента
        self.client.force_login(self.student_user)
        
        # 1. Получение данных дашборда
        response = self.client.get('/api/dashboard/student/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('materials', data)
        self.assertIn('progress', data)
        
        # 2. Получение назначенных материалов
        response = self.client.get('/api/materials/student/assigned/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Доступ к общему чату
        response = self.client.get('/api/chat/general/')
        self.assertEqual(response.status_code, 200)
        
        # 4. Отправка сообщения в чат
        message_data = {
            'content': 'Привет всем!',
            'room_id': self.general_chat.id
        }
        response = self.client.post(
            '/api/chat/general/message/',
            data=json.dumps(message_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # Проверяем, что сообщение создано
        self.assertTrue(Message.objects.filter(
            content='Привет всем!',
            sender=self.student_user,
            room=self.general_chat
        ).exists())
    
    def test_parent_dashboard_workflow(self):
        """Тест полного workflow дашборда родителя"""
        # Вход родителя
        self.client.force_login(self.parent_user)
        
        # 1. Получение данных дашборда
        response = self.client.get('/api/dashboard/parent/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('children', data)
        self.assertIn('payments', data)
        
        # 2. Получение информации о детях
        response = self.client.get('/api/dashboard/parent/children/')
        self.assertEqual(response.status_code, 200)
        
        children_data = response.json()
        self.assertEqual(len(children_data), 1)
        self.assertEqual(children_data[0]['first_name'], 'Иван')
        
        # 3. Создание предмета и зачисления
        subject_enrollment = SubjectEnrollment.objects.create(
            student=self.student_user,
            teacher=self.teacher_user,
            subject='Математика',
            status=SubjectEnrollment.Status.ACTIVE
        )
        
        # 4. Инициация платежа
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
    
    def test_teacher_dashboard_workflow(self):
        """Тест полного workflow дашборда преподавателя"""
        # Вход преподавателя
        self.client.force_login(self.teacher_user)
        
        # 1. Получение данных дашборда
        response = self.client.get('/api/dashboard/teacher/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('students', data)
        self.assertIn('materials', data)
        
        # 2. Распределение материала студентам
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
        
        # 3. Создание отчета о прогрессе студента
        report_data = {
            'student_id': self.student_user.id,
            'report_type': StudentReport.ReportType.PROGRESS,
            'title': 'Отчет о прогрессе',
            'content': 'Студент показывает хорошие результаты',
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
        
        # Проверяем, что отчет создан
        self.assertTrue(StudentReport.objects.filter(
            student=self.student_user,
            created_by=self.teacher_user,
            title='Отчет о прогрессе'
        ).exists())
        
        # 4. Получение отправленных отчетов
        response = self.client.get('/api/reports/teacher/')
        self.assertEqual(response.status_code, 200)
        
        reports = response.json()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]['title'], 'Отчет о прогрессе')


class E2EChatForumTestCase(TestCase):
    """
    End-to-end тесты для функциональности общего чата и системы веток
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаем пользователей
        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Иван',
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
        
        # Создаем общий чат
        self.general_chat = ChatRoom.objects.create(
            name='Общий чат',
            room_type=ChatRoom.RoomType.GENERAL
        )
        self.general_chat.participants.add(self.student_user, self.teacher_user)
    
    def test_general_chat_forum_functionality(self):
        """Тест функциональности общего чата как форума"""
        # Вход студента
        self.client.force_login(self.student_user)
        
        # 1. Получение доступа к общему чату
        response = self.client.get('/api/chat/general/')
        self.assertEqual(response.status_code, 200)
        
        # 2. Отправка основного сообщения
        message_data = {
            'content': 'Вопрос по домашнему заданию',
            'room_id': self.general_chat.id
        }
        response = self.client.post(
            '/api/chat/general/message/',
            data=json.dumps(message_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        main_message = Message.objects.get(content='Вопрос по домашнему заданию')
        
        # 3. Вход преподавателя
        self.client.force_login(self.teacher_user)
        
        # 4. Ответ в ветке сообщения
        reply_data = {
            'content': 'Отвечаю на ваш вопрос',
            'parent_message_id': main_message.id
        }
        response = self.client.post(
            f'/api/chat/general/thread/{main_message.id}/',
            data=json.dumps(reply_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # Проверяем, что создана ветка
        self.assertTrue(MessageThread.objects.filter(
            parent_message=main_message
        ).exists())
        
        # 5. Получение сообщений с пагинацией
        response = self.client.get('/api/chat/general/messages/')
        self.assertEqual(response.status_code, 200)
        
        messages_data = response.json()
        self.assertIn('results', messages_data)
        self.assertIn('count', messages_data)
        
        # 6. Проверяем, что роли отображаются в сообщениях
        self.assertEqual(messages_data['results'][0]['sender_role'], 'student')
        self.assertEqual(messages_data['results'][1]['sender_role'], 'teacher')
    
    def test_chat_moderation_capabilities(self):
        """Тест возможностей модерации чата"""
        # Вход преподавателя
        self.client.force_login(self.teacher_user)
        
        # 1. Отправка сообщения
        message_data = {
            'content': 'Сообщение от преподавателя',
            'room_id': self.general_chat.id
        }
        response = self.client.post(
            '/api/chat/general/message/',
            data=json.dumps(message_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # 2. Проверяем, что преподаватель может видеть все сообщения
        response = self.client.get('/api/chat/general/messages/')
        self.assertEqual(response.status_code, 200)
        
        messages_data = response.json()
        self.assertGreaterEqual(len(messages_data['results']), 1)


class E2EReportNotificationTestCase(TestCase):
    """
    End-to-end тесты для создания отчетов и системы уведомлений родителей
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаем пользователей
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
    
    @patch('backend.reports.report_service.telegram_notification_service')
    def test_report_creation_and_parent_notification(self, mock_telegram):
        """Тест создания отчета и уведомления родителей"""
        # Настраиваем мок
        mock_telegram.send_notification.return_value = {'ok': True}
        
        # Вход преподавателя
        self.client.force_login(self.teacher_user)
        
        # 1. Создание отчета о прогрессе
        report_data = {
            'student_id': self.student_user.id,
            'report_type': StudentReport.ReportType.PROGRESS,
            'title': 'Еженедельный отчет',
            'content': 'Студент показывает отличные результаты',
            'metrics': {
                'attendance': 100,
                'homework_completion': 95,
                'test_scores': 90
            }
        }
        
        response = self.client.post(
            '/api/reports/create/',
            data=json.dumps(report_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # Проверяем, что отчет создан
        report = StudentReport.objects.get(
            student=self.student_user,
            created_by=self.teacher_user
        )
        self.assertEqual(report.title, 'Еженедельный отчет')
        self.assertEqual(report.report_type, StudentReport.ReportType.PROGRESS)
        
        # 2. Вход родителя
        self.client.force_login(self.parent_user)
        
        # 3. Получение отчетов о ребенке
        response = self.client.get('/api/dashboard/parent/reports/')
        self.assertEqual(response.status_code, 200)
        
        reports_data = response.json()
        self.assertEqual(len(reports_data), 1)
        self.assertEqual(reports_data[0]['title'], 'Еженедельный отчет')
        
        # 4. Проверяем, что отправлено уведомление родителю
        # (В реальном приложении это будет происходить автоматически при создании отчета)
        mock_telegram.send_notification.assert_called()
    
    def test_multiple_reports_for_different_students(self):
        """Тест создания отчетов для разных студентов"""
        # Создаем второго студента
        student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role=User.Role.STUDENT,
            first_name='Анна',
            last_name='Сидорова'
        )
        
        StudentProfile.objects.create(
            user=student2,
            grade='9'
        )
        
        # Связываем с тем же родителем
        self.parent_profile.children.add(student2)
        
        # Вход преподавателя
        self.client.force_login(self.teacher_user)
        
        # Создаем отчеты для обоих студентов
        for student in [self.student_user, student2]:
            report_data = {
                'student_id': student.id,
                'report_type': StudentReport.ReportType.PROGRESS,
                'title': f'Отчет для {student.first_name}',
                'content': f'Прогресс студента {student.first_name}',
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
        
        # Проверяем, что созданы оба отчета
        self.assertEqual(StudentReport.objects.count(), 2)
        
        # Вход родителя
        self.client.force_login(self.parent_user)
        
        # Проверяем, что родитель видит отчеты обоих детей
        response = self.client.get('/api/dashboard/parent/reports/')
        self.assertEqual(response.status_code, 200)
        
        reports_data = response.json()
        self.assertEqual(len(reports_data), 2)
        
        # Проверяем, что отчеты принадлежат детям этого родителя
        student_ids = [report['student_id'] for report in reports_data]
        self.assertIn(self.student_user.id, student_ids)
        self.assertIn(student2.id, student_ids)


if __name__ == '__main__':
    pytest.main([__file__])
