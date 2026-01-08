import pytest
import django
from django.conf import settings
from rest_framework.test import APIClient
from accounts.factories import (
    StudentFactory,
    TeacherFactory,
    TutorFactory,
    ParentFactory,
    StudentProfileFactory,
    TeacherProfileFactory,
    TutorProfileFactory,
    ParentProfileFactory,
    UserFactory,
)

@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database"""
    pass


@pytest.fixture
def student_user(db):
    """Create a student user for testing"""
    return StudentFactory()


@pytest.fixture
def teacher_user(db):
    """Create a teacher user for testing"""
    return TeacherFactory()


@pytest.fixture
def tutor_user(db):
    """Create a tutor user for testing"""
    return TutorFactory()


@pytest.fixture
def parent_user(db):
    """Create a parent user for testing"""
    return ParentFactory()


@pytest.fixture
def student_profile(db):
    """Create a student profile for testing"""
    return StudentProfileFactory()


@pytest.fixture
def teacher_profile(db):
    """Create a teacher profile for testing"""
    return TeacherProfileFactory()


@pytest.fixture
def tutor_profile(db):
    """Create a tutor profile for testing"""
    return TutorProfileFactory()


@pytest.fixture
def parent_profile(db):
    """Create a parent profile for testing"""
    return ParentProfileFactory()


@pytest.fixture
def api_client(db):
    """Create an API client for testing"""
    return APIClient()
