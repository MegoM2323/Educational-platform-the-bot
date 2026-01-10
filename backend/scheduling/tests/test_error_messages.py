"""Unit tests for error message quality (L1-L2)."""

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import date, time, timedelta
from scheduling.models import Lesson
from materials.models import Subject
from accounts.models import StudentProfile
import inspect

User = get_user_model()


class ErrorMessageQualityTests(TestCase):
    """Test error message clarity and documentation."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Math")
        self.teacher = User.objects.create(username="teacher_errors", role="teacher")
        self.student = User.objects.create(username="student_errors", role="student")

    def test_lesson_clean_error_shows_actual_duration(self):
        """ValidationError for duration shows actual vs required."""
        lesson = Lesson(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(10, 15),
        )

        try:
            lesson.full_clean()
        except ValidationError as e:
            error_message = str(e)
            self.assertIn("15", error_message)

    def test_lesson_clean_error_shows_date_context(self):
        """ValidationError for date shows what was requested."""
        past_date = date.today() - timedelta(days=1)
        lesson = Lesson(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=past_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        try:
            lesson.full_clean()
        except ValidationError as e:
            error_message = str(e)
            self.assertIn("date", error_message.lower())

    def test_lesson_clean_has_docstring(self):
        """Lesson.clean() has a docstring."""
        docstring = Lesson.clean.__doc__
        self.assertIsNotNone(docstring)
        self.assertTrue(len(docstring) > 0)

    def test_student_profile_delete_has_docstring(self):
        """StudentProfile.delete() has a docstring."""
        docstring = StudentProfile.delete.__doc__
        self.assertIsNotNone(docstring)
        self.assertTrue(len(docstring) > 0)

    def test_student_profile_clean_has_docstring(self):
        """StudentProfile.clean() has a docstring."""
        docstring = StudentProfile.clean.__doc__
        self.assertIsNotNone(docstring)
        self.assertTrue(len(docstring) > 0)

    def test_complex_methods_have_inline_comments(self):
        """Complex methods contain inline comments (at least 2+)."""
        delete_method = StudentProfile.delete
        source = inspect.getsource(delete_method)

        comment_count = source.count("#")
        self.assertGreaterEqual(comment_count, 2)

    def test_lesson_datetime_properties_have_docstrings(self):
        """Lesson.datetime_start and datetime_end have docstrings."""
        self.assertIsNotNone(Lesson.datetime_start.__doc__)
        self.assertIsNotNone(Lesson.datetime_end.__doc__)

    def test_error_message_not_empty(self):
        """Error messages are not empty strings."""
        lesson = Lesson(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        try:
            lesson.full_clean()
        except ValidationError as e:
            self.assertGreater(len(str(e)), 0)

    def test_lesson_string_representation_shows_details(self):
        """Lesson.__str__() shows meaningful information."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        lesson_str = str(lesson)
        self.assertIn(self.teacher.get_full_name(), lesson_str)
        self.assertIn(self.student.get_full_name(), lesson_str)
        self.assertIn(self.subject.name, lesson_str)

    def test_lesson_string_with_null_student(self):
        """Lesson.__str__() handles null student gracefully."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=None,
            subject=self.subject,
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        lesson_str = str(lesson)
        self.assertIn("(No student)", lesson_str)
