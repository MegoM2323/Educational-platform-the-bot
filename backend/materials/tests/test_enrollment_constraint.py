"""Unit tests for SubjectEnrollment constraint fixes (C5)."""

import pytest
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.test import TestCase
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


class SubjectEnrollmentConstraintTests(TestCase):
    """Test SubjectEnrollment constraint logic."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Physics", color="#FF0000")
        self.teacher = User.objects.create(username="teacher_constraint", role="teacher")
        self.student = User.objects.create(username="student_constraint", role="student")

    def test_can_reenroll_after_dropout(self):
        """Student can re-enroll after status=DROPPED."""
        enrollment1 = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="dropped",
            is_active=False
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        self.assertNotEqual(enrollment1.id, enrollment2.id)

    def test_cannot_have_multiple_active_enrollments(self):
        """Cannot have 2 active enrollments for same student+subject."""
        enrollment1 = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        with self.assertRaises(IntegrityError):
            enrollment2 = SubjectEnrollment.objects.create(
                student=self.student,
                subject=self.subject,
                teacher=self.teacher,
                status="active",
                is_active=True
            )

    def test_can_have_multiple_inactive_enrollments(self):
        """Can have multiple inactive enrollments for same student+subject."""
        enrollment1 = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="completed",
            is_active=False
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="dropped",
            is_active=False
        )

        self.assertNotEqual(enrollment1.id, enrollment2.id)
