"""
Tests for lesson visibility filtering with nullable student field.

Verifies that visibility filters correctly handle lessons with student=NULL
across all user roles (STUDENT, TUTOR, PARENT, TEACHER, ADMIN).
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

from materials.models import Subject, SubjectEnrollment
from scheduling.models import Lesson
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


@pytest.fixture
def teacher_user(db):
    """Create teacher user"""
    user = User.objects.create_user(
        username=f"teacher_null_{timezone.now().timestamp()}",
        email=f"teacher_null_{timezone.now().timestamp()}@test.com",
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
def student_user(db):
    """Create student user"""
    user = User.objects.create_user(
        username=f"student_null_{timezone.now().timestamp()}",
        email=f"student_null_{timezone.now().timestamp()}@test.com",
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
def tutor_user(db):
    """Create tutor user"""
    user = User.objects.create_user(
        username=f"tutor_null_{timezone.now().timestamp()}",
        email=f"tutor_null_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="Maria",
        last_name="Tutor",
        role=User.Role.TUTOR,
        is_active=True,
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def parent_user(db):
    """Create parent user"""
    user = User.objects.create_user(
        username=f"parent_null_{timezone.now().timestamp()}",
        email=f"parent_null_{timezone.now().timestamp()}@test.com",
        password="pass123",
        first_name="John",
        last_name="Parent",
        role=User.Role.PARENT,
        is_active=True,
    )
    ParentProfile.objects.create(user=user)
    return user


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return User.objects.create_superuser(
        username=f"admin_null_{timezone.now().timestamp()}",
        email=f"admin_null_{timezone.now().timestamp()}@test.com",
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


def create_lesson_without_student(teacher, subject, status=Lesson.Status.PENDING, days_ahead=1):
    """Helper to create a lesson WITHOUT a student (student=NULL)"""
    future_date = (timezone.now() + timedelta(days=days_ahead)).date()
    return Lesson.objects.create(
        teacher=teacher,
        student=None,  # EXPLICITLY NULL
        subject=subject,
        date=future_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        status=status,
    )


def create_lesson_with_student(teacher, student, subject, status=Lesson.Status.PENDING, days_ahead=1):
    """Helper to create a lesson WITH a student"""
    # Create enrollment first to satisfy validation
    SubjectEnrollment.objects.update_or_create(
        student=student,
        subject=subject,
        defaults={'teacher': teacher, 'is_active': True}
    )
    
    future_date = (timezone.now() + timedelta(days=days_ahead)).date()
    return Lesson.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        date=future_date,
        start_time=time(10, 0),
        end_time=time(11, 0),
        status=status,
    )


# ============================================================================
# TEST SUITE: Visibility with nullable student
# ============================================================================

@pytest.mark.django_db
class TestLessonVisibilityNullableStudent:
    """Test lesson visibility filtering when student=NULL"""

    # ========================================================================
    # STUDENT role tests
    # ========================================================================

    def test_student_does_not_see_lessons_without_student(self, student_user, teacher_user, subject, api_client):
        """STUDENT should NOT see lessons with student=NULL (even if same teacher)"""
        # Create lesson without student
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) not in lesson_ids, \
            "Student should NOT see lessons with student=NULL"

    def test_student_sees_only_lessons_assigned_to_them(self, student_user, teacher_user, subject, api_client):
        """STUDENT should see only lessons where student=them (not NULL)"""
        # Create two lessons: one without student, one with student
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        lesson_assigned = create_lesson_with_student(teacher_user, student_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) not in lesson_ids, \
            "Student should NOT see lessons with student=NULL"
        assert str(lesson_assigned.id) in lesson_ids, \
            "Student should see lessons assigned to them"

    # ========================================================================
    # TUTOR role tests
    # ========================================================================

    def test_tutor_does_not_see_lessons_without_student(self, tutor_user, student_user, teacher_user, subject, api_client):
        """TUTOR should NOT see lessons with student=NULL (student_id__in filter excludes NULL)"""
        # Connect tutor to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.tutor = tutor_user
        student_profile.save()

        # Create two lessons: one without student, one with student
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        lesson_assigned = create_lesson_with_student(teacher_user, student_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(tutor_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) not in lesson_ids, \
            "Tutor should NOT see lessons with student=NULL"
        assert str(lesson_assigned.id) in lesson_ids, \
            "Tutor should see lessons of their managed students"

    # ========================================================================
    # PARENT role tests
    # ========================================================================

    def test_parent_does_not_see_lessons_without_student(self, parent_user, student_user, teacher_user, subject, api_client):
        """PARENT should NOT see lessons with student=NULL (student_id__in filter excludes NULL)"""
        # Connect parent to student
        student_profile = StudentProfile.objects.get(user=student_user)
        student_profile.parent = parent_user
        student_profile.save()

        # Create two lessons: one without student, one with student
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        lesson_assigned = create_lesson_with_student(teacher_user, student_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(parent_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) not in lesson_ids, \
            "Parent should NOT see lessons with student=NULL"
        assert str(lesson_assigned.id) in lesson_ids, \
            "Parent should see lessons of their children"

    # ========================================================================
    # TEACHER role tests
    # ========================================================================

    def test_teacher_sees_lessons_without_student(self, teacher_user, subject, api_client):
        """TEACHER SHOULD see lessons with student=NULL (drafts)"""
        # Create lesson without student (draft)
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) in lesson_ids, \
            "Teacher SHOULD see their own lessons with student=NULL (drafts)"

    def test_teacher_sees_both_null_and_assigned_lessons(self, teacher_user, student_user, subject, api_client):
        """TEACHER should see both NULL and assigned lessons"""
        # Create both types
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        lesson_assigned = create_lesson_with_student(teacher_user, student_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) in lesson_ids, \
            "Teacher should see NULL lessons"
        assert str(lesson_assigned.id) in lesson_ids, \
            "Teacher should see assigned lessons"

    def test_teacher_does_not_see_other_teacher_null_lessons(self, teacher_user, subject, api_client):
        """TEACHER should NOT see NULL lessons of other teachers"""
        # Create another teacher
        other_teacher = User.objects.create_user(
            username=f"teacher2_null_{timezone.now().timestamp()}",
            email=f"teacher2_null_{timezone.now().timestamp()}@test.com",
            password="pass123",
            first_name="Other",
            last_name="Teacher",
            role=User.Role.TEACHER,
            is_active=True,
        )
        TeacherProfile.objects.create(
            user=other_teacher,
            subject="English",
            experience_years=3,
            bio="Other teacher",
        )

        # Create lessons
        lesson_own_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        lesson_other_null = create_lesson_without_student(other_teacher, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_own_null.id) in lesson_ids, \
            "Teacher should see their own NULL lessons"
        assert str(lesson_other_null.id) not in lesson_ids, \
            "Teacher should NOT see other teacher's NULL lessons"

    # ========================================================================
    # ADMIN role tests
    # ========================================================================

    def test_admin_sees_all_lessons_including_null_student(self, admin_user, teacher_user, subject, api_client):
        """ADMIN should see ALL lessons including those with student=NULL"""
        # Create lessons
        lesson_null = create_lesson_without_student(teacher_user, subject, Lesson.Status.PENDING)
        
        tokens = get_tokens(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson_null.id) in lesson_ids, \
            "Admin SHOULD see lessons with student=NULL"

    # ========================================================================
    # Database queries: NULL handling verification
    # ========================================================================

    def test_queryset_null_filtering_with_isnull(self, teacher_user, subject):
        """Verify that NULL student filtering is handled correctly by Django ORM"""
        # Create lessons
        lesson_null = create_lesson_without_student(teacher_user, subject)
        
        # Teacher should see NULL lessons
        teacher_lessons = Lesson.objects.filter(teacher=teacher_user)
        assert teacher_lessons.filter(id=lesson_null.id).exists(), \
            "Teacher queryset should include NULL student lessons"

        # student_id__in should NOT match NULL
        student_ids = [999]  # Non-existent student
        lessons_in_filter = Lesson.objects.filter(student_id__in=student_ids)
        assert not lessons_in_filter.filter(id=lesson_null.id).exists(), \
            "student_id__in should NOT match NULL students (PostgreSQL behavior)"

    def test_student_id_in_with_empty_list(self, teacher_user, subject):
        """Verify that student_id__in with empty list doesn't match NULL"""
        lesson_null = create_lesson_without_student(teacher_user, subject)
        
        # Empty list should return no results
        lessons_empty = Lesson.objects.filter(student_id__in=[])
        assert not lessons_empty.filter(id=lesson_null.id).exists(), \
            "student_id__in with empty list should return no results (including NULL)"

    # ========================================================================
    # Edge cases with nullable student
    # ========================================================================

    def test_lesson_with_null_student_serialization(self, teacher_user, subject, api_client):
        """Verify that NULL student is correctly serialized in API response"""
        lesson_null = create_lesson_without_student(teacher_user, subject)
        
        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get(f'/api/scheduling/lessons/{lesson_null.id}/')

        assert response.status_code == 200
        data = response.data
        assert data['student'] is None or data['student'] == '', \
            "NULL student should be serialized as None or empty"
        assert data['student_id'] is None or data['student_id'] == '', \
            "NULL student_id should be serialized as None or empty"
        assert data['student_name'] == "(No student assigned)" or data['student_name'] is None, \
            "NULL student should have placeholder name"

    def test_multiple_teachers_with_null_students_isolation(self, teacher_user, subject, api_client):
        """Verify that different teachers see only their own NULL lessons"""
        other_teacher = User.objects.create_user(
            username=f"teacher3_null_{timezone.now().timestamp()}",
            email=f"teacher3_null_{timezone.now().timestamp()}@test.com",
            password="pass123",
            first_name="Third",
            last_name="Teacher",
            role=User.Role.TEACHER,
            is_active=True,
        )
        TeacherProfile.objects.create(
            user=other_teacher,
            subject="Math",
            experience_years=2,
            bio="Third teacher",
        )

        lesson1_null = create_lesson_without_student(teacher_user, subject)
        lesson2_null = create_lesson_without_student(other_teacher, subject, days_ahead=2)
        
        tokens = get_tokens(teacher_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == 200
        lesson_ids = [l['id'] for l in response.data['results']]
        assert str(lesson1_null.id) in lesson_ids
        assert str(lesson2_null.id) not in lesson_ids, \
            "Teacher should not see other teacher's NULL lessons"

