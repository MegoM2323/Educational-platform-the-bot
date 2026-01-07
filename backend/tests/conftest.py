import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Setup Django before importing any Django modules
if not settings.configured:
    django.setup()

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from playwright.sync_api import sync_playwright

from materials.models import Subject, Material, SubjectEnrollment, TeacherSubject
from accounts.models import TeacherProfile, StudentProfile, TutorProfile, ParentProfile
from scheduling.models import Lesson

User = get_user_model()


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database"""
    pass


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    user = User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="admin123secure",
        first_name="Admin",
        last_name="User",
        role=User.Role.ADMIN,
    )
    return user


@pytest.fixture
def teacher_user(db):
    """Create teacher user with profile"""
    user = User.objects.create_user(
        username="teacher1",
        email="teacher1@test.com",
        password="teacher123secure",
        first_name="John",
        last_name="Teacher",
        role=User.Role.TEACHER,
        is_active=True,
    )
    TeacherProfile.objects.create(
        user=user,
        subject="Mathematics",
        experience_years=5,
        bio="Experienced math teacher",
    )
    return user


@pytest.fixture
def teacher_user_2(db):
    """Create second teacher user for access control tests"""
    user = User.objects.create_user(
        username="teacher2",
        email="teacher2@test.com",
        password="teacher456secure",
        first_name="Jane",
        last_name="Educator",
        role=User.Role.TEACHER,
        is_active=True,
    )
    TeacherProfile.objects.create(
        user=user,
        subject="English",
        experience_years=3,
        bio="English language specialist",
    )
    return user


@pytest.fixture
def student_user(db):
    """Create student user with profile"""
    user = User.objects.create_user(
        username="student1",
        email="student1@test.com",
        password="student123secure",
        first_name="Alice",
        last_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(
        user=user,
        grade=10,
        goal="Pass the exam",
    )
    return user


@pytest.fixture
def student_user_2(db):
    """Create second student for various tests"""
    user = User.objects.create_user(
        username="student2",
        email="student2@test.com",
        password="student456secure",
        first_name="Bob",
        last_name="Learner",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(
        user=user,
        grade=9,
        goal="Improve grades",
    )
    return user


@pytest.fixture
def parent_user(db):
    """Create parent user with profile"""
    user = User.objects.create_user(
        username="parent1",
        email="parent1@test.com",
        password="parent123secure",
        first_name="John",
        last_name="Parent",
        role=User.Role.PARENT,
        is_active=True,
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def tutor_user(db):
    """Create tutor user"""
    user = User.objects.create_user(
        username="tutor1",
        email="tutor1@test.com",
        password="tutor123secure",
        first_name="Tom",
        last_name="Tutor",
        role=User.Role.TUTOR,
        is_active=True,
    )
    return user


@pytest.fixture
def subject_math(db):
    """Create Mathematics subject"""
    return Subject.objects.create(
        name="Mathematics",
        description="Basic mathematics course",
        color="#FF5733",
    )


@pytest.fixture
def subject_english(db):
    """Create English subject"""
    return Subject.objects.create(
        name="English",
        description="English language and literature",
        color="#33FF57",
    )


@pytest.fixture
def teacher_subject_math(db, teacher_user, subject_math):
    """Create TeacherSubject relationship for teacher and math"""
    return TeacherSubject.objects.create(
        teacher=teacher_user,
        subject=subject_math,
        is_active=True,
    )


@pytest.fixture
def teacher_subject_english(db, teacher_user_2, subject_english):
    """Create TeacherSubject relationship for teacher_2 and english"""
    return TeacherSubject.objects.create(
        teacher=teacher_user_2,
        subject=subject_english,
        is_active=True,
    )


@pytest.fixture
def material_math(db, teacher_user, subject_math):
    """Create material for math subject"""
    return Material.objects.create(
        title="Algebra Basics",
        description="Introduction to algebra",
        content="Algebra is the branch of mathematics...",
        author=teacher_user,
        subject=subject_math,
        type=Material.Type.LESSON,
        status=Material.Status.ACTIVE,
        is_public=False,
        difficulty_level=2,
    )


@pytest.fixture
def material_english(db, teacher_user_2, subject_english):
    """Create material for english subject"""
    return Material.objects.create(
        title="Shakespeare's Sonnets",
        description="Analysis of Shakespeare's sonnets",
        content="Shakespeare's sonnets are a collection of 154 poems...",
        author=teacher_user_2,
        subject=subject_english,
        type=Material.Type.DOCUMENT,
        status=Material.Status.DRAFT,
        is_public=False,
        difficulty_level=3,
    )


@pytest.fixture
def subject_enrollment(db, student_user, subject_math, teacher_user):
    """Create subject enrollment"""
    return SubjectEnrollment.objects.create(
        student=student_user,
        subject=subject_math,
        teacher=teacher_user,
        is_active=True,
    )


@pytest.fixture
def lesson_fixture(db, student_user, teacher_user):
    """Create lesson for testing"""
    return Lesson.objects.create(
        student=student_user,
        teacher=teacher_user,
        date="2026-01-07",
        start_time="10:00:00",
        end_time="11:00:00",
    )


@pytest.fixture
def authenticated_client(api_client, teacher_user):
    """Create API client authenticated as teacher"""
    refresh = RefreshToken.for_user(teacher_user)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authenticated_client_2(api_client, teacher_user_2):
    """Create API client authenticated as second teacher"""
    refresh = RefreshToken.for_user(teacher_user_2)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authenticated_student_client(api_client, student_user):
    """Create API client authenticated as student"""
    refresh = RefreshToken.for_user(student_user)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authenticated_tutor_client(api_client, tutor_user):
    """Create API client authenticated as tutor"""
    refresh = RefreshToken.for_user(tutor_user)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """Create API client authenticated as admin"""
    refresh = RefreshToken.for_user(admin_user)
    token = str(refresh.access_token)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture(scope="function")
def browser():
    """Fixture providing a Playwright browser instance for E2E tests"""
    with sync_playwright() as p:
        browser_instance = p.chromium.launch(headless=True)
        yield browser_instance
        browser_instance.close()
