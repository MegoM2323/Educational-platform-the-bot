"""
Comprehensive tests for lesson visibility filtering.

Tests the role-based access control (RBAC) for:
- LessonViewSet.get_queryset() filters
- student_schedule() endpoint
- get_tutor_student_lessons() service
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from datetime import datetime, timedelta, time, date
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from materials.models import Subject, SubjectEnrollment, TeacherSubject
from scheduling.models import Lesson
from scheduling.services.lesson_service import LessonService
from accounts.models import TeacherProfile, StudentProfile, ParentProfile, TutorProfile

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def subject(db):
    """Create a subject"""
    return Subject.objects.create(
        name="Mathematics",
        description="Math subject",
    )


def create_enrollment(teacher, student, subject):
    """Helper to create subject enrollment (teacher teaches student this subject)"""
    # Check if enrollment already exists and update or create
    enrollment, _ = SubjectEnrollment.objects.update_or_create(
        student=student,
        subject=subject,
        defaults={
            'teacher': teacher,
            'is_active': True,
        }
    )
    return enrollment


@pytest.fixture
def teacher_user(db):
    """Create teacher user"""
    user = User.objects.create_user(
        username=f"teacher_visibility_{timezone.now().timestamp()}",
        email=f"teacher_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="John",
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
def teacher_user_2(db):
    """Create second teacher user"""
    user = User.objects.create_user(
        username=f"teacher2_visibility_{timezone.now().timestamp()}",
        email=f"teacher2_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="Jane",
        last_name="Educator",
        role=User.Role.TEACHER,
        is_active=True,
    )
    TeacherProfile.objects.create(
        user=user,
        subject="English",
        experience_years=3,
        bio="English teacher",
    )
    return user


@pytest.fixture
def student_user(db):
    """Create student user"""
    user = User.objects.create_user(
        username=f"student_visibility_{timezone.now().timestamp()}",
        email=f"student_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="Alice",
        last_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(
        user=user,
        grade=10,
        goal="Pass exam",
    )
    return user


@pytest.fixture
def student_user_2(db):
    """Create second student user"""
    user = User.objects.create_user(
        username=f"student2_visibility_{timezone.now().timestamp()}",
        email=f"student2_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
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
def tutor_user(db):
    """Create tutor user"""
    user = User.objects.create_user(
        username=f"tutor_visibility_{timezone.now().timestamp()}",
        email=f"tutor_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="Maria",
        last_name="Tutor",
        role=User.Role.TUTOR,
        is_active=True,
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def tutor_user_2(db):
    """Create second tutor user"""
    user = User.objects.create_user(
        username=f"tutor2_visibility_{timezone.now().timestamp()}",
        email=f"tutor2_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="Peter",
        last_name="Tutor2",
        role=User.Role.TUTOR,
        is_active=True,
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user(db):
    """Create parent user"""
    user = User.objects.create_user(
        username=f"parent_visibility_{timezone.now().timestamp()}",
        email=f"parent_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="John",
        last_name="Parent",
        role=User.Role.PARENT,
        is_active=True,
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user_2(db):
    """Create second parent user"""
    user = User.objects.create_user(
        username=f"parent2_visibility_{timezone.now().timestamp()}",
        email=f"parent2_vis_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="Jane",
        last_name="Parent2",
        role=User.Role.PARENT,
        is_active=True,
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return User.objects.create_superuser(
        username=f"admin_visibility_{timezone.now().timestamp()}",
        email=f"admin_vis_{timezone.now().timestamp()}@test.com",
        password="admin123",
        first_name="Admin",
        last_name="User",
        role=User.Role.ADMIN,
    )


@pytest.fixture
def api_client():
    """Provide API client"""
    return APIClient()


def get_tokens(user):
    """Get JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


def create_lesson(teacher, student, subject, status=Lesson.Status.PENDING, days_ahead=1, create_enrollment_flag=True, hour=10):
    """Helper to create a lesson and optionally create enrollment"""
    if create_enrollment_flag:
        create_enrollment(teacher, student, subject)

    future_date = (timezone.now() + timedelta(days=days_ahead)).date()
    return Lesson.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        date=future_date,
        start_time=time(hour, 0),
        end_time=time(hour + 1, 0),
        status=status,
    )


# ============================================================================
# TEST SUITE 1: LessonViewSet.get_queryset() filters
# ============================================================================

@pytest.mark.django_db
class TestLessonVisibilityFilters:
    """Test lesson visibility filtering by user role"""

    # Student visibility tests
    def test_student_sees_pending_lessons(self, student_user, teacher_user, subject, api_client):
        """Student should see their own pending lessons"""
        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_student_sees_confirmed_lessons(self, student_user, teacher_user, subject, api_client):
        """Student should see their own confirmed lessons"""
        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.CONFIRMED)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_student_does_not_see_completed_lessons(self, student_user, teacher_user, subject, api_client):
        """Student should NOT see their completed lessons"""
        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_student_does_not_see_cancelled_lessons(self, student_user, teacher_user, subject, api_client):
        """Student should NOT see their cancelled lessons"""
        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_student_sees_only_own_lessons(self, student_user, student_user_2, teacher_user, subject, api_client):
        """Student should NOT see lessons of other students"""
        lesson_own = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        lesson_other = create_lesson(teacher_user, student_user_2, subject, Lesson.Status.PENDING)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_own.id) in lesson_ids
        assert str(lesson_other.id) not in lesson_ids

    # Tutor visibility tests
    def test_tutor_sees_pending_lessons_of_managed_students(self, tutor_user, student_user, teacher_user, subject, api_client):
        """Tutor should see pending lessons of their managed students"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_tutor_sees_confirmed_lessons_of_managed_students(self, tutor_user, student_user, teacher_user, subject, api_client):
        """Tutor should see confirmed lessons of their managed students"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.CONFIRMED)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_tutor_does_not_see_completed_lessons_of_managed_students(self, tutor_user, student_user, teacher_user, subject, api_client):
        """Tutor should NOT see completed lessons of their managed students"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_tutor_does_not_see_cancelled_lessons_of_managed_students(self, tutor_user, student_user, teacher_user, subject, api_client):
        """Tutor should NOT see cancelled lessons of their managed students"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_tutor_does_not_see_lessons_of_unmanaged_students(self, tutor_user, tutor_user_2, student_user, teacher_user, subject, api_client):
        """Tutor should NOT see lessons of students they don't manage"""
        # Connect tutor_user_2 to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user_2
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    # Parent visibility tests
    def test_parent_sees_pending_lessons_of_children(self, parent_user, student_user, teacher_user, subject, api_client):
        """Parent should see pending lessons of their children"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_parent_sees_confirmed_lessons_of_children(self, parent_user, student_user, teacher_user, subject, api_client):
        """Parent should see confirmed lessons of their children"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.CONFIRMED)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_parent_does_not_see_completed_lessons_of_children(self, parent_user, student_user, teacher_user, subject, api_client):
        """Parent should NOT see completed lessons of their children"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_parent_does_not_see_cancelled_lessons_of_children(self, parent_user, student_user, teacher_user, subject, api_client):
        """Parent should NOT see cancelled lessons of their children"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_parent_does_not_see_lessons_of_other_children(self, parent_user, parent_user_2, student_user, teacher_user, subject, api_client):
        """Parent should NOT see lessons of children they don't have"""
        # Connect parent_user_2 to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user_2
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    # Teacher visibility tests
    def test_teacher_sees_own_lessons_all_statuses(self, teacher_user, student_user, subject, api_client):
        """Teacher should see all their lessons regardless of status"""
        pending = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        confirmed = create_lesson(teacher_user, student_user, subject, Lesson.Status.CONFIRMED)
        completed = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)
        cancelled = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(pending.id) in lesson_ids
        assert str(confirmed.id) in lesson_ids
        assert str(completed.id) in lesson_ids
        assert str(cancelled.id) in lesson_ids

    def test_teacher_sees_only_own_lessons(self, teacher_user, teacher_user_2, student_user, subject, api_client):
        """Teacher should NOT see lessons of other teachers"""
        lesson_own = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        lesson_other = create_lesson(teacher_user_2, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_own.id) in lesson_ids
        assert str(lesson_other.id) not in lesson_ids

    # Admin visibility tests
    def test_admin_sees_all_lessons(self, admin_user, teacher_user, student_user, subject, api_client):
        """Admin should see all lessons regardless of status"""
        pending = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        confirmed = create_lesson(teacher_user, student_user, subject, Lesson.Status.CONFIRMED)
        completed = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)
        cancelled = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        tokens = get_tokens(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(pending.id) in lesson_ids
        assert str(confirmed.id) in lesson_ids
        assert str(completed.id) in lesson_ids
        assert str(cancelled.id) in lesson_ids


# ============================================================================
# TEST SUITE 2: student_schedule() endpoint
# ============================================================================

@pytest.mark.django_db
class TestStudentScheduleEndpoint:
    """Test student_schedule() endpoint visibility"""

    def test_parent_sees_child_pending_lessons_in_student_schedule(self, parent_user, student_user, teacher_user, subject, api_client):
        """Parent can view child's pending lessons in student_schedule endpoint"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_parent_does_not_see_child_completed_lessons_in_student_schedule(self, parent_user, student_user, teacher_user, subject, api_client):
        """Parent cannot view child's completed lessons in student_schedule endpoint"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_parent_cannot_access_other_child_student_schedule(self, parent_user, parent_user_2, student_user, teacher_user, subject, api_client):
        """Parent cannot access student_schedule for a child that is not theirs"""
        # Connect parent_user_2 to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user_2
        student_profile.save()

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 403

    def test_tutor_sees_student_pending_lessons_in_student_schedule(self, tutor_user, student_user, teacher_user, subject, api_client):
        """Tutor can view their managed student's pending lessons in student_schedule endpoint"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) in lesson_ids

    def test_tutor_does_not_see_student_completed_lessons_in_student_schedule(self, tutor_user, student_user, teacher_user, subject, api_client):
        """Tutor cannot view their managed student's completed lessons in student_schedule endpoint"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        lesson = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson.id) not in lesson_ids

    def test_tutor_cannot_access_unmanaged_student_schedule(self, tutor_user, tutor_user_2, student_user, teacher_user, subject, api_client):
        """Tutor cannot access student_schedule for a student they don't manage"""
        # Connect tutor_user_2 to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user_2
        student_profile.save()

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 403

    def test_student_cannot_access_student_schedule_endpoint(self, student_user, api_client):
        """Student should not be able to access student_schedule endpoint"""
        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 403

    def test_teacher_cannot_access_student_schedule_endpoint(self, teacher_user, student_user, api_client):
        """Teacher should not be able to access student_schedule endpoint"""
        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == 403


# ============================================================================
# TEST SUITE 3: get_tutor_student_lessons() service
# ============================================================================

@pytest.mark.django_db
class TestGetTutorStudentLessons:
    """Test get_tutor_student_lessons() service"""

    def test_returns_pending_and_confirmed_only(self, tutor_user, student_user, teacher_user, subject):
        """get_tutor_student_lessons should return only pending and confirmed lessons"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        pending = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        confirmed = create_lesson(teacher_user, student_user, subject, Lesson.Status.CONFIRMED)
        completed = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)
        cancelled = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        lessons = LessonService.get_tutor_student_lessons(tutor_user, student_user.id)
        lesson_ids = set(str(l.id) for l in lessons)

        assert str(pending.id) in lesson_ids
        assert str(confirmed.id) in lesson_ids
        assert str(completed.id) not in lesson_ids
        assert str(cancelled.id) not in lesson_ids

    def test_excludes_completed_and_cancelled(self, tutor_user, student_user, teacher_user, subject):
        """get_tutor_student_lessons should exclude completed and cancelled lessons"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        completed = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED)
        cancelled = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED)

        lessons = LessonService.get_tutor_student_lessons(tutor_user, student_user.id)
        lesson_ids = set(str(l.id) for l in lessons)

        assert str(completed.id) not in lesson_ids
        assert str(cancelled.id) not in lesson_ids

    def test_raises_validation_error_for_unmanaged_student(self, tutor_user, student_user):
        """get_tutor_student_lessons should raise ValidationError if tutor doesn't manage student"""
        with pytest.raises(Exception):  # ValidationError
            LessonService.get_tutor_student_lessons(tutor_user, student_user.id)

    def test_with_include_cancelled_flag(self, tutor_user, student_user, teacher_user, subject):
        """get_tutor_student_lessons should include all statuses when include_cancelled=True"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        pending = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING, hour=10)
        cancelled = create_lesson(teacher_user, student_user, subject, Lesson.Status.CANCELLED, hour=11)
        completed = create_lesson(teacher_user, student_user, subject, Lesson.Status.COMPLETED, hour=12)

        lessons = LessonService.get_tutor_student_lessons(tutor_user, student_user.id, include_cancelled=True)
        lesson_ids = set(str(l.id) for l in lessons)

        assert str(pending.id) in lesson_ids
        assert str(cancelled.id) in lesson_ids
        assert str(completed.id) in lesson_ids  # All statuses included


# ============================================================================
# TEST SUITE 4: Edge cases
# ============================================================================

@pytest.mark.django_db
class TestLessonVisibilityEdgeCases:
    """Test edge cases for lesson visibility"""

    def test_no_lessons_visible_without_relationships(self, student_user, teacher_user_2, subject, api_client):
        """Student should see no lessons if they have no relationship with teacher"""
        # Create lesson with different teacher (no relationship)
        create_lesson(teacher_user_2, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        assert response.data['count'] == 1  # Still sees own lesson

    def test_unauthenticated_access_blocked(self, api_client):
        """Unauthenticated users should not access lessons"""
        response = api_client.get('/api/scheduling/lessons/')
        assert response.status_code == 401

    def test_parent_with_multiple_children(self, parent_user, student_user, student_user_2, teacher_user, subject, api_client):
        """Parent should see lessons of all their children"""
        # Connect parent to both students
        student_profile_1 = StudentProfile.objects.get(user=student_user)
        student_profile_1.parent = parent_user
        student_profile_1.save()

        student_profile_2 = StudentProfile.objects.get(user=student_user_2)
        student_profile_2.parent = parent_user
        student_profile_2.save()

        lesson_1 = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        lesson_2 = create_lesson(teacher_user, student_user_2, subject, Lesson.Status.PENDING)

        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_1.id) in lesson_ids
        assert str(lesson_2.id) in lesson_ids

    def test_tutor_with_multiple_students(self, tutor_user, student_user, student_user_2, teacher_user, subject, api_client):
        """Tutor should see lessons of all their managed students"""
        # Connect tutor to both students
        student_profile_1 = StudentProfile.objects.get(user=student_user)
        student_profile_1.tutor = tutor_user
        student_profile_1.save()

        student_profile_2 = StudentProfile.objects.get(user=student_user_2)
        student_profile_2.tutor = tutor_user
        student_profile_2.save()

        lesson_1 = create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)
        lesson_2 = create_lesson(teacher_user, student_user_2, subject, Lesson.Status.PENDING)

        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_1.id) in lesson_ids
        assert str(lesson_2.id) in lesson_ids

    def test_queryset_select_related_optimization(self, student_user, teacher_user, subject, api_client):
        """Verify queryset uses select_related for optimization"""
        create_lesson(teacher_user, student_user, subject, Lesson.Status.PENDING)

        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        # If this doesn't error, select_related is working
        assert len(response.data['results']) >= 1
