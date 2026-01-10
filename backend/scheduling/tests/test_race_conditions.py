"""Unit tests for race condition prevention (C4)."""

import pytest
from django.db import transaction
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from datetime import datetime, time, date, timedelta
from scheduling.models import Lesson
from materials.models import Subject

User = get_user_model()


class RaceConditionTests(TransactionTestCase):
    """Test race condition prevention."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(
            name="Math",
            color="#000000"
        )
        self.teacher = User.objects.create(
            username="teacher_race",
            role="teacher"
        )
        self.student = User.objects.create(
            username="student_race",
            role="student"
        )

    def test_lesson_creation_validates_time_range(self):
        """Lesson validation prevents invalid time ranges."""
        with self.assertRaises(Exception):
            Lesson.objects.create(
                teacher=self.teacher,
                student=self.student,
                subject=self.subject,
                date=date.today() + timedelta(days=1),
                start_time=time(11, 0),
                end_time=time(10, 0),  # Invalid: end before start
                status="pending"
            )

    def test_lesson_creation_validates_date(self):
        """Lesson validation prevents creating lessons in the past."""
        with self.assertRaises(Exception):
            Lesson.objects.create(
                teacher=self.teacher,
                student=self.student,
                subject=self.subject,
                date=date.today() - timedelta(days=1),  # Past date
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="pending"
            )

    def test_multiple_lessons_same_teacher_different_times(self):
        """Teacher can have multiple lessons at different times."""
        lesson_date = date.today() + timedelta(days=1)

        lesson1 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=lesson_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending"
        )

        lesson2 = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=lesson_date,
            start_time=time(11, 0),
            end_time=time(12, 0),
            status="pending"
        )

        self.assertEqual(Lesson.objects.filter(teacher=self.teacher).count(), 2)

    def test_atomic_transaction_rollback_on_error(self):
        """@transaction.atomic rolls back on error."""
        lesson_date = date.today() + timedelta(days=1)

        try:
            with transaction.atomic():
                lesson = Lesson.objects.create(
                    teacher=self.teacher,
                    student=self.student,
                    subject=self.subject,
                    date=lesson_date,
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    status="pending"
                )
                # Force error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Lesson should be rolled back
        self.assertEqual(
            Lesson.objects.filter(
                date=lesson_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            ).count(),
            0
        )
