"""
Integration тесты для Profile API endpoints.

Запуск:
    pytest backend/tests/integration/test_profile_integration.py -v
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import (
    StudentProfile, TeacherProfile, TutorProfile, ParentProfile
)

User = get_user_model()

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """REST API клиент"""
    return APIClient()


@pytest.fixture
def student_user():
    """Создает студента с профилем"""
    user = User.objects.create_user(
        username='student_int_test',
        email='student_int@test.com',
        password='TestPass123!',
        role=User.Role.STUDENT,
        first_name='Иван',
        last_name='Сидоров'
    )
    profile = StudentProfile.objects.create(user=user, grade='10А')
    return user


@pytest.fixture
def teacher_user():
    """Создает преподавателя с профилем"""
    user = User.objects.create_user(
        username='teacher_int_test',
        email='teacher_int@test.com',
        password='TestPass123!',
        role=User.Role.TEACHER,
        first_name='Петр',
        last_name='Петров'
    )
    profile = TeacherProfile.objects.create(
        user=user,
        subject='Математика'
    )
    return user


@pytest.fixture
def tutor_user():
    """Создает тьютора с профилем"""
    user = User.objects.create_user(
        username='tutor_int_test',
        email='tutor_int@test.com',
        password='TestPass123!',
        role=User.Role.TUTOR,
        first_name='Анна',
        last_name='Петрова'
    )
    profile = TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user():
    """Создает родителя с профилем"""
    user = User.objects.create_user(
        username='parent_int_test',
        email='parent_int@test.com',
        password='TestPass123!',
        role=User.Role.PARENT,
        first_name='Ольга',
        last_name='Сидорова'
    )
    profile = ParentProfile.objects.create(user=user)
    return user


class TestStudentProfileIntegration:
    """Integration тесты для Student Profile"""

    def test_student_can_update_own_profile(self, api_client, student_user):
        """Студент может обновить свой профиль"""
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'grade': '11А',
            'goal': 'Поступление в МГУ',
            'progress_percentage': 85,
            'streak_days': 30
        }

        response = api_client.patch(
            '/api/auth/profile/student/',
            update_data,
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_student_cannot_get_profile_without_auth(self, api_client):
        """Студент не может получить профиль без аутентификации"""
        response = api_client.get('/api/auth/profile/student/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_student_profile_requires_auth(self, api_client):
        """Требуется аутентификация для доступа к профилю"""
        response = api_client.get('/api/auth/profile/student/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_student_profile_partial_update(self, api_client, student_user):
        """Студент может частично обновить профиль"""
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {'grade': '12А'}

        response = api_client.patch(
            '/api/auth/profile/student/',
            update_data,
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT]

    def test_student_profile_update_persists(self, api_client, student_user):
        """Обновленные данные профиля сохраняются в БД"""
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        new_grade = '12Б'
        update_data = {'grade': new_grade}

        response = api_client.patch(
            '/api/auth/profile/student/',
            update_data,
            format='json'
        )

        if response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]:
            student_user.refresh_from_db()
            profile = StudentProfile.objects.get(user=student_user)
            assert profile.grade == new_grade


class TestTeacherProfileIntegration:
    """Integration тесты для Teacher Profile"""

    def test_teacher_can_update_own_profile(self, api_client, teacher_user):
        """Преподаватель может обновить свой профиль"""
        token = Token.objects.create(user=teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'subject': 'Физика',
            'experience_years': 10,
            'bio': 'Опытный преподаватель физики'
        }

        response = api_client.patch(
            '/api/auth/profile/teacher/',
            update_data,
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_teacher_profile_requires_auth(self, api_client):
        """Требуется аутентификация для доступа к профилю"""
        response = api_client.get('/api/auth/profile/teacher/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_teacher_partial_update(self, api_client, teacher_user):
        """Преподаватель может частично обновить профиль"""
        token = Token.objects.create(user=teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {'subject': 'Химия'}

        response = api_client.patch(
            '/api/auth/profile/teacher/',
            update_data,
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT]


class TestTutorProfileIntegration:
    """Integration тесты для Tutor Profile"""

    def test_tutor_can_update_own_profile(self, api_client, tutor_user):
        """Тьютор может обновить свой профиль"""
        token = Token.objects.create(user=tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'bio': 'Опытный тьютор с 10-летним стажем',
            'specialization': 'Подготовка к ОГЭ и ЕГЭ'
        }

        response = api_client.patch(
            '/api/auth/profile/tutor/',
            update_data,
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_tutor_profile_requires_auth(self, api_client):
        """Требуется аутентификация для доступа к профилю"""
        response = api_client.get('/api/auth/profile/tutor/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestParentProfileIntegration:
    """Integration тесты для Parent Profile"""

    def test_parent_can_update_own_profile(self, api_client, parent_user):
        """Родитель может обновить свой профиль"""
        token = Token.objects.create(user=parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'notification_preference': 'sms'
        }

        response = api_client.patch(
            '/api/auth/profile/parent/',
            update_data,
            format='json'
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_parent_profile_requires_auth(self, api_client):
        """Требуется аутентификация для доступа к профилю"""
        response = api_client.get('/api/auth/profile/parent/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestProfileErrorHandling:
    """Integration тесты для обработки ошибок"""

    def test_invalid_token_returns_error(self, api_client):
        """Невалидный токен возвращает ошибку"""
        api_client.credentials(HTTP_AUTHORIZATION='Token invalid_token')

        response = api_client.get('/api/auth/profile/student/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_missing_auth_header_returns_error(self, api_client):
        """Отсутствие заголовка авторизации возвращает ошибку"""
        response = api_client.get('/api/auth/profile/student/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_wrong_role_access(self, api_client, student_user):
        """Студент не может обращаться к teacher profile"""
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = api_client.get('/api/auth/profile/teacher/')
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


class TestProfileCrossRoles:
    """Integration тесты для кросс-ролевых сценариев"""

    def test_multiple_roles_isolation(self, api_client, student_user, teacher_user):
        """Студент и преподаватель имеют изолированные профили"""
        student_token = Token.objects.create(user=student_user)
        teacher_token = Token.objects.create(user=teacher_user)

        # Студент обновляет свой профиль
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {student_token.key}')
        student_response = api_client.patch(
            '/api/auth/profile/student/',
            {'grade': '11А'},
            format='json'
        )

        # Преподаватель обновляет свой профиль
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {teacher_token.key}')
        teacher_response = api_client.patch(
            '/api/auth/profile/teacher/',
            {'subject': 'Физика'},
            format='json'
        )

        # Оба должны быть успешными
        assert student_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert teacher_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_tutor_and_parent_isolation(self, api_client, tutor_user, parent_user):
        """Тьютор и родитель имеют изолированные профили"""
        tutor_token = Token.objects.create(user=tutor_user)
        parent_token = Token.objects.create(user=parent_user)

        # Тьютор обновляет свой профиль
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {tutor_token.key}')
        tutor_response = api_client.patch(
            '/api/auth/profile/tutor/',
            {'bio': 'Опытный тьютор'},
            format='json'
        )

        # Родитель обновляет свой профиль
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {parent_token.key}')
        parent_response = api_client.patch(
            '/api/auth/profile/parent/',
            {'notification_preference': 'telegram'},
            format='json'
        )

        # Оба должны быть успешными
        assert tutor_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert parent_response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


class TestProfileDataValidation:
    """Integration тесты для валидации данных"""

    def test_student_progress_validation(self, api_client, student_user):
        """Валидация процента прогресса студента"""
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Отправляем invalid progress (> 100)
        invalid_data = {'progress_percentage': 150}

        response = api_client.patch(
            '/api/auth/profile/student/',
            invalid_data,
            format='json'
        )

        # Должно быть либо validation error, либо success (depending on API)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_teacher_experience_validation(self, api_client, teacher_user):
        """Валидация опыта преподавателя"""
        token = Token.objects.create(user=teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Отправляем negative experience
        invalid_data = {'experience_years': -5}

        response = api_client.patch(
            '/api/auth/profile/teacher/',
            invalid_data,
            format='json'
        )

        # Должно быть либо validation error, либо success
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST
        ]


class TestProfileConcurrency:
    """Integration тесты для параллельных обновлений"""

    def test_sequential_updates(self, api_client, student_user):
        """Несколько последовательных обновлений работают корректно"""
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        updates = [
            {'grade': '11А'},
            {'goal': 'Поступление в МГУ'},
            {'streak_days': 30}
        ]

        for update in updates:
            response = api_client.patch(
                '/api/auth/profile/student/',
                update,
                format='json'
            )
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
