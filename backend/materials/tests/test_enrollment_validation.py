"""Unit tests for SubjectEnrollment validation (M2)."""

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


class SubjectEnrollmentValidationTests(TestCase):
    """Test SubjectEnrollment validation."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="English")
        self.student = User.objects.create(username="student_valid", role="student")
        self.teacher = User.objects.create(username="teacher_valid", role="teacher")
        self.inactive_teacher = User.objects.create(
            username="inactive_teacher",
            role="teacher",
            is_active=False
        )

    def test_enrollment_clean_validates_teacher_active(self):
        """clean() validates teacher is active."""
        enrollment = SubjectEnrollment(
            student=self.student,
            subject=self.subject,
            teacher=self.inactive_teacher,
            status="active"
        )

        with self.assertRaises(ValidationError):
            enrollment.clean()

    def test_enrollment_clean_validates_teacher_role(self):
        """clean() validates teacher has TEACHER role."""
        non_teacher = User.objects.create(
            username="not_teacher",
            role="student"
        )

        enrollment = SubjectEnrollment(
            student=self.student,
            subject=self.subject,
            teacher=non_teacher,
            status="active"
        )

        with self.assertRaises(ValidationError):
            enrollment.clean()

    def test_enrollment_save_calls_full_clean(self):
        """save() calls full_clean() and validates."""
        non_teacher = User.objects.create(
            username="invalid_save_teacher",
            role="student"
        )

        enrollment = SubjectEnrollment(
            student=self.student,
            subject=self.subject,
            teacher=non_teacher,
            status="active"
        )

        with self.assertRaises(ValidationError):
            enrollment.save()

    def test_valid_enrollment_saves(self):
        """Valid enrollment saves without error."""
        enrollment = SubjectEnrollment(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        enrollment.full_clean()
        enrollment.save()

        self.assertTrue(
            SubjectEnrollment.objects.filter(id=enrollment.id).exists()
        )

    def test_enrollment_with_inactive_student(self):
        """Cannot create enrollment with inactive student."""
        inactive_student = User.objects.create(
            username="inactive_student_enroll",
            role="student",
            is_active=False
        )

        enrollment = SubjectEnrollment(
            student=inactive_student,
            subject=self.subject,
            teacher=self.teacher,
            status="active"
        )

        with self.assertRaises(ValidationError):
            enrollment.clean()
