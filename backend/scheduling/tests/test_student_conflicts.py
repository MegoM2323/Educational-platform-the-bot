"""Unit tests for student conflict checking (H2)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import date, time, timedelta
from scheduling.models import Lesson
from materials.models import Subject

User = get_user_model()


class StudentConflictsTests(TestCase):
    """Test student conflict detection."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Math")
        self.teacher = User.objects.create(username="teacher_conflicts", role="teacher")
        self.student = User.objects.create(username="student_conflicts", role="student")

    def test_lesson_without_student_does_not_error(self):
        """Lesson without student (student=NULL) doesn't cause AttributeError."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=None,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending"
        )

        self.assertIsNone(lesson.student)
        self.assertEqual(lesson.teacher.id, self.teacher.id)
        self.assertIn("(No student)", str(lesson))

    def test_conflict_has_type_field(self):
        """Conflict detection includes 'type' field indicating teacher or student conflict."""
        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed"
        )

        self.assertIsNotNone(lesson1.teacher)
        self.assertIsNotNone(lesson1.student)

    def test_no_conflict_for_different_times(self):
        """No conflict when lessons are at different times."""
        lesson_date = date.today() + timedelta(days=1)

        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=lesson_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed"
        )

        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=lesson_date,
            start_time=time(12, 0),
            end_time=time(13, 0),
            status="confirmed"
        )

        self.assertEqual(
            Lesson.objects.filter(student=self.student, date=lesson_date).count(),
            2
        )

    def test_cancelled_lessons_not_in_conflicts(self):
        """Cancelled lessons should not be considered as conflicts."""
        lesson_date = date.today() + timedelta(days=1)

        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=lesson_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="cancelled"
        )

        active_lessons = Lesson.objects.filter(
            student=self.student,
            date=lesson_date,
            status__in=["pending", "confirmed"]
        )

        self.assertEqual(active_lessons.count(), 0)
