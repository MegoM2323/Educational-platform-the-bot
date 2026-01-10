"""Unit tests for Lesson serializer validation (M3)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import date, time, timedelta
from scheduling.serializers import LessonCreateSerializer
from materials.models import Subject

User = get_user_model()


class LessonSerializerValidationTests(TestCase):
    """Test Lesson serializer validation."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Math")
        self.teacher = User.objects.create(
            username="teacher_serializer",
            role="teacher"
        )
        self.student = User.objects.create(
            username="student_serializer",
            role="student"
        )
        self.lesson_date = date.today() + timedelta(days=1)

    def test_validate_student_with_integer_id(self):
        """Serializer accepts student as integer ID."""
        data = {
            "teacher": self.teacher.id,
            "student": self.student.id,
            "subject": self.subject.id,
            "date": self.lesson_date,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        serializer = LessonCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_validate_student_invalid_format_rejected(self):
        """Serializer rejects invalid student format."""
        data = {
            "teacher": self.teacher.id,
            "student": "abc",
            "subject": self.subject.id,
            "date": self.lesson_date,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        serializer = LessonCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("student", serializer.errors)

    def test_validate_student_nonexistent_id_rejected(self):
        """Serializer rejects nonexistent student ID."""
        data = {
            "teacher": self.teacher.id,
            "student": 999999,
            "subject": self.subject.id,
            "date": self.lesson_date,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        serializer = LessonCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_validate_teacher_nonexistent_rejected(self):
        """Serializer rejects nonexistent teacher."""
        data = {
            "teacher": 999999,
            "student": self.student.id,
            "subject": self.subject.id,
            "date": self.lesson_date,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        serializer = LessonCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_validate_subject_nonexistent_rejected(self):
        """Serializer rejects nonexistent subject."""
        data = {
            "teacher": self.teacher.id,
            "student": self.student.id,
            "subject": 999999,
            "date": self.lesson_date,
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        serializer = LessonCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
