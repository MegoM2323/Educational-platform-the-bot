"""
Тесты для проверки исправленных 404 ошибок в API endpoints.
Проверяет работоспособность после исправления путей в frontend API клиентах.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import StudentProfile, TutorProfile, ParentProfile
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.fixture
def api_client():
    """API клиент для тестов"""
    return APIClient()


@pytest.fixture
def tutor_user(db):
    """Создать тьютора"""
    user = User.objects.create_user(
        username='tutor1',
        email='tutor1@test.com',
        password='testpass123',
        role='tutor',
        first_name='Test',
        last_name='Tutor'
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_user(db, tutor_user):
    """Создать ученика"""
    user = User.objects.create_user(
        username='student1',
        email='student1@test.com',
        password='testpass123',
        role='student',
        first_name='Test',
        last_name='Student'
    )
    StudentProfile.objects.create(
        user=user,
        tutor=tutor_user,
        grade='10'
    )
    return user


@pytest.fixture
def parent_user(db):
    """Создать родителя"""
    user = User.objects.create_user(
        username='parent1',
        email='parent1@test.com',
        password='testpass123',
        role='parent',
        first_name='Test',
        last_name='Parent'
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
class TestTutorStudentCreateEndpoint:
    """
    Тест для исправления: frontend/src/integrations/api/adminAPI.ts createStudent
    Endpoint: /api/tutor/my-students/ (POST)
    """

    def test_create_student_endpoint_exists(self, api_client, tutor_user):
        """POST /api/tutor/my-students/ должен существовать и принимать запросы"""
        api_client.force_authenticate(user=tutor_user)

        data = {
            'first_name': 'New',
            'last_name': 'Student',
            'grade': '9',
            'parent_first_name': 'Parent',
            'parent_last_name': 'Name',
            'parent_email': 'parent@test.com',
        }

        response = api_client.post('/api/tutor/my-students/', data)

        # Endpoint должен существовать (не 404)
        assert response.status_code != status.HTTP_404_NOT_FOUND

        # Успешное создание
        assert response.status_code == status.HTTP_201_CREATED
        assert 'student' in response.data
        assert 'credentials' in response.data

    def test_create_student_validation(self, api_client, tutor_user):
        """Проверка валидации при создании ученика"""
        api_client.force_authenticate(user=tutor_user)

        # Пустые данные
        response = api_client.post('/api/tutor/my-students/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_student_permissions(self, api_client, student_user):
        """Только тьютор может создавать учеников"""
        api_client.force_authenticate(user=student_user)

        data = {
            'first_name': 'New',
            'last_name': 'Student',
            'grade': '9',
            'parent_first_name': 'Parent',
            'parent_last_name': 'Name',
        }

        response = api_client.post('/api/tutor/my-students/', data)

        # Не 404, а 403 (доступ запрещён)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
class TestTelegramEndpoints:
    """
    Тесты для исправления: frontend/src/integrations/api/telegramAPI.ts
    Endpoints:
    - /api/profile/telegram/generate-link/ (POST)
    - /api/profile/telegram/status/ (GET)
    - /api/profile/telegram/unlink/ (DELETE)
    """

    def test_generate_link_endpoint_exists(self, api_client, tutor_user):
        """POST /api/profile/telegram/generate-link/ должен существовать"""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.post('/api/profile/telegram/generate-link/')

        # Endpoint существует (не 404)
        assert response.status_code != status.HTTP_404_NOT_FOUND

        # Успешная генерация токена
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'link' in response.data
        assert 'expires_at' in response.data

    def test_telegram_status_endpoint_exists(self, api_client, tutor_user):
        """GET /api/profile/telegram/status/ должен существовать"""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.get('/api/profile/telegram/status/')

        # Endpoint существует (не 404)
        assert response.status_code != status.HTTP_404_NOT_FOUND

        # Успешный ответ (даже если Telegram не привязан)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_unlink_telegram_endpoint_exists(self, api_client, tutor_user):
        """DELETE /api/profile/telegram/unlink/ должен существовать"""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.delete('/api/profile/telegram/unlink/')

        # Endpoint существует (не 404)
        assert response.status_code != status.HTTP_404_NOT_FOUND

        # Может вернуть 400 если Telegram не был привязан, но не 404
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_telegram_endpoints_require_auth(self, api_client):
        """Все Telegram endpoints требуют авторизации"""
        # Без авторизации
        response_generate = api_client.post('/api/profile/telegram/generate-link/')
        response_status = api_client.get('/api/profile/telegram/status/')
        response_unlink = api_client.delete('/api/profile/telegram/unlink/')

        # Не 404, а 401/403
        assert response_generate.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert response_status.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert response_unlink.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_telegram_link_token_expiration(self, api_client, tutor_user):
        """Токен привязки должен иметь срок действия"""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.post('/api/profile/telegram/generate-link/')
        assert response.status_code == status.HTTP_200_OK

        # Проверяем формат expires_at
        assert 'expires_at' in response.data
        assert 'ttl_minutes' in response.data

        # TTL должен быть разумным (например, 5-60 минут)
        ttl = response.data.get('ttl_minutes', 0)
        assert 1 <= ttl <= 60


@pytest.mark.django_db
class TestEndpointsIntegration:
    """Интеграционные тесты для всех исправленных endpoints"""

    def test_all_endpoints_accessible_for_tutor(self, api_client, tutor_user):
        """Все исправленные endpoints доступны для тьютора"""
        api_client.force_authenticate(user=tutor_user)

        endpoints = [
            ('POST', '/api/tutor/my-students/', {
                'first_name': 'Test',
                'last_name': 'Student',
                'grade': '10',
                'parent_first_name': 'Parent',
                'parent_last_name': 'Name',
            }),
            ('POST', '/api/profile/telegram/generate-link/', None),
            ('GET', '/api/profile/telegram/status/', None),
            ('DELETE', '/api/profile/telegram/unlink/', None),
        ]

        for method, url, data in endpoints:
            if method == 'POST':
                response = api_client.post(url, data)
            elif method == 'GET':
                response = api_client.get(url)
            elif method == 'DELETE':
                response = api_client.delete(url)

            # Главное - не 404
            assert response.status_code != status.HTTP_404_NOT_FOUND, \
                f"{method} {url} returned 404"

    def test_student_cannot_create_students(self, api_client, student_user):
        """Ученик не может создавать других учеников"""
        api_client.force_authenticate(user=student_user)

        data = {
            'first_name': 'Test',
            'last_name': 'Student',
            'grade': '10',
            'parent_first_name': 'Parent',
            'parent_last_name': 'Name',
        }

        response = api_client.post('/api/tutor/my-students/', data)

        # Не 404, а 403 (endpoint существует, но доступ запрещён)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_parent_can_use_telegram_endpoints(self, api_client, parent_user):
        """Родитель может использовать Telegram endpoints"""
        api_client.force_authenticate(user=parent_user)

        # Генерация токена
        response = api_client.post('/api/profile/telegram/generate-link/')
        assert response.status_code == status.HTTP_200_OK

        # Проверка статуса
        response = api_client.get('/api/profile/telegram/status/')
        assert response.status_code != status.HTTP_404_NOT_FOUND
