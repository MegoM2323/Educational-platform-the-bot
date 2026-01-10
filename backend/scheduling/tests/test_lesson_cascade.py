"""
Unit tests for Lesson cascade protection (C1).
"""

from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import time, date, timedelta
from materials.models import Subject, SubjectEnrollment
from scheduling.models import Lesson

User = get_user_model()


class LessonCascadeProtectTests(TestCase):
    """Test Subject PROTECT constraint when lessons exist."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Advanced Math",
            color="#FF5733"
        )
        self.teacher = User.objects.create(
            username="teacher1",
            first_name="John",
            last_name="Doe",
            role="teacher"
        )
        self.student = User.objects.create(
            username="student1",
            first_name="Jane",
            last_name="Smith",
            role="student"
        )
        # Create SubjectEnrollment
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active"
        )

    def test_cannot_delete_subject_with_lessons(self):
        """Subject with lessons cannot be deleted - ProtectedError."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending"
        )

        with self.assertRaises(ProtectedError):
            self.subject.delete()

        self.assertTrue(Subject.objects.filter(id=self.subject.id).exists())

    def test_can_delete_subject_without_lessons(self):
        """Subject without lessons can be deleted successfully."""
        subject_id = self.subject.id
        self.subject.delete()

        self.assertFalse(Subject.objects.filter(id=subject_id).exists())

    def test_deleting_lesson_does_not_cascade_delete_subject(self):
        """Deleting a lesson does not affect the subject."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending"
        )

        lesson.delete()

        self.assertTrue(Subject.objects.filter(id=self.subject.id).exists())

    def test_multiple_lessons_same_subject_protect_delete(self):
        """Subject with multiple lessons cannot be deleted."""
        for i in range(3):
            Lesson.objects.create(
                teacher=self.teacher,
                student=self.student,
                subject=self.subject,
                date=date.today() + timedelta(days=i+1),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="pending"
            )

        with self.assertRaises(ProtectedError):
            self.subject.delete()

    def test_delete_all_lessons_then_delete_subject(self):
        """Can delete subject after all its lessons are removed."""
        lessons = [
            Lesson.objects.create(
                teacher=self.teacher,
                student=self.student,
                subject=self.subject,
                date=date.today() + timedelta(days=i+1),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="pending"
            )
            for i in range(2)
        ]

        for lesson in lessons:
            lesson.delete()

        subject_id = self.subject.id
        self.subject.delete()

        self.assertFalse(Subject.objects.filter(id=subject_id).exists())
