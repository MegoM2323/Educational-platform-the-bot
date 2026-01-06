"""
Conftest fixtures for tutor cabinet tests
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def tutor_user(db):
    """Create a tutor user"""
    User = get_user_model()
    return User.objects.create_user(
        username='tutor_user',
        email='tutor@example.com',
        password='testpass123',
        first_name='John',
        last_name='Tutor'
    )


@pytest.fixture
def authenticated_client(tutor_user):
    """Create authenticated API client for tutor"""
    client = APIClient()
    client.force_authenticate(user=tutor_user)
    return client


@pytest.fixture
def tutor_students(db):
    """Create students for tutor"""
    User = get_user_model()
    students = []
    for i in range(5):
        student = User.objects.create_user(
            username=f'student_{i}',
            email=f'student_{i}@example.com',
            password='testpass123',
            first_name=f'Student_{i}',
            last_name=f'User_{i}'
        )
        students.append(student)

    return students
