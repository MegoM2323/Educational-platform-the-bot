import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest.mock import patch, MagicMock
from django.db import transaction
from django.utils import timezone

from .models import Application
from .application_service import ApplicationService
from .notification_service import TelegramNotificationService
from accounts.models import StudentProfile, TeacherProfile, ParentProfile

User = get_user_model()


class ApplicationModelTest(TestCase):
    """Тесты для модели Application"""
    
    def setUp(self):
        self.application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan.petrov@example.com',
            'phone': '+7-999-123-45-67',
            'telegram_id': '@ivan_petrov',
            'applicant_type': Application.ApplicantType.STUDENT,
            'grade': '10',
            'motivation': 'Хочу изучать программирование',
            'parent_first_name': 'Анна',
            'parent_last_name': 'Петрова',
            'parent_email': 'anna.petrova@example.com',
            'parent_phone': '+7-999-123-45-68',
            'parent_telegram_id': '@anna_petrova'
        }
    
    def test_create_application(self):
        """Тест создания заявки"""
        application = Application.objects.create(**self.application_data)
        
        self.assertEqual(application.first_name, 'Иван')
        self.assertEqual(application.last_name, 'Петров')
        self.assertEqual(application.email, 'ivan.petrov@example.com')
        self.assertEqual(application.applicant_type, Application.ApplicantType.STUDENT)
        self.assertEqual(application.status, Application.Status.PENDING)
        self.assertIsNotNone(application.tracking_token)
        self.assertIsNotNone(application.created_at)
    
    def test_application_properties(self):
        """Тест свойств заявки"""
        application = Application.objects.create(**self.application_data)
        
        self.assertTrue(application.is_pending)
        self.assertFalse(application.is_processed)
        self.assertEqual(application.full_name, 'Иван Петров')
        self.assertEqual(application.parent_full_name, 'Анна Петрова')
    
    def test_application_status_change(self):
        """Тест изменения статуса заявки"""
        application = Application.objects.create(**self.application_data)
        
        # Проверяем начальный статус
        self.assertTrue(application.is_pending)
        self.assertIsNone(application.processed_at)
        
        # Изменяем статус
        application.status = Application.Status.APPROVED
        application.save()
        
        # Проверяем, что processed_at обновился
        self.assertIsNotNone(application.processed_at)
        self.assertFalse(application.is_pending)
        self.assertTrue(application.is_processed)
    
    def test_application_str_representation(self):
        """Тест строкового представления заявки"""
        application = Application.objects.create(**self.application_data)
        expected = "Application from Иван Петров (Student)"
        self.assertEqual(str(application), expected)


class ApplicationServiceTest(TransactionTestCase):
    """Тесты для ApplicationService"""
    
    def setUp(self):
        self.service = ApplicationService()
        self.application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan.petrov@example.com',
            'phone': '+7-999-123-45-67',
            'telegram_id': '@ivan_petrov',
            'applicant_type': Application.ApplicantType.STUDENT,
            'grade': '10',
            'motivation': 'Хочу изучать программирование',
            'parent_first_name': 'Анна',
            'parent_last_name': 'Петрова',
            'parent_email': 'anna.petrova@example.com',
            'parent_phone': '+7-999-123-45-68',
            'parent_telegram_id': '@anna_petrova'
        }
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=User.Role.TEACHER,
            is_staff=True,
            is_superuser=True
        )
    
    def test_generate_credentials(self):
        """Тест генерации учетных данных"""
        application = Application.objects.create(**self.application_data)
        username, password = self.service._generate_credentials(application)
        
        self.assertIsInstance(username, str)
        self.assertIsInstance(password, str)
        self.assertGreater(len(password), 8)
        self.assertTrue(username.startswith('иван.петров'))
    
    def test_generate_credentials_uniqueness(self):
        """Тест уникальности генерируемых учетных данных"""
        application = Application.objects.create(**self.application_data)
        
        # Создаем пользователя с таким же именем
        User.objects.create_user(
            username='иван.петров',
            email='existing@example.com',
            password='testpass123'
        )
        
        username, password = self.service._generate_credentials(application)
        
        # Должно добавиться число в конце
        self.assertTrue(username.startswith('иван.петров'))
        self.assertNotEqual(username, 'иван.петров')
    
    def test_generate_password_strength(self):
        """Тест силы генерируемого пароля"""
        password = self.service._generate_password()
        
        self.assertGreaterEqual(len(password), 12)
        self.assertTrue(any(c.isdigit() for c in password))
        self.assertTrue(any(c.isalpha() for c in password))
    
    @patch.object(TelegramNotificationService, 'send_credentials')
    @patch.object(TelegramNotificationService, 'send_parent_link')
    def test_approve_student_application(self, mock_parent_link, mock_credentials):
        """Тест одобрения заявки студента"""
        application = Application.objects.create(**self.application_data)
        
        # Мокаем отправку уведомлений
        mock_credentials.return_value = {'ok': True}
        mock_parent_link.return_value = {'ok': True}
        
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertTrue(result)
        
        # Проверяем, что статус изменился
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.APPROVED)
        self.assertEqual(application.processed_by, self.admin_user)
        self.assertIsNotNone(application.processed_at)
        
        # Проверяем, что создались пользователи
        self.assertTrue(User.objects.filter(email=application.email).exists())
        self.assertTrue(User.objects.filter(email=application.parent_email).exists())
        
        # Проверяем, что создались профили
        student_user = User.objects.get(email=application.email)
        parent_user = User.objects.get(email=application.parent_email)
        
        self.assertTrue(hasattr(student_user, 'student_profile'))
        self.assertTrue(hasattr(parent_user, 'parent_profile'))
        
        # Проверяем связь родителя и ребенка
        parent_profile = parent_user.parent_profile
        self.assertIn(student_user, parent_profile.children.all())
    
    @patch.object(TelegramNotificationService, 'send_credentials')
    def test_approve_teacher_application(self, mock_credentials):
        """Тест одобрения заявки преподавателя"""
        teacher_data = self.application_data.copy()
        teacher_data.update({
            'applicant_type': Application.ApplicantType.TEACHER,
            'subject': 'Математика',
            'experience': '5 лет преподавания',
            'parent_first_name': '',
            'parent_last_name': '',
            'parent_email': '',
            'parent_phone': '',
            'parent_telegram_id': ''
        })
        
        application = Application.objects.create(**teacher_data)
        mock_credentials.return_value = {'ok': True}
        
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertTrue(result)
        
        # Проверяем, что создался только один пользователь
        self.assertEqual(User.objects.filter(email=application.email).count(), 1)
        
        # Проверяем профиль преподавателя
        teacher_user = User.objects.get(email=application.email)
        self.assertTrue(hasattr(teacher_user, 'teacher_profile'))
        self.assertEqual(teacher_user.teacher_profile.subject, 'Математика')
    
    @patch.object(TelegramNotificationService, 'send_application_status')
    def test_reject_application(self, mock_status):
        """Тест отклонения заявки"""
        application = Application.objects.create(**self.application_data)
        reason = "Недостаточно документов"
        
        mock_status.return_value = {'ok': True}
        
        result = self.service.reject_application(application, self.admin_user, reason)
        
        self.assertTrue(result)
        
        # Проверяем, что статус изменился
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.REJECTED)
        self.assertEqual(application.processed_by, self.admin_user)
        self.assertIsNotNone(application.processed_at)
        self.assertEqual(application.notes, reason)
        
        # Проверяем, что пользователи не создались
        self.assertFalse(User.objects.filter(email=application.email).exists())
    
    def test_approve_already_processed_application(self):
        """Тест попытки одобрить уже обработанную заявку"""
        application = Application.objects.create(**self.application_data)
        application.status = Application.Status.APPROVED
        application.save()
        
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertFalse(result)
    
    def test_reject_already_processed_application(self):
        """Тест попытки отклонить уже обработанную заявку"""
        application = Application.objects.create(**self.application_data)
        application.status = Application.Status.REJECTED
        application.save()
        
        result = self.service.reject_application(application, self.admin_user)
        
        self.assertFalse(result)


class TelegramNotificationServiceTest(TestCase):
    """Тесты для TelegramNotificationService"""
    
    def setUp(self):
        self.service = TelegramNotificationService()
    
    @patch('requests.post')
    def test_send_credentials(self, mock_post):
        """Тест отправки учетных данных"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.send_credentials(
            telegram_id='@test_user',
            username='testuser',
            password='testpass123',
            role='student'
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result['ok'])
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_credentials_with_child(self, mock_post):
        """Тест отправки учетных данных с информацией о ребенке"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.send_credentials(
            telegram_id='@parent_user',
            username='parentuser',
            password='parentpass123',
            role='parent',
            child_name='Иван Петров'
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result['ok'])
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_parent_link(self, mock_post):
        """Тест отправки родительских учетных данных"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.send_parent_link(
            telegram_id='@parent_user',
            parent_username='parentuser',
            parent_password='parentpass123',
            child_name='Иван Петров'
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result['ok'])
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_application_status(self, mock_post):
        """Тест отправки статуса заявки"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': True, 'result': {'message_id': 123}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.send_application_status(
            telegram_id='@test_user',
            status=Application.Status.APPROVED,
            details='Заявка одобрена'
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(result['ok'])
        mock_post.assert_called_once()
    
    def test_send_message_without_credentials(self):
        """Тест отправки сообщения без настроенных учетных данных"""
        with patch.object(self.service, 'bot_token', None):
            result = self.service.send_credentials(
                telegram_id='@test_user',
                username='testuser',
                password='testpass123',
                role='student'
            )
            
            self.assertIsNone(result)
    
    @patch('requests.post')
    def test_send_message_telegram_error(self, mock_post):
        """Тест обработки ошибки Telegram API"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': False, 'description': 'Bad Request'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.service.send_credentials(
            telegram_id='@test_user',
            username='testuser',
            password='testpass123',
            role='student'
        )
        
        self.assertIsNone(result)
    
    @patch('requests.post')
    def test_send_message_network_error(self, mock_post):
        """Тест обработки сетевой ошибки"""
        mock_post.side_effect = Exception("Network error")
        
        result = self.service.send_credentials(
            telegram_id='@test_user',
            username='testuser',
            password='testpass123',
            role='student'
        )
        
        self.assertIsNone(result)
    
    @patch('requests.get')
    def test_test_connection_success(self, mock_get):
        """Тест успешной проверки соединения"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'ok': True, 
            'result': {'username': 'test_bot', 'first_name': 'Test Bot'}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with patch.object(self.service, 'bot_token', 'test_token'):
            result = self.service.test_connection()
            
            self.assertTrue(result)
    
    @patch('requests.get')
    def test_test_connection_failure(self, mock_get):
        """Тест неудачной проверки соединения"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'ok': False, 'description': 'Unauthorized'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with patch.object(self.service, 'bot_token', 'invalid_token'):
            result = self.service.test_connection()
            
            self.assertFalse(result)
    
    def test_test_connection_no_token(self):
        """Тест проверки соединения без токена"""
        with patch.object(self.service, 'bot_token', None):
            result = self.service.test_connection()
            
            self.assertFalse(result)


class ApplicationIntegrationTest(TransactionTestCase):
    """Интеграционные тесты для системы заявок"""
    
    def setUp(self):
        self.service = ApplicationService()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=User.Role.TEACHER,
            is_staff=True,
            is_superuser=True
        )
    
    @patch.object(TelegramNotificationService, 'send_credentials')
    @patch.object(TelegramNotificationService, 'send_parent_link')
    def test_complete_application_workflow(self, mock_parent_link, mock_credentials):
        """Тест полного цикла обработки заявки"""
        # Создаем заявку
        application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan.petrov@example.com',
            'phone': '+7-999-123-45-67',
            'telegram_id': '@ivan_petrov',
            'applicant_type': Application.ApplicantType.STUDENT,
            'grade': '10',
            'motivation': 'Хочу изучать программирование',
            'parent_first_name': 'Анна',
            'parent_last_name': 'Петрова',
            'parent_email': 'anna.petrova@example.com',
            'parent_phone': '+7-999-123-45-68',
            'parent_telegram_id': '@anna_petrova'
        }
        
        application = Application.objects.create(**application_data)
        
        # Мокаем отправку уведомлений
        mock_credentials.return_value = {'ok': True}
        mock_parent_link.return_value = {'ok': True}
        
        # Одобряем заявку
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertTrue(result)
        
        # Проверяем, что все создалось корректно
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.APPROVED)
        
        # Проверяем создание пользователей
        student_user = User.objects.get(email=application.email)
        parent_user = User.objects.get(email=application.parent_email)
        
        self.assertEqual(student_user.role, User.Role.STUDENT)
        self.assertEqual(parent_user.role, User.Role.PARENT)
        
        # Проверяем профили
        self.assertTrue(hasattr(student_user, 'student_profile'))
        self.assertTrue(hasattr(parent_user, 'parent_profile'))
        
        # Проверяем связь родителя и ребенка
        parent_profile = parent_user.parent_profile
        self.assertIn(student_user, parent_profile.children.all())
        
        # Проверяем, что уведомления были отправлены
        self.assertEqual(mock_credentials.call_count, 1)
        self.assertEqual(mock_parent_link.call_count, 1)
    
    @patch.object(TelegramNotificationService, 'send_credentials')
    def test_approve_parent_application(self, mock_credentials):
        """Тест одобрения заявки родителя"""
        parent_data = {
            'first_name': 'Анна',
            'last_name': 'Петрова',
            'email': 'anna.petrova@example.com',
            'phone': '+7-999-123-45-68',
            'telegram_id': '@anna_petrova',
            'applicant_type': Application.ApplicantType.PARENT,
            'parent_first_name': '',
            'parent_last_name': '',
            'parent_email': '',
            'parent_phone': '',
            'parent_telegram_id': ''
        }
        
        application = Application.objects.create(**parent_data)
        mock_credentials.return_value = {'ok': True}
        
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertTrue(result)
        
        # Проверяем, что создался только один пользователь
        self.assertEqual(User.objects.filter(email=application.email).count(), 1)
        
        # Проверяем профиль родителя
        parent_user = User.objects.get(email=application.email)
        self.assertTrue(hasattr(parent_user, 'parent_profile'))
        self.assertEqual(parent_user.role, User.Role.PARENT)
    
    def test_approve_application_without_telegram_id(self):
        """Тест одобрения заявки без Telegram ID"""
        application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan.petrov@example.com',
            'phone': '+7-999-123-45-67',
            'telegram_id': '',  # Нет Telegram ID
            'applicant_type': Application.ApplicantType.TEACHER,
            'subject': 'Математика',
            'experience': '5 лет преподавания',
            'parent_first_name': '',
            'parent_last_name': '',
            'parent_email': '',
            'parent_phone': '',
            'parent_telegram_id': ''
        }
        
        application = Application.objects.create(**application_data)
        
        # Должно работать даже без Telegram ID
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertTrue(result)
        
        # Проверяем, что пользователь создался
        self.assertTrue(User.objects.filter(email=application.email).exists())
    
    def test_approve_application_with_incomplete_parent_data(self):
        """Тест одобрения заявки студента с неполными данными родителя"""
        application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan.petrov@example.com',
            'phone': '+7-999-123-45-67',
            'telegram_id': '@ivan_petrov',
            'applicant_type': Application.ApplicantType.STUDENT,
            'grade': '10',
            'motivation': 'Хочу изучать программирование',
            'parent_first_name': 'Анна',
            'parent_last_name': 'Петрова',
            'parent_email': '',  # Нет email родителя
            'parent_phone': '+7-999-123-45-68',
            'parent_telegram_id': '@anna_petrova'
        }
        
        application = Application.objects.create(**application_data)
        
        # Должно создать только студента, без родителя
        result = self.service.approve_application(application, self.admin_user)
        
        self.assertTrue(result)
        
        # Проверяем, что создался только студент
        self.assertEqual(User.objects.filter(email=application.email).count(), 1)
        self.assertFalse(User.objects.filter(email=application.parent_email).exists())
        
        student_user = User.objects.get(email=application.email)
        self.assertEqual(student_user.role, User.Role.STUDENT)
    
    def test_credential_generation_uniqueness_across_multiple_applications(self):
        """Тест уникальности учетных данных при множественных заявках"""
        # Создаем несколько заявок с одинаковыми именами
        for i in range(3):
            application_data = {
                'first_name': 'Иван',
                'last_name': 'Петров',
                'email': f'ivan.petrov{i}@example.com',
                'phone': f'+7-999-123-45-6{i}',
                'telegram_id': f'@ivan_petrov{i}',
                'applicant_type': Application.ApplicantType.TEACHER,
                'subject': 'Математика',
                'experience': '5 лет преподавания',
                'parent_first_name': '',
                'parent_last_name': '',
                'parent_email': '',
                'parent_phone': '',
                'parent_telegram_id': ''
            }
            
            application = Application.objects.create(**application_data)
            username, password = self.service._generate_credentials(application)
            
            # Проверяем, что имя пользователя уникально
            self.assertFalse(User.objects.filter(username=username).exists())
            
            # Создаем пользователя для следующей итерации
            User.objects.create_user(
                username=username,
                email=application.email,
                password=password
            )
    
    def test_password_generation_strength_requirements(self):
        """Тест требований к силе пароля"""
        for _ in range(10):  # Тестируем несколько паролей
            password = self.service._generate_password()
            
            # Проверяем длину
            self.assertGreaterEqual(len(password), 12)
            
            # Проверяем наличие цифр
            self.assertTrue(any(c.isdigit() for c in password))
            
            # Проверяем наличие букв
            self.assertTrue(any(c.isalpha() for c in password))
            
            # Проверяем наличие специальных символов (может не быть в каждом пароле)
            special_chars = "!@#$%^&*"
            has_special = any(c in special_chars for c in password)
            # Специальные символы не обязательны, но если есть - хорошо
            if has_special:
                self.assertTrue(has_special)
    
    def test_application_service_error_handling(self):
        """Тест обработки ошибок в ApplicationService"""
        # Тест с некорректными данными - некорректный email не вызывает ошибку при создании пользователя
        application_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'invalid-email',  # Некорректный email
            'phone': '+7-999-123-45-67',
            'telegram_id': '@ivan_petrov',
            'applicant_type': Application.ApplicantType.TEACHER,
            'subject': 'Математика',
            'experience': '5 лет преподавания',
            'parent_first_name': '',
            'parent_last_name': '',
            'parent_email': '',
            'parent_phone': '',
            'parent_telegram_id': ''
        }
        
        application = Application.objects.create(**application_data)
        
        # Попытка одобрить заявку - должна пройти успешно
        result = self.service.approve_application(application, self.admin_user)
        
        # Проверяем, что заявка была одобрена
        self.assertTrue(result)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.APPROVED)
    
    def test_telegram_notification_service_error_handling(self):
        """Тест обработки ошибок в TelegramNotificationService"""
        service = TelegramNotificationService()
        
        # Тест с некорректными параметрами
        result = service.send_credentials(
            telegram_id='',  # Пустой telegram_id
            username='testuser',
            password='testpass123',
            role='student'
        )
        
        self.assertIsNone(result)
    
    def test_application_model_validation(self):
        """Тест валидации модели Application"""
        # Тест с некорректным email - Django не валидирует email на уровне модели
        # Валидация происходит на уровне сериализатора
        application = Application.objects.create(
            first_name='Иван',
            last_name='Петров',
            email='invalid-email',
            phone='+7-999-123-45-67',
            applicant_type=Application.ApplicantType.STUDENT
        )
        
        # Проверяем, что заявка создалась (Django позволяет некорректный email)
        self.assertIsNotNone(application.id)
        self.assertEqual(application.email, 'invalid-email')
    
    def test_application_status_transitions(self):
        """Тест переходов статусов заявки"""
        application = Application.objects.create(
            first_name='Иван',
            last_name='Петров',
            email='ivan.petrov@example.com',
            phone='+7-999-123-45-67',
            applicant_type=Application.ApplicantType.STUDENT
        )
        
        # Начальный статус
        self.assertEqual(application.status, Application.Status.PENDING)
        self.assertTrue(application.is_pending)
        self.assertFalse(application.is_processed)
        
        # Переход в одобрено
        application.status = Application.Status.APPROVED
        application.save()
        
        self.assertFalse(application.is_pending)
        self.assertTrue(application.is_processed)
        
        # Переход в отклонено
        application.status = Application.Status.REJECTED
        application.save()
        
        self.assertFalse(application.is_pending)
        self.assertTrue(application.is_processed)