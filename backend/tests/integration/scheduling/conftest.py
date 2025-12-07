"""
Fixtures for integration tests of scheduling app - Lesson model.

Imports fixtures from unit test conftest to share them.
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from accounts.models import User, StudentProfile, TeacherProfile, TutorProfile
from materials.models import Subject, SubjectEnrollment
from scheduling.models import Lesson, LessonHistory


@pytest.fixture
def teacher_user(db):
    """Create a teacher user with TeacherProfile for testing."""
    user = User.objects.create_user(
        username='test_teacher@test.com',
        email='test_teacher@test.com',
        password='TestPass123!',
        first_name='Test',
        last_name='Teacher',
        role='teacher'
    )
    TeacherProfile.objects.create(user=user)
    return user


@pytest.fixture
def student_user(db):
    """Create a student user with StudentProfile for testing."""
    user = User.objects.create_user(
        username='test_student@test.com',
        email='test_student@test.com',
        password='TestPass123!',
        first_name='Test',
        last_name='Student',
        role='student'
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def tutor_user(db):
    """Create a tutor user with TutorProfile for testing."""
    user = User.objects.create_user(
        username='test_tutor@test.com',
        email='test_tutor@test.com',
        password='TestPass123!',
        first_name='Test',
        last_name='Tutor',
        role='tutor'
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user(db):
    """Create a parent user for testing."""
    from accounts.models import ParentProfile
    user = User.objects.create_user(
        username='test_parent@test.com',
        email='test_parent@test.com',
        password='TestPass123!',
        first_name='Test',
        last_name='Parent',
        role='parent'
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def another_teacher_user(db):
    """Create another teacher for testing multiple teachers."""
    user = User.objects.create_user(
        username='another_teacher@test.com',
        email='another_teacher@test.com',
        password='TestPass123!',
        first_name='Another',
        last_name='Teacher',
        role='teacher'
    )
    TeacherProfile.objects.create(user=user)
    return user


@pytest.fixture
def another_student_user(db):
    """Create another student for testing multiple students."""
    user = User.objects.create_user(
        username='another_student@test.com',
        email='another_student@test.com',
        password='TestPass123!',
        first_name='Another',
        last_name='Student',
        role='student'
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def math_subject(db):
    """Create a test subject."""
    return Subject.objects.create(
        name='Математика',
        description='Тестовый предмет математика'
    )


@pytest.fixture
def english_subject(db):
    """Create another test subject."""
    return Subject.objects.create(
        name='Английский язык',
        description='Тестовый предмет английский'
    )


@pytest.fixture
def subject_enrollment(db, student_user, teacher_user, math_subject):
    """Create an active SubjectEnrollment linking teacher to student."""
    return SubjectEnrollment.objects.create(
        student=student_user,
        teacher=teacher_user,
        subject=math_subject,
        is_active=True
    )


@pytest.fixture
def another_enrollment(db, another_student_user, teacher_user, english_subject):
    """Create another SubjectEnrollment for different student."""
    return SubjectEnrollment.objects.create(
        student=another_student_user,
        teacher=teacher_user,
        subject=english_subject,
        is_active=True
    )


@pytest.fixture
def lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a test lesson for future date."""
    future_date = timezone.now().date() + timedelta(days=3)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=future_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        description='Алгебра для 8 класса',
        telemost_link='https://telemost.yandex.ru/test',
        status='pending'
    )


@pytest.fixture
def confirmed_lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a confirmed lesson."""
    future_date = timezone.now().date() + timedelta(days=5)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=future_date,
        start_time=time(14, 0),
        end_time=time(15, 0),
        description='Геометрия',
        status='confirmed'
    )


@pytest.fixture
def past_lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a lesson in the past."""
    past_date = timezone.now().date() - timedelta(days=5)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=past_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        description='Прошлый урок',
        status='completed'
    )


@pytest.fixture
def near_future_lesson(db, teacher_user, student_user, math_subject, subject_enrollment):
    """Create a lesson that is less than 2 hours away."""
    near_future = timezone.now() + timedelta(minutes=30)
    return Lesson.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=math_subject,
        date=near_future.date(),
        start_time=near_future.time(),
        end_time=(near_future + timedelta(hours=1)).time(),
        description='Урок через 30 минут',
        status='confirmed'
    )
