"""
Тест проверки прав доступа админа vs неавторизованного пользователя.

Тестирует что только админ может обращаться к admin endpoints:
1. Без авторизации - 401 Unauthorized
2. С токеном обычного учителя - 403 Forbidden
3. С токеном обычного студента - 403 Forbidden
4. С токеном админа - 200 OK
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from materials.models import Subject, SubjectEnrollment, TeacherSubject
from scheduling.models import Lesson
from accounts.models import TeacherProfile, StudentProfile

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    user = User.objects.create_superuser(
        username="admin_access_test",
        email="admin_access@test.com",
        password="admin123secure",
        first_name="Admin",
        last_name="AccessTest",
        role=User.Role.ADMIN,
    )
    return user


@pytest.fixture
def teacher_user(db):
    """Create regular teacher (not admin)"""
    user = User.objects.create_user(
        username="teacher_access_test",
        email="teacher_access@test.com",
        password="teacher123",
        first_name="Ivan",
        last_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    TeacherProfile.objects.create(
        user=user,
        subject="Mathematics",
        experience_years=5,
        bio="Math teacher",
    )
    return user


@pytest.fixture
def student_user(db):
    """Create regular student (not admin)"""
    user = User.objects.create_user(
        username="student_access_test",
        email="student_access@test.com",
        password="student123",
        first_name="Alex",
        last_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(
        user=user,
        grade=10,
    )
    return user


@pytest.fixture
def subject(db):
    """Create test subject"""
    return Subject.objects.create(
        name="Mathematics",
        description="Math subject",
    )


class TestAdminVsNonAdminAccess:
    """Test access control for admin endpoints"""

    def test_admin_users_list_without_auth(self):
        """Test /api/admin/users/ without authentication returns 401"""
        client = APIClient()
        response = client.get('/api/admin/users/')

        assert response.status_code == 401

    def test_admin_users_list_with_teacher_token(self, teacher_user):
        """Test /api/admin/users/ with teacher token returns 403"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/admin/users/')

        assert response.status_code == 403

    def test_admin_users_list_with_student_token(self, student_user):
        """Test /api/admin/users/ with student token returns 403"""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/admin/users/')

        assert response.status_code == 403

    def test_admin_users_list_with_admin_token(self, admin_user):
        """Test /api/admin/users/ with admin token returns 200"""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get('/api/admin/users/')

        assert response.status_code == 200

    def test_admin_schedule_lessons_without_auth(self):
        """Test /api/admin/schedule/lessons/ without authentication returns 401"""
        client = APIClient()
        response = client.get('/api/admin/schedule/lessons/')

        assert response.status_code == 401

    def test_admin_schedule_lessons_with_teacher_token(self, teacher_user):
        """Test /api/admin/schedule/lessons/ with teacher token returns 403"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/admin/schedule/lessons/')

        assert response.status_code == 403

    def test_admin_schedule_lessons_with_student_token(self, student_user):
        """Test /api/admin/schedule/lessons/ with student token returns 403"""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/admin/schedule/lessons/')

        assert response.status_code == 403

    def test_admin_schedule_lessons_with_admin_token(self, admin_user):
        """Test /api/admin/schedule/lessons/ with admin token returns 200"""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get('/api/admin/schedule/lessons/')

        assert response.status_code == 200

    def test_chat_admin_rooms_without_auth(self):
        """Test /api/chat/admin/rooms/ without authentication returns 401"""
        client = APIClient()
        response = client.get('/api/chat/admin/rooms/')

        assert response.status_code == 401

    def test_chat_admin_rooms_with_teacher_token(self, teacher_user):
        """Test /api/chat/admin/rooms/ with teacher token returns 403"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/chat/admin/rooms/')

        assert response.status_code == 403

    def test_chat_admin_rooms_with_student_token(self, student_user):
        """Test /api/chat/admin/rooms/ with student token returns 403"""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/chat/admin/rooms/')

        assert response.status_code == 403

    def test_chat_admin_rooms_with_admin_token(self, admin_user):
        """Test /api/chat/admin/rooms/ with admin token returns 200"""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get('/api/chat/admin/rooms/')

        assert response.status_code == 200


class TestMultipleAdminEndpoints:
    """Test multiple admin endpoints in sequence to ensure consistent access control"""

    def test_all_critical_endpoints_without_auth(self):
        """Test that all critical admin endpoints return 401 without auth"""
        client = APIClient()

        endpoints = [
            ('GET', '/api/admin/users/'),
            ('GET', '/api/admin/schedule/lessons/'),
            ('GET', '/api/chat/admin/rooms/'),
        ]

        for method, endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401

    def test_all_critical_endpoints_with_teacher_token(self, teacher_user):
        """Test that all critical admin endpoints return 403 with teacher token"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        endpoints = [
            ('GET', '/api/admin/users/'),
            ('GET', '/api/admin/schedule/lessons/'),
            ('GET', '/api/chat/admin/rooms/'),
        ]

        for method, endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 403

    def test_all_critical_endpoints_with_student_token(self, student_user):
        """Test that all critical admin endpoints return 403 with student token"""
        client = APIClient()
        client.force_authenticate(user=student_user)

        endpoints = [
            ('GET', '/api/admin/users/'),
            ('GET', '/api/admin/schedule/lessons/'),
            ('GET', '/api/chat/admin/rooms/'),
        ]

        for method, endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 403

    def test_all_critical_endpoints_with_admin_token(self, admin_user):
        """Test that all critical admin endpoints return 200 with admin token"""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        endpoints = [
            ('GET', '/api/admin/users/'),
            ('GET', '/api/admin/schedule/lessons/'),
            ('GET', '/api/chat/admin/rooms/'),
        ]

        for method, endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200


class TestEdgeCases:
    """Test edge cases for access control"""

    def test_empty_auth_returns_401(self):
        """Test that no auth returns 401"""
        client = APIClient()

        response = client.get('/api/admin/users/')

        assert response.status_code == 401
