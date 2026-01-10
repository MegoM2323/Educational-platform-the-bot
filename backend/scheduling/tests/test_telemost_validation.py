"""Unit tests for telemost link validation (H3)."""

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import date, time, timedelta
from scheduling.models import Lesson, validate_telemost_link
from materials.models import Subject

User = get_user_model()


class TelomostValidationTests(TestCase):
    """Test telemost link validation."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Math")
        self.teacher = User.objects.create(username="teacher_telemost", role="teacher")
        self.student = User.objects.create(username="student_telemost", role="student")

    def test_valid_yandex_telemost_link(self):
        """Valid Yandex Telemost link is accepted."""
        link = "https://telemost.yandex.ru/j/12345"
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending",
            telemost_link=link
        )
        self.assertEqual(lesson.telemost_link, link)

    def test_valid_google_meet_link(self):
        """Valid Google Meet link is accepted."""
        link = "https://meet.google.com/abc-defg-hij"
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending",
            telemost_link=link
        )
        self.assertEqual(lesson.telemost_link, link)

    def test_blank_link_allowed(self):
        """Blank telemost link is allowed."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="pending",
            telemost_link=""
        )
        self.assertEqual(lesson.telemost_link, "")

    def test_phishing_link_rejected(self):
        """Phishing links are rejected."""
        with self.assertRaises(ValidationError):
            Lesson.objects.create(
                teacher=self.teacher,
                student=self.student,
                subject=self.subject,
                date=date.today() + timedelta(days=1),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status="pending",
                telemost_link="https://telemost-yandex.ru/j/12345"
            )

    def test_validator_function_directly(self):
        """Test validate_telemost_link function directly."""
        validate_telemost_link("https://telemost.yandex.ru/j/12345")
        validate_telemost_link("")
        with self.assertRaises(ValidationError):
            validate_telemost_link("https://example.com")
