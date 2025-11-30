"""
Mini integration тесты для Profile ViewSets API endpoints.
"""

import pytest
from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture для REST API клиента"""
    return APIClient()


def create_test_image():
    """Создать тестовое изображение"""
    image = Image.new('RGB', (400, 400), color='red')
    image_io = BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)
    return SimpleUploadedFile(
        'test_avatar.png',
        image_io.getvalue(),
        content_type='image/png'
    )


@pytest.mark.django_db
class TestStudentProfileViewSet:
    """Базовые тесты для StudentProfileViewSet"""

    def test_student_can_get_own_profile(self, api_client):
        """Студент может получить свой профиль"""
        user = User.objects.create_user(
            username='test_student',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Иван'
        )
        profile = StudentProfile.objects.create(user=user, grade='10А')
        
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/auth/profile/student/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['grade'] == '10А'

    def test_student_can_update_own_profile(self, api_client):
        """Студент может обновить свой профиль"""
        user = User.objects.create_user(
            username='test_student',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        profile = StudentProfile.objects.create(user=user, grade='10А')

        api_client.force_authenticate(user=user)
        response = api_client.patch('/api/auth/profile/student/me/', {
            'grade': '11A',
            'goal': 'Learn math'
        })

        assert response.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.grade == '11A'

    def test_unauthenticated_cannot_get_profile(self, api_client):
        """Неавторизованный пользователь не может получить профиль"""
        response = api_client.get('/api/auth/profile/student/me/')
        # DRF returns 403 for AnonymousUser when permission denied
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_cannot_list_all_profiles(self, api_client):
        """Нельзя получить список всех профилей"""
        user = User.objects.create_user(
            username='test_student',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/auth/profile/student/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTeacherProfileViewSet:
    """Базовые тесты для TeacherProfileViewSet"""

    def test_teacher_can_get_own_profile(self, api_client):
        """Преподаватель может получить свой профиль"""
        user = User.objects.create_user(
            username='test_teacher',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        profile = TeacherProfile.objects.create(user=user, subject='Math', experience_years=5)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/auth/profile/teacher/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['subject'] == 'Math'

    def test_teacher_can_update_own_profile(self, api_client):
        """Преподаватель может обновить свой профиль"""
        user = User.objects.create_user(
            username='test_teacher',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        profile = TeacherProfile.objects.create(user=user, subject='Math', experience_years=5)

        api_client.force_authenticate(user=user)
        response = api_client.patch('/api/auth/profile/teacher/me/', {
            'experience_years': 6
        })

        assert response.status_code == status.HTTP_200_OK
        profile.refresh_from_db()
        assert profile.experience_years == 6
