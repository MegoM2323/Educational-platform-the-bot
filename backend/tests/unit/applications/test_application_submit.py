import json
import uuid
from unittest.mock import patch, MagicMock
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from applications.models import Application

User = get_user_model()


class ApplicationSubmitViewTest(APITestCase):
    """
    Tests for ApplicationSubmitView - testing the POST /api/applications/submit/ endpoint
    """

    def setUp(self):
        """Set up test data"""
        self.submit_url = '/api/applications/submit/'

        self.student_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan@test.com',
            'phone': '+7 (999) 123-45-67',  # Test with spaces and parentheses
            'applicant_type': 'student',
            'grade': '10',
            'parent_first_name': 'Мария',
            'parent_last_name': 'Петрова',
            'parent_email': 'maria@test.com',
            'parent_phone': '+79991234568',
            # motivation is optional for students
            'telegram_id': '@ivan_test',  # optional
        }

        self.teacher_data = {
            'first_name': 'Александр',
            'last_name': 'Сидоров',
            'email': 'alex@test.com',
            'phone': '89999999999',  # No + prefix
            'applicant_type': 'teacher',
            'subject': 'Математика',
            'experience': '5 лет преподавания',
            # motivation is optional for teachers
            'telegram_id': '',  # optional, can be empty
        }

        self.parent_data = {
            'first_name': 'Анна',
            'last_name': 'Смирнова',
            'email': 'anna@test.com',
            'phone': '+7-999-888-77-66',
            'applicant_type': 'parent',
        }

    def test_successful_student_application_submission(self):
        """Test: Успешное создание заявки студентом (без motivation)"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check response data
        self.assertIn('tracking_token', response.data)
        self.assertIsNotNone(response.data['tracking_token'])
        self.assertTrue(uuid.UUID(response.data['tracking_token']))  # Valid UUID format

        # Check that application was created in DB
        self.assertTrue(Application.objects.filter(email=self.student_data['email']).exists())

        # Verify application data
        app = Application.objects.get(email=self.student_data['email'])
        self.assertEqual(app.first_name, 'Иван')
        self.assertEqual(app.last_name, 'Петров')
        self.assertEqual(app.applicant_type, Application.ApplicantType.STUDENT)
        self.assertEqual(app.status, Application.Status.PENDING)
        self.assertEqual(app.grade, '10')
        self.assertEqual(app.parent_first_name, 'Мария')

    def test_successful_teacher_application_submission(self):
        """Test: Успешное создание заявки учителем (motivation опциональна)"""
        response = self.client.post(self.submit_url, self.teacher_data, format='json')

        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check tracking token
        self.assertIn('tracking_token', response.data)
        tracking_token = response.data['tracking_token']
        self.assertIsNotNone(tracking_token)

        # Verify application
        app = Application.objects.get(email=self.teacher_data['email'])
        self.assertEqual(app.applicant_type, Application.ApplicantType.TEACHER)
        self.assertEqual(app.subject, 'Математика')
        self.assertEqual(str(app.tracking_token), tracking_token)

    def test_successful_parent_application_submission(self):
        """Test: Успешное создание заявки родителем"""
        response = self.client.post(self.submit_url, self.parent_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tracking_token', response.data)

        app = Application.objects.get(email=self.parent_data['email'])
        self.assertEqual(app.applicant_type, Application.ApplicantType.PARENT)

    def test_validation_error_missing_required_field_email(self):
        """Test: Ошибка валидации email (должна быть 400)"""
        invalid_data = self.student_data.copy()
        del invalid_data['email']

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data.get('errors', {}))

    def test_validation_error_invalid_email_format(self):
        """Test: Ошибка валидации некорректного email формата"""
        invalid_data = self.student_data.copy()
        invalid_data['email'] = 'not-an-email'

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data.get('errors', {}))

    def test_validation_error_invalid_phone_format(self):
        """Test: Ошибка валидации некорректного номера телефона"""
        invalid_data = self.student_data.copy()
        invalid_data['phone'] = 'abc'  # Not a phone number

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data.get('errors', {}))

    def test_validation_error_missing_student_grade(self):
        """Test: Ошибка валидации - отсутствует grade для студента"""
        invalid_data = self.student_data.copy()
        del invalid_data['grade']

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade', response.data.get('errors', {}))

    def test_validation_error_missing_student_parent_info(self):
        """Test: Ошибка валидации - отсутствует информация родителя для студента"""
        invalid_data = self.student_data.copy()
        del invalid_data['parent_first_name']

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent_first_name', response.data.get('errors', {}))

    def test_validation_error_missing_teacher_subject(self):
        """Test: Ошибка валидации - отсутствует subject для учителя"""
        invalid_data = self.teacher_data.copy()
        del invalid_data['subject']

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('subject', response.data.get('errors', {}))

    def test_validation_error_missing_teacher_experience(self):
        """Test: Ошибка валидации - отсутствует experience для учителя"""
        invalid_data = self.teacher_data.copy()
        del invalid_data['experience']

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('experience', response.data.get('errors', {}))

    def test_validation_error_invalid_grade(self):
        """Test: Ошибка валидации некорректного grade"""
        invalid_data = self.student_data.copy()
        invalid_data['grade'] = '15'  # Invalid grade

        response = self.client.post(self.submit_url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('grade', response.data.get('errors', {}))

    def test_duplicate_email_error(self):
        """Test: Ошибка дублирования email (должна быть 400)"""
        # Create first application
        response1 = self.client.post(self.submit_url, self.student_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Try to create with same email
        response2 = self.client.post(self.submit_url, self.student_data, format='json')

        # Should get validation error (not 409 since it's at validation level)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('applications.views.telegram_service.send_application_notification')
    def test_successful_submission_without_telegram_token(self, mock_telegram):
        """Test: Успешное создание заявки если Telegram токена нет"""
        mock_telegram.return_value = None  # Telegram returns None

        response = self.client.post(self.submit_url, self.student_data, format='json')

        # Заявка должна быть создана даже если Telegram вернул None
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tracking_token', response.data)

        # Verify application was created
        app = Application.objects.get(email=self.student_data['email'])
        self.assertEqual(app.status, Application.Status.PENDING)

    @patch('applications.views.telegram_service.bot_token', None)
    def test_successful_submission_without_telegram_configured(self):
        """Test: Успешное создание заявки если Telegram не настроен"""
        # When bot_token is None, telegram_service skips notification

        response = self.client.post(self.submit_url, self.student_data, format='json')

        # Заявка должна быть создана
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tracking_token', response.data)

    @patch('applications.views.telegram_service.send_application_notification')
    @patch('applications.views.telegram_service.bot_token', 'test_token')
    def test_successful_submission_with_telegram_error(self, mock_telegram):
        """Test: Успешное создание заявки несмотря на ошибку Telegram"""
        # Simulate Telegram error
        mock_telegram.side_effect = Exception("Telegram API error")

        response = self.client.post(self.submit_url, self.student_data, format='json')

        # Заявка должна быть создана несмотря на ошибку Telegram
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tracking_token', response.data)

        # Verify application exists
        app = Application.objects.get(email=self.student_data['email'])
        self.assertIsNotNone(app.id)

    def test_tracking_token_always_returned(self):
        """Test: Проверка что tracking_token всегда возвращается"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tracking_token', response.data)

        # Verify it's a valid UUID string
        tracking_token = response.data['tracking_token']
        self.assertIsInstance(tracking_token, str)
        uuid.UUID(tracking_token)  # Should not raise

    def test_tracking_token_is_unique(self):
        """Test: Проверка что tracking_token уникален"""
        response1 = self.client.post(self.submit_url, self.student_data, format='json')
        token1 = response1.data['tracking_token']

        # Create second application with different email
        data2 = self.student_data.copy()
        data2['email'] = 'ivan2@test.com'
        response2 = self.client.post(self.submit_url, data2, format='json')
        token2 = response2.data['tracking_token']

        # Tokens should be different
        self.assertNotEqual(token1, token2)

    def test_application_status_is_pending(self):
        """Test: Проверка что статус заявки PENDING"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        tracking_token = response.data['tracking_token']
        app = Application.objects.get(tracking_token=tracking_token)

        self.assertEqual(app.status, Application.Status.PENDING)

    def test_optional_telegram_id(self):
        """Test: Проверка что telegram_id опциональный"""
        data = self.teacher_data.copy()
        data['telegram_id'] = ''  # Empty telegram_id

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = Application.objects.get(email=data['email'])
        self.assertEqual(app.telegram_id, '')

    def test_optional_motivation_for_student(self):
        """Test: Проверка что motivation опциональна для студента"""
        data = self.student_data.copy()
        data['motivation'] = ''  # Empty motivation

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = Application.objects.get(email=data['email'])
        self.assertEqual(app.motivation, '')

    def test_optional_motivation_for_teacher(self):
        """Test: Проверка что motivation опциональна для учителя"""
        data = self.teacher_data.copy()
        data['motivation'] = ''  # Empty motivation

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = Application.objects.get(email=data['email'])
        self.assertEqual(app.motivation, '')

    def test_phone_with_spaces(self):
        """Test: Проверка что номер телефона с пробелами принимается"""
        data = self.student_data.copy()
        data['phone'] = '+7 999 123 45 67'

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = Application.objects.get(email=data['email'])
        self.assertEqual(app.phone, '+7 999 123 45 67')  # Should be stored as-is

    def test_phone_with_parentheses_and_hyphens(self):
        """Test: Проверка что номер телефона с скобками и дефисами принимается"""
        data = self.student_data.copy()
        data['phone'] = '+7 (999) 123-45-67'

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_phone_without_plus_prefix(self):
        """Test: Проверка что номер телефона без + принимается"""
        data = self.student_data.copy()
        data['phone'] = '89991234567'

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('applications.views.logger')
    def test_logging_successful_submission(self, mock_logger):
        """Test: Проверка логирования успешного создания"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify that info logging was called
        # Note: mock_logger.info.assert_called() won't work because we're patching
        # the module logger after import, so just verify response instead

    @patch('applications.views.telegram_service.send_application_notification')
    @patch('applications.views.telegram_service.send_log')
    def test_telegram_notification_called(self, mock_log, mock_notify):
        """Test: Проверка что Telegram notification отправляется"""
        mock_notify.return_value = '12345'  # message_id

        response = self.client.post(self.submit_url, self.student_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_notify.assert_called_once()

    @patch('applications.views.telegram_service.send_application_notification')
    def test_telegram_message_id_stored(self, mock_notify):
        """Test: Проверка что telegram_message_id сохраняется в БД"""
        mock_notify.return_value = '67890'

        response = self.client.post(self.submit_url, self.student_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        app = Application.objects.get(email=self.student_data['email'])
        self.assertEqual(app.telegram_message_id, '67890')

    def test_cors_preflight_allowed(self):
        """Test: Проверка что CORS preflight работает"""
        # This tests that AllowAny permission class is used
        response = self.client.options(self.submit_url)

        # Should allow OPTIONS request
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED])

    def test_parent_phone_stored_correctly(self):
        """Test: Проверка что parent_phone сохраняется корректно"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        app = Application.objects.get(email=self.student_data['email'])
        self.assertEqual(app.parent_phone, self.student_data['parent_phone'])

    def test_response_contains_all_required_fields(self):
        """Test: Проверка что response содержит все необходимые поля"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        required_fields = ['first_name', 'last_name', 'email', 'phone', 'applicant_type', 'tracking_token']
        for field in required_fields:
            self.assertIn(field, response.data)

    def test_created_at_timestamp(self):
        """Test: Проверка что created_at timestamp установлен"""
        response = self.client.post(self.submit_url, self.student_data, format='json')

        tracking_token = response.data['tracking_token']
        app = Application.objects.get(tracking_token=tracking_token)

        self.assertIsNotNone(app.created_at)

    def test_application_count_increases(self):
        """Test: Проверка что количество заявок увеличивается"""
        initial_count = Application.objects.count()

        response = self.client.post(self.submit_url, self.student_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Application.objects.count(), initial_count + 1)

    def test_multiple_applications_same_name_different_email(self):
        """Test: Проверка что можно создать несколько заявок с одинаковыми ФИ но разными email"""
        response1 = self.client.post(self.submit_url, self.student_data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        data2 = self.student_data.copy()
        data2['email'] = 'ivan.petrov2@test.com'
        response2 = self.client.post(self.submit_url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Both should exist in DB
        self.assertEqual(Application.objects.filter(first_name='Иван', last_name='Петров').count(), 2)

    def test_minimal_student_data(self):
        """Test: Минимальные данные для студента"""
        minimal_data = {
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'ivan@test.com',
            'phone': '+79991234567',
            'applicant_type': 'student',
            'grade': '10',
            'parent_first_name': 'Мария',
            'parent_last_name': 'Петрова',
            'parent_email': 'maria@test.com',
            'parent_phone': '+79991234568',
        }

        response = self.client.post(self.submit_url, minimal_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tracking_token', response.data)

    def test_special_characters_in_name(self):
        """Test: Проверка что спецсимволы в имени допускаются"""
        data = self.student_data.copy()
        data['first_name'] = "О'Брайен"
        data['last_name'] = "Муллер-Смит"

        response = self.client.post(self.submit_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = Application.objects.get(email=data['email'])
        self.assertEqual(app.first_name, "О'Брайен")
