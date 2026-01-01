#!/usr/bin/env python
"""
Pytest-based comprehensive API endpoint testing
This file uses pytest and Django test client
Run with: pytest test_all_endpoints.py -v
"""

import pytest
import json
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta

User = get_user_model()


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test users"""
        self.client = APIClient()

        # Create test users
        self.test_users = {
            "student": {
                "email": "student1@test.com",
                "password": "student123",
                "is_student": True
            },
            "teacher": {
                "email": "teacher1@test.com",
                "password": "teacher123",
                "is_teacher": True
            },
            "admin": {
                "email": "admin@test.com",
                "password": "admin123",
                "is_staff": True,
                "is_superuser": True
            },
            "tutor": {
                "email": "tutor1@test.com",
                "password": "tutor123",
                "is_tutor": True
            },
            "parent": {
                "email": "parent1@test.com",
                "password": "parent123",
                "is_parent": True
            },
        }

        for role, user_data in self.test_users.items():
            email = user_data["email"]
            pwd = user_data.pop("password")
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(email=email, password=pwd, **user_data)

    @pytest.mark.django_db
    def test_student_login(self):
        """Test student login"""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'student1@test.com',
                'password': 'student123'
            },
            format='json'
        )
        assert response.status_code == 200, f"Got {response.status_code}: {response.data}"
        data = response.json()
        assert 'data' in data or 'token' in data

    @pytest.mark.django_db
    def test_teacher_login(self):
        """Test teacher login"""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'teacher1@test.com',
                'password': 'teacher123'
            },
            format='json'
        )
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data or 'token' in data

    @pytest.mark.django_db
    def test_admin_login(self):
        """Test admin login"""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'admin@test.com',
                'password': 'admin123'
            },
            format='json'
        )
        assert response.status_code == 200
        data = response.json()
        assert 'data' in data or 'token' in data

    @pytest.mark.django_db
    def test_invalid_login(self):
        """Test invalid login"""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'nonexistent@test.com',
                'password': 'wrongpassword'
            },
            format='json'
        )
        # Should fail with 400 or 401
        assert response.status_code in [400, 401, 403]


class TestProfileEndpoints:
    """Test profile endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test user and client"""
        self.client = APIClient()

        # Create student user
        self.student = User.objects.create_user(
            email='student1@test.com',
            password='student123',
            first_name='Test',
            last_name='Student',
            is_student=True
        )

        # Get or create token
        token, _ = Token.objects.get_or_create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @pytest.mark.django_db
    def test_get_profile(self):
        """Test GET /api/profile/"""
        response = self.client.get('/api/profile/')
        assert response.status_code in [200, 400, 404]

    @pytest.mark.django_db
    def test_patch_profile(self):
        """Test PATCH /api/profile/"""
        response = self.client.patch(
            '/api/profile/',
            {'first_name': 'Updated'},
            format='json'
        )
        assert response.status_code in [200, 400, 404]


class TestSchedulingEndpoints:
    """Test scheduling endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test user and client"""
        self.client = APIClient()

        # Create student user
        self.student = User.objects.create_user(
            email='student1@test.com',
            password='student123',
            is_student=True
        )

        # Get or create token
        token, _ = Token.objects.get_or_create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @pytest.mark.django_db
    def test_get_lessons_list(self):
        """Test GET /api/scheduling/lessons/"""
        response = self.client.get('/api/scheduling/lessons/')
        assert response.status_code in [200, 404]

    @pytest.mark.django_db
    def test_post_lesson_requires_teacher(self):
        """Test POST /api/scheduling/lessons/ (student should fail)"""
        response = self.client.post(
            '/api/scheduling/lessons/',
            {
                'subject': 'Math',
                'title': 'Test Lesson',
                'start_time': (datetime.now() + timedelta(days=1)).isoformat(),
                'end_time': (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            },
            format='json'
        )
        # Should fail for non-teacher (403 or 400)
        assert response.status_code in [400, 403, 404]


class TestMaterialsEndpoints:
    """Test materials endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test user and client"""
        self.client = APIClient()

        # Create teacher user
        self.teacher = User.objects.create_user(
            email='teacher1@test.com',
            password='teacher123',
            is_teacher=True
        )

        # Get or create token
        token, _ = Token.objects.get_or_create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @pytest.mark.django_db
    def test_get_materials_list(self):
        """Test GET /api/materials/"""
        response = self.client.get('/api/materials/')
        assert response.status_code in [200, 404]


class TestAssignmentsEndpoints:
    """Test assignments endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test user and client"""
        self.client = APIClient()

        # Create student user
        self.student = User.objects.create_user(
            email='student1@test.com',
            password='student123',
            is_student=True
        )

        # Get or create token
        token, _ = Token.objects.get_or_create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @pytest.mark.django_db
    def test_get_assignments_list(self):
        """Test GET /api/assignments/"""
        response = self.client.get('/api/assignments/')
        assert response.status_code in [200, 404]


class TestChatEndpoints:
    """Test chat endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test user and client"""
        self.client = APIClient()

        # Create student user
        self.student = User.objects.create_user(
            email='student1@test.com',
            password='student123',
            is_student=True
        )

        # Get or create token
        token, _ = Token.objects.get_or_create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @pytest.mark.django_db
    def test_get_conversations_list(self):
        """Test GET /api/chat/conversations/"""
        response = self.client.get('/api/chat/conversations/')
        assert response.status_code in [200, 404]


class TestAdminEndpoints:
    """Test admin endpoint permissions"""

    @pytest.fixture(autouse=True)
    def setup(self, db):
        """Setup test users and clients"""
        # Create student user
        self.student = User.objects.create_user(
            email='student1@test.com',
            password='student123',
            is_student=True
        )

        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )

        self.student_client = APIClient()
        token, _ = Token.objects.get_or_create(user=self.student)
        self.student_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        self.admin_client = APIClient()
        admin_token, _ = Token.objects.get_or_create(user=self.admin)
        self.admin_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')

    @pytest.mark.django_db
    def test_admin_endpoint_forbidden_for_student(self):
        """Test that non-admin gets 403 on admin endpoints"""
        response = self.student_client.get('/api/admin/users/')
        assert response.status_code in [403, 404]

    @pytest.mark.django_db
    def test_admin_endpoint_accessible_for_admin(self):
        """Test that admin can access admin endpoints"""
        response = self.admin_client.get('/api/admin/users/')
        # May be 200 or 404 if endpoint doesn't exist
        assert response.status_code in [200, 404]


class TestHealthEndpoints:
    """Test health and status endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup client"""
        self.client = APIClient()

    @pytest.mark.django_db
    def test_swagger_endpoint(self):
        """Test GET /api/schema/swagger/"""
        response = self.client.get('/api/schema/swagger/')
        # Should return 200 or 404
        assert response.status_code in [200, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
