import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from backend.applications.models import Application
from backend.applications.application_service import ApplicationService
from backend.accounts.models import StudentProfile, ParentProfile

User = get_user_model()


class ApplicationServiceTestCase(TestCase):
    """
    Тесты для ApplicationService
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.service = ApplicationService()
        
        # Создаем администратора
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        
        # Создаем тестовую заявку студента
        self.student_application = Application.objects.create(
            first_name='Иван',
            last_name='Петров',
            email='ivan@test.com',
            phone='+79001234567',
            telegram_id='123456789',
            applicant_type=Application.ApplicantType.STUDENT,
            grade='10',
            motivation='Хочу изучать программирование',
            parent_first_name='Петр',
            parent_last_name='Петров',
            parent_email='petr@test.com',
            parent_phone='+79007654321',
            parent_telegram_id='987654321'
        )
        
        # Создаем тестовую заявку преподавателя
        self.teacher_application = Application.objects.create(
            first_name='Мария',
            last_name='Иванова',
            email='maria@test.com',
            phone='+79005555555',
            telegram_id='555555555',
            applicant_type=Application.ApplicantType.TEACHER,
            subject='Математика',
            experience='5 лет опыта преподавания'
        )
    
    def test_generate_credentials(self):
        """Тест генерации учетных данных"""
        username, password = self.service._generate_credentials(self.student_application)
        
        # Проверяем, что имя пользователя сгенерировано корректно
        self.assertEqual(username, 'иван.петров')
        
        # Проверяем, что пароль имеет правильную длину
        self.assertEqual(len(password), 12)
        
        # Проверяем, что пароль содержит буквы и цифры
        self.assertTrue(any(c.isalpha() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
    
    def test_generate_unique_username(self):
        """Тест генерации уникального имени пользователя"""
        # Создаем пользователя с именем, которое может конфликтовать
        User.objects.create_user(
            username='иван.петров',
            email='existing@test.com',
            password='testpass'
        )
        
        username, _ = self.service._generate_credentials(self.student_application)
        
        # Проверяем, что сгенерировано уникальное имя
        self.assertEqual(username, 'иван.петров1')
    
    @patch('backend.applications.application_service.telegram_notification_service')
    def test_approve_student_application(self, mock_telegram):
        """Тест одобрения заявки студента"""
        # Настраиваем мок
        mock_telegram.send_credentials.return_value = {'ok': True}
        mock_telegram.send_parent_link.return_value = {'ok': True}
        
        # Одобряем заявку
        result = self.service.approve_application(self.student_application, self.admin_user)
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Обновляем объект из базы данных
        self.student_application.refresh_from_db()
        
        # Проверяем, что статус изменился
        self.assertEqual(self.student_application.status, Application.Status.APPROVED)
        self.assertEqual(self.student_application.processed_by, self.admin_user)
        self.assertIsNotNone(self.student_application.processed_at)
        
        # Проверяем, что созданы учетные данные
        self.assertIsNotNone(self.student_application.generated_username)
        self.assertIsNotNone(self.student_application.generated_password)
        self.assertIsNotNone(self.student_application.parent_username)
        self.assertIsNotNone(self.student_application.parent_password)
        
        # Проверяем, что создан пользователь-студент
        student_user = User.objects.get(username=self.student_application.generated_username)
        self.assertEqual(student_user.role, User.Role.STUDENT)
        self.assertEqual(student_user.first_name, 'Иван')
        self.assertEqual(student_user.last_name, 'Петров')
        
        # Проверяем, что создан профиль студента
        self.assertTrue(hasattr(student_user, 'student_profile'))
        self.assertEqual(student_user.student_profile.grade, '10')
        
        # Проверяем, что создан родительский пользователь
        parent_user = User.objects.get(username=self.student_application.parent_username)
        self.assertEqual(parent_user.role, User.Role.PARENT)
        self.assertEqual(parent_user.first_name, 'Петр')
        
        # Проверяем связь родитель-ребенок
        self.assertTrue(hasattr(parent_user, 'parent_profile'))
        self.assertIn(student_user, parent_user.parent_profile.children.all())
        
        # Проверяем, что вызваны методы отправки уведомлений
        mock_telegram.send_credentials.assert_called_once()
        mock_telegram.send_parent_link.assert_called_once()
    
    @patch('backend.applications.application_service.telegram_notification_service')
    def test_approve_teacher_application(self, mock_telegram):
        """Тест одобрения заявки преподавателя"""
        # Настраиваем мок
        mock_telegram.send_credentials.return_value = {'ok': True}
        
        # Одобряем заявку
        result = self.service.approve_application(self.teacher_application, self.admin_user)
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Обновляем объект из базы данных
        self.teacher_application.refresh_from_db()
        
        # Проверяем, что статус изменился
        self.assertEqual(self.teacher_application.status, Application.Status.APPROVED)
        
        # Проверяем, что создан пользователь-преподаватель
        teacher_user = User.objects.get(username=self.teacher_application.generated_username)
        self.assertEqual(teacher_user.role, User.Role.TEACHER)
        
        # Проверяем, что создан профиль преподавателя
        self.assertTrue(hasattr(teacher_user, 'teacher_profile'))
        self.assertEqual(teacher_user.teacher_profile.subject, 'Математика')
        
        # Проверяем, что родительский аккаунт не создан
        self.assertEqual(self.teacher_application.parent_username, '')
        
        # Проверяем, что вызван только один метод отправки уведомлений
        mock_telegram.send_credentials.assert_called_once()
    
    @patch('backend.applications.application_service.telegram_notification_service')
    def test_reject_application(self, mock_telegram):
        """Тест отклонения заявки"""
        # Настраиваем мок
        mock_telegram.send_application_status.return_value = {'ok': True}
        
        reason = "Недостаточно опыта"
        
        # Отклоняем заявку
        result = self.service.reject_application(self.teacher_application, self.admin_user, reason)
        
        # Проверяем результат
        self.assertTrue(result)
        
        # Обновляем объект из базы данных
        self.teacher_application.refresh_from_db()
        
        # Проверяем, что статус изменился
        self.assertEqual(self.teacher_application.status, Application.Status.REJECTED)
        self.assertEqual(self.teacher_application.processed_by, self.admin_user)
        self.assertEqual(self.teacher_application.notes, reason)
        
        # Проверяем, что пользователь не создан
        self.assertFalse(User.objects.filter(email=self.teacher_application.email).exists())
        
        # Проверяем, что вызван метод отправки уведомления об отклонении
        mock_telegram.send_application_status.assert_called_once_with(
            self.teacher_application.telegram_id,
            Application.Status.REJECTED,
            reason
        )
    
    def test_approve_already_processed_application(self):
        """Тест попытки одобрения уже обработанной заявки"""
        # Устанавливаем статус как уже обработанный
        self.student_application.status = Application.Status.APPROVED
        self.student_application.save()
        
        # Пытаемся одобрить заявку
        result = self.service.approve_application(self.student_application, self.admin_user)
        
        # Проверяем, что операция не удалась
        self.assertFalse(result)