"""
Lesson Visibility Matrix - Comprehensive Test Suite.

Full matrix verification testing all 4 statuses × 5 roles = 20 visibility scenarios.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, time
from rest_framework.test import APIClient

from scheduling.models import Lesson
from accounts.models import StudentProfile
from materials.models import Subject, SubjectEnrollment, Topic, Course

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(scope="module")
def subject(db):
    course = Course.objects.create(name="Test Course")
    topic = Topic.objects.create(name="Test Topic", course=course)
    return Subject.objects.create(name="Test Subject", topic=topic, course=course)


@pytest.fixture(scope="module")
def users(db):
    return {
        "teacher": User.objects.create_user(
            username="teacher_matrix", email="teacher@test.com", password="pass123", role="teacher"
        ),
        "student": User.objects.create_user(
            username="student_matrix", email="student@test.com", password="pass123", role="student"
        ),
        "tutor": User.objects.create_user(
            username="tutor_matrix", email="tutor@test.com", password="pass123", role="tutor"
        ),
        "parent": User.objects.create_user(
            username="parent_matrix", email="parent@test.com", password="pass123", role="parent"
        ),
        "admin": User.objects.create_user(
            username="admin_matrix", email="admin@test.com", password="pass123", role="admin", is_staff=True, is_superuser=True
        ),
    }


@pytest.fixture(scope="module")
def relationships(db, users, subject):
    StudentProfile.objects.create(user=users["student"], tutor=users["tutor"], parent=users["parent"])
    SubjectEnrollment.objects.create(user=users["student"], subject=subject, teacher=users["teacher"])
    return {}


@pytest.fixture
def tomorrow_times(db):
    tomorrow = timezone.now().date() + timedelta(days=1)
    return {
        "date": tomorrow,
        "start_time": time(10, 0),
        "end_time": time(11, 0),
    }


@pytest.mark.django_db
class TestVisibilityMatrix:
    """Test all 4 statuses × 5 roles = 20 visibility scenarios."""

    def test_pending_visible_to_student(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.PENDING,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["student"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_pending_visible_to_tutor(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.PENDING,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["tutor"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_pending_visible_to_parent(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.PENDING,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["parent"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_pending_visible_to_teacher(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.PENDING,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["teacher"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_pending_visible_to_admin(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.PENDING,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["admin"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_completed_not_visible_to_student(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.COMPLETED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["student"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) not in lesson_ids

    def test_completed_not_visible_to_tutor(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.COMPLETED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["tutor"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) not in lesson_ids

    def test_completed_not_visible_to_parent(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.COMPLETED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["parent"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) not in lesson_ids

    def test_completed_visible_to_teacher(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.COMPLETED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["teacher"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_completed_visible_to_admin(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.COMPLETED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["admin"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_cancelled_not_visible_to_student(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.CANCELLED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["student"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) not in lesson_ids

    def test_cancelled_not_visible_to_tutor(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.CANCELLED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["tutor"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) not in lesson_ids

    def test_cancelled_not_visible_to_parent(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.CANCELLED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["parent"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) not in lesson_ids

    def test_cancelled_visible_to_teacher(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.CANCELLED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["teacher"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids

    def test_cancelled_visible_to_admin(self, users, subject, tomorrow_times):
        lesson = Lesson.objects.create(
            teacher=users["teacher"],
            student=users["student"],
            subject=subject,
            status=Lesson.Status.CANCELLED,
            **tomorrow_times
        )
        client = APIClient()
        client.force_authenticate(users["admin"])
        response = client.get("/api/scheduling/lessons/")
        lesson_ids = [str(l["id"]) for l in response.json()["results"]]
        assert str(lesson.id) in lesson_ids
