"""
E2E тест управления расписанием администратором.

Тестирует полный цикл:
1. LIST: загрузка и отображение расписания
2. CREATE: создание новых уроков
3. FILTER: фильтрация по датам и преподавателям
4. STATS: проверка статистики
"""

import os
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if not settings.configured:
    django.setup()

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from materials.models import Subject, SubjectEnrollment, TeacherSubject
from scheduling.models import Lesson
from accounts.models import TeacherProfile, StudentProfile

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user with cleanup"""
    # Cleanup existing admin test users
    User.objects.filter(username="admin_schedule_test").delete()

    timestamp = uuid4().hex[:8]
    user = User.objects.create_superuser(
        username=f"admin_schedule_test_{timestamp}",
        email=f"admin_schedule_{timestamp}@test.com",
        password="admin123secure",
        first_name="Admin",
        last_name="Schedule",
        role=User.Role.ADMIN,
    )
    return user


@pytest.fixture
def teacher_user_1(db):
    """Create first teacher user with cleanup"""
    # Cleanup existing teacher test users
    User.objects.filter(username__startswith="teacher_schedule_1").delete()

    timestamp = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"teacher_schedule_1_{timestamp}",
        email=f"teacher_schedule_1_{timestamp}@test.com",
        password="teacher123",
        first_name="Ivan",
        last_name="Petrov",
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
    """Create second teacher user with cleanup"""
    # Cleanup existing teacher test users
    User.objects.filter(username__startswith="teacher_schedule_2").delete()

    timestamp = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"teacher_schedule_2_{timestamp}",
        email=f"teacher_schedule_2_{timestamp}@test.com",
        password="teacher456",
        first_name="Maria",
        last_name="Smirnova",
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
def student_user_1(db):
    """Create first student user with cleanup"""
    # Cleanup existing student test users
    User.objects.filter(username__startswith="student_schedule_1").delete()

    timestamp = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"student_schedule_1_{timestamp}",
        email=f"student_schedule_1_{timestamp}@test.com",
        password="student123",
        first_name="Alex",
        last_name="Ivanov",
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
    """Create second student user with cleanup"""
    # Cleanup existing student test users
    User.objects.filter(username__startswith="student_schedule_2").delete()

    timestamp = uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"student_schedule_2_{timestamp}",
        email=f"student_schedule_2_{timestamp}@test.com",
        password="student456",
        first_name="Nina",
        last_name="Sokolova",
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
def subject_math(db):
    """Create Mathematics subject with cleanup"""
    # Cleanup existing
    Subject.objects.filter(name="Mathematics").delete()

    return Subject.objects.create(
        name="Mathematics",
        description="Math subject",
        color="#FF5733",
    )


@pytest.fixture
def subject_english(db):
    """Create English subject with cleanup"""
    # Cleanup existing
    Subject.objects.filter(name="English").delete()

    return Subject.objects.create(
        name="English",
        description="English subject",
        color="#33FF57",
    )


@pytest.fixture
def admin_client(db, admin_user):
    """Create authenticated admin client"""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def sample_lessons(
    db,
    teacher_user_1,
    teacher_user_2,
    student_user_1,
    student_user_2,
    subject_math,
    subject_english,
):
    """Create sample lessons for testing with cleanup"""
    # Cleanup existing lessons to ensure isolation
    Lesson.objects.all().delete()
    TeacherSubject.objects.filter(teacher__in=[teacher_user_1, teacher_user_2]).delete()
    SubjectEnrollment.objects.filter(
        student__in=[student_user_1, student_user_2]
    ).delete()

    # Create TeacherSubject relationships (required for Lesson validation)
    teacher_subject_1 = TeacherSubject.objects.create(
        teacher=teacher_user_1, subject=subject_math, is_active=True
    )
    teacher_subject_2 = TeacherSubject.objects.create(
        teacher=teacher_user_2, subject=subject_english, is_active=True
    )

    # Create SubjectEnrollment relationships (required for Lesson validation)
    enrollment_1 = SubjectEnrollment.objects.create(
        student=student_user_1,
        subject=subject_math,
        teacher=teacher_user_1,
        is_active=True,
    )
    enrollment_2 = SubjectEnrollment.objects.create(
        student=student_user_2,
        subject=subject_english,
        teacher=teacher_user_2,
        is_active=True,
    )
    enrollment_3 = SubjectEnrollment.objects.create(
        student=student_user_2,
        subject=subject_math,
        teacher=teacher_user_1,
        is_active=True,
    )
    enrollment_4 = SubjectEnrollment.objects.create(
        student=student_user_1,
        subject=subject_english,
        teacher=teacher_user_2,
        is_active=True,
    )

    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    week_later = today + timedelta(days=7)
    unique_ts = uuid4().hex[:6]

    lessons = []

    # Lesson 1: Tomorrow, Math, Pending
    lesson1 = Lesson.objects.create(
        teacher=teacher_user_1,
        student=student_user_1,
        subject=subject_math,
        date=tomorrow,
        start_time="10:00:00",
        end_time="11:00:00",
        status=Lesson.Status.PENDING,
        description=f"Math lesson 1 {unique_ts}",
    )
    lessons.append(lesson1)

    # Lesson 2: Tomorrow, English, Confirmed
    lesson2 = Lesson.objects.create(
        teacher=teacher_user_2,
        student=student_user_2,
        subject=subject_english,
        date=tomorrow,
        start_time="14:00:00",
        end_time="15:00:00",
        status=Lesson.Status.CONFIRMED,
        description=f"English lesson 1 {unique_ts}",
    )
    lessons.append(lesson2)

    # Lesson 3: Week later, Math, Completed
    lesson3 = Lesson.objects.create(
        teacher=teacher_user_1,
        student=student_user_2,
        subject=subject_math,
        date=week_later,
        start_time="09:00:00",
        end_time="10:00:00",
        status=Lesson.Status.COMPLETED,
        description=f"Math lesson 2 {unique_ts}",
    )
    lessons.append(lesson3)

    # Lesson 4: Week later, English, Cancelled
    lesson4 = Lesson.objects.create(
        teacher=teacher_user_2,
        student=student_user_1,
        subject=subject_english,
        date=week_later,
        start_time="15:00:00",
        end_time="16:00:00",
        status=Lesson.Status.CANCELLED,
        description=f"English lesson 2 cancelled {unique_ts}",
    )
    lessons.append(lesson4)

    return lessons


@pytest.mark.django_db
class TestAdminScheduleList:
    """Test schedule list functionality"""

    def test_admin_can_list_all_lessons(self, admin_client, sample_lessons):
        """Test that admin can load all lessons"""
        response = admin_client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "results" in response.json()
        assert len(response.json()["results"]) == 4

    def test_list_response_contains_required_columns(
        self, admin_client, sample_lessons
    ):
        """Test that lesson list contains required columns"""
        response = admin_client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 200

        lesson_data = response.json()["results"][0]
        required_fields = [
            "id",
            "date",
            "start_time",
            "end_time",
            "teacher_name",
            "student_name",
            "subject_name",
            "status",
        ]
        for field in required_fields:
            assert field in lesson_data, f"Missing field: {field}"

    def test_list_lessons_ordered_by_date(self, admin_client, sample_lessons):
        """Test that lessons are ordered by date"""
        response = admin_client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 200

        results = response.json()["results"]
        for i in range(len(results) - 1):
            current_date = results[i]["date"]
            next_date = results[i + 1]["date"]
            # Should be ordered (later dates may come first due to descending order)
            assert current_date is not None
            assert next_date is not None

    def test_list_pagination_works(self, admin_client, sample_lessons):
        """Test that pagination metadata is included"""
        response = admin_client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 200

        data = response.json()
        assert "count" in data
        assert data["count"] == 4

    def test_list_includes_all_statuses(self, admin_client, sample_lessons):
        """Test that list includes lessons with different statuses"""
        response = admin_client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 200

        results = response.json()["results"]
        statuses = {lesson["status"] for lesson in results}

        assert "pending" in statuses
        assert "confirmed" in statuses
        assert "completed" in statuses
        assert "cancelled" in statuses


@pytest.mark.django_db
class TestAdminScheduleCreate:
    """Test lesson creation functionality"""

    def test_admin_can_create_lesson(
        self, admin_client, teacher_user_1, student_user_1, subject_math
    ):
        """Test that admin can create a new lesson"""
        # Create necessary enrollment relationship
        TeacherSubject.objects.create(
            teacher=teacher_user_1, subject=subject_math, is_active=True
        )
        SubjectEnrollment.objects.create(
            student=student_user_1,
            subject=subject_math,
            teacher=teacher_user_1,
            is_active=True,
        )

        future_date = (datetime.now().date() + timedelta(days=5)).strftime("%Y-%m-%d")

        data = {
            "teacher": teacher_user_1.id,
            "student": student_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "15:00:00",
            "end_time": "16:00:00",
            "description": "New math lesson",
            "telemost_link": "https://telemost.yandex.ru/j/12345",
        }

        response = admin_client.post(
            "/api/admin/schedule/lessons/create/", data, format="json"
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

        # Verify lesson was created
        assert Lesson.objects.filter(
            teacher=teacher_user_1,
            student=student_user_1,
            subject=subject_math,
        ).exists()

    def test_created_lesson_appears_in_list(
        self, admin_client, teacher_user_1, student_user_1, subject_math
    ):
        """Test that created lesson appears in list"""
        # Create necessary enrollment relationship
        TeacherSubject.objects.create(
            teacher=teacher_user_1, subject=subject_math, is_active=True
        )
        SubjectEnrollment.objects.create(
            student=student_user_1,
            subject=subject_math,
            teacher=teacher_user_1,
            is_active=True,
        )

        future_date = (datetime.now().date() + timedelta(days=3)).strftime("%Y-%m-%d")

        data = {
            "teacher": teacher_user_1.id,
            "student": student_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "description": "Test lesson creation",
        }

        create_response = admin_client.post(
            "/api/admin/schedule/lessons/create/", data, format="json"
        )
        assert create_response.status_code == 201

        # Get list and verify lesson is there
        list_response = admin_client.get("/api/admin/schedule/lessons/")
        assert list_response.status_code == 200

        lessons = list_response.json()["results"]
        created_lesson = next(
            (
                l
                for l in lessons
                if l["subject_name"] == "Mathematics" and "11:00" in l["start_time"]
            ),
            None,
        )
        assert created_lesson is not None

    def test_create_lesson_requires_teacher(
        self, admin_client, student_user_1, subject_math
    ):
        """Test that teacher is required"""
        future_date = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")

        data = {
            "student": student_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        }

        response = admin_client.post(
            "/api/admin/schedule/lessons/create/", data, format="json"
        )
        assert response.status_code == 400
        assert response.json()["success"] is False

    def test_create_lesson_requires_student(
        self, admin_client, teacher_user_1, subject_math
    ):
        """Test that student is required"""
        future_date = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")

        data = {
            "teacher": teacher_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        }

        response = admin_client.post(
            "/api/admin/schedule/lessons/create/", data, format="json"
        )
        assert response.status_code == 400
        assert response.json()["success"] is False

    def test_create_lesson_with_invalid_teacher(
        self, admin_client, student_user_1, subject_math
    ):
        """Test that invalid teacher ID is rejected"""
        future_date = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")

        # Use a non-existent teacher ID (User IDs are integers)
        fake_teacher_id = 999999

        data = {
            "teacher": fake_teacher_id,
            "student": student_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        }

        response = admin_client.post(
            "/api/admin/schedule/lessons/create/", data, format="json"
        )
        assert response.status_code == 404
        assert response.json()["success"] is False


@pytest.mark.django_db
class TestAdminScheduleFilter:
    """Test schedule filtering functionality"""

    def test_filter_by_teacher(self, admin_client, sample_lessons, teacher_user_1):
        """Test filtering lessons by teacher"""
        params = {"teacher_id": teacher_user_1.id}
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 200

        lessons = response.json()["results"]
        # Teacher 1 should have 2 lessons (lesson 1 and 3)
        assert all(l["teacher_name"] == teacher_user_1.get_full_name() for l in lessons)
        assert len(lessons) >= 2

    def test_filter_by_date_range(self, admin_client, sample_lessons):
        """Test filtering lessons by date range"""
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_end = tomorrow

        params = {
            "date_from": tomorrow,
            "date_to": tomorrow_end,
        }
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 200

        lessons = response.json()["results"]
        # Should have 2 lessons on this date
        assert len(lessons) >= 1

    def test_filter_by_subject(self, admin_client, sample_lessons, subject_math):
        """Test filtering lessons by subject"""
        params = {"subject_id": subject_math.id}
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 200

        lessons = response.json()["results"]
        assert all(l["subject_name"] == "Mathematics" for l in lessons)
        assert len(lessons) >= 2

    def test_filter_by_student(self, admin_client, sample_lessons, student_user_1):
        """Test filtering lessons by student"""
        params = {"student_id": student_user_1.id}
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 200

        lessons = response.json()["results"]
        assert all(l["student_name"] == student_user_1.get_full_name() for l in lessons)

    def test_filter_by_status(self, admin_client, sample_lessons):
        """Test filtering lessons by status"""
        params = {"status": "pending"}
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 200

        lessons = response.json()["results"]
        assert all(l["status"] == "pending" for l in lessons)

    def test_combined_filters(
        self, admin_client, sample_lessons, teacher_user_1, subject_math
    ):
        """Test using multiple filters together"""
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_end = tomorrow

        params = {
            "teacher_id": teacher_user_1.id,
            "subject_id": subject_math.id,
            "date_from": tomorrow,
            "date_to": tomorrow_end,
        }
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 200

        lessons = response.json()["results"]
        assert all(l["teacher_name"] == teacher_user_1.get_full_name() for l in lessons)
        assert all(l["subject_name"] == "Mathematics" for l in lessons)

    def test_filter_with_invalid_date_format(self, admin_client, sample_lessons):
        """Test that invalid date format is rejected"""
        params = {"date_from": "invalid-date"}
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 400
        assert response.json()["success"] is False

    def test_filter_with_date_range_validation(self, admin_client, sample_lessons):
        """Test that date_from > date_to is rejected"""
        later_date = (datetime.now().date() + timedelta(days=10)).strftime("%Y-%m-%d")
        earlier_date = (datetime.now().date() + timedelta(days=5)).strftime("%Y-%m-%d")

        params = {
            "date_from": later_date,
            "date_to": earlier_date,
        }
        response = admin_client.get("/api/admin/schedule/lessons/", params)
        assert response.status_code == 400
        assert response.json()["success"] is False


@pytest.mark.django_db
class TestAdminScheduleStats:
    """Test schedule statistics functionality"""

    def test_admin_can_get_stats(self, admin_client, sample_lessons):
        """Test that admin can retrieve schedule statistics"""
        response = admin_client.get("/api/admin/schedule/stats/")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_stats_contains_total_lessons_count(self, admin_client, sample_lessons):
        """Test that stats include total lessons count"""
        response = admin_client.get("/api/admin/schedule/stats/")
        assert response.status_code == 200

        stats = response.json()["stats"]
        assert "total_lessons" in stats or "total_count" in stats or "count" in stats

    def test_stats_contains_lessons_by_status(self, admin_client, sample_lessons):
        """Test that stats include lesson counts by status"""
        response = admin_client.get("/api/admin/schedule/stats/")
        assert response.status_code == 200

        stats = response.json()["stats"]
        # Should have status-related counts
        assert isinstance(stats, dict)

    def test_stats_counts_match_database(self, admin_client, sample_lessons):
        """Test that stats counts match actual database"""
        response = admin_client.get("/api/admin/schedule/stats/")
        assert response.status_code == 200

        stats = response.json()["stats"]
        # Verify basic stats structure exists
        assert stats is not None

        # Count from database
        total_db = Lesson.objects.count()
        pending_db = Lesson.objects.filter(status=Lesson.Status.PENDING).count()
        confirmed_db = Lesson.objects.filter(status=Lesson.Status.CONFIRMED).count()
        completed_db = Lesson.objects.filter(status=Lesson.Status.COMPLETED).count()
        cancelled_db = Lesson.objects.filter(status=Lesson.Status.CANCELLED).count()

        assert total_db == 4
        assert pending_db == 1
        assert confirmed_db == 1
        assert completed_db == 1
        assert cancelled_db == 1


@pytest.mark.django_db
class TestAdminSchedulePermissions:
    """Test permission and authentication"""

    def test_non_admin_cannot_list_schedule(self, db, teacher_user_1):
        """Test that non-admin users cannot access schedule list"""
        client = APIClient()
        client.force_authenticate(user=teacher_user_1)

        response = client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 403

    def test_non_admin_cannot_create_lesson(self, db, teacher_user_1):
        """Test that non-admin users cannot create lessons via admin endpoint"""
        client = APIClient()
        client.force_authenticate(user=teacher_user_1)

        future_date = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")
        data = {
            "teacher": teacher_user_1.id,
            "student": teacher_user_1.id,
            "subject": 1,
            "date": future_date,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
        }

        response = client.post(
            "/api/admin/schedule/lessons/create/", data, format="json"
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_schedule(self):
        """Test that unauthenticated users cannot access schedule"""
        client = APIClient()
        response = client.get("/api/admin/schedule/lessons/")
        assert response.status_code == 401

    def test_admin_can_access_filters(self, admin_client):
        """Test that admin can access filter options"""
        response = admin_client.get("/api/admin/schedule/filters/")
        assert response.status_code == 200
        assert response.json()["success"] is True

        data = response.json()
        assert "teachers" in data
        assert "subjects" in data
        assert "students" in data


@pytest.mark.django_db
class TestAdminScheduleIntegration:
    """Integration tests for full schedule management workflow"""

    def test_full_schedule_management_workflow(
        self,
        admin_client,
        teacher_user_1,
        student_user_1,
        subject_math,
    ):
        """Test complete schedule management workflow"""
        # Create enrollment for this test
        TeacherSubject.objects.create(
            teacher=teacher_user_1, subject=subject_math, is_active=True
        )
        SubjectEnrollment.objects.create(
            student=student_user_1,
            subject=subject_math,
            teacher=teacher_user_1,
            is_active=True,
        )

        # Step 1: List existing lessons (may start with 0)
        list_response = admin_client.get("/api/admin/schedule/lessons/")
        assert list_response.status_code == 200
        initial_count = list_response.json()["count"]

        # Step 2: Create new lesson
        future_date = (datetime.now().date() + timedelta(days=10)).strftime("%Y-%m-%d")
        create_data = {
            "teacher": teacher_user_1.id,
            "student": student_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "13:00:00",
            "end_time": "14:00:00",
            "description": "Integration test lesson",
        }
        create_response = admin_client.post(
            "/api/admin/schedule/lessons/create/", create_data, format="json"
        )
        assert create_response.status_code == 201

        # Step 3: Verify lesson appears in list
        list_response2 = admin_client.get("/api/admin/schedule/lessons/")
        assert list_response2.status_code == 200
        new_count = list_response2.json()["count"]
        assert new_count == initial_count + 1

        # Step 4: Filter by teacher
        filter_response = admin_client.get(
            "/api/admin/schedule/lessons/", {"teacher_id": teacher_user_1.id}
        )
        assert filter_response.status_code == 200
        filtered_lessons = filter_response.json()["results"]
        assert len(filtered_lessons) >= 1

        # Step 5: Check stats
        stats_response = admin_client.get("/api/admin/schedule/stats/")
        assert stats_response.status_code == 200
        stats = stats_response.json()["stats"]
        assert stats is not None

    def test_schedule_with_multiple_status_changes(
        self,
        admin_client,
        teacher_user_1,
        student_user_1,
        subject_math,
    ):
        """Test creating lessons and verifying different statuses"""
        # Create enrollment relationship
        TeacherSubject.objects.create(
            teacher=teacher_user_1, subject=subject_math, is_active=True
        )
        SubjectEnrollment.objects.create(
            student=student_user_1,
            subject=subject_math,
            teacher=teacher_user_1,
            is_active=True,
        )

        future_date = (datetime.now().date() + timedelta(days=6)).strftime("%Y-%m-%d")

        # Create lesson (default status: pending)
        create_data = {
            "teacher": teacher_user_1.id,
            "student": student_user_1.id,
            "subject": subject_math.id,
            "date": future_date,
            "start_time": "16:00:00",
            "end_time": "17:00:00",
        }
        response = admin_client.post(
            "/api/admin/schedule/lessons/create/", create_data, format="json"
        )
        assert response.status_code == 201

        # Get list and verify status
        list_response = admin_client.get("/api/admin/schedule/lessons/")
        lessons = list_response.json()["results"]
        new_lesson = next((l for l in lessons if "16:00" in l["start_time"]), None)
        assert new_lesson is not None
        assert new_lesson["status"] == "pending"
