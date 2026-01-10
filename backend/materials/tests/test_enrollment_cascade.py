"""
Unit tests for SubjectEnrollment cascade protection (C2).
"""

import pytest
from django.db.models.deletion import ProtectedError
from django.contrib.auth import get_user_model
from django.test import TestCase
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


class SubjectEnrollmentCascadeProtectTests(TestCase):
    """Test SubjectEnrollment PROTECT constraints on User and Subject."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(
            name="English",
            description="English Language",
            color="#00FF00"
        )
        self.teacher = User.objects.create(
            username="teacher2",
            first_name="Bob",
            last_name="Johnson",
            role="teacher"
        )
        self.student = User.objects.create(
            username="student2",
            first_name="Alice",
            last_name="Williams",
            role="student"
        )

    def test_cannot_delete_student_with_enrollment(self):
        """Student with active enrollments cannot be deleted - ProtectedError."""
        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        with self.assertRaises(ProtectedError):
            self.student.delete()

    def test_cannot_delete_teacher_with_enrollments(self):
        """Teacher with active enrollments cannot be deleted - ProtectedError."""
        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        with self.assertRaises(ProtectedError):
            self.teacher.delete()

    def test_cannot_delete_subject_with_enrollments(self):
        """Subject with active enrollments cannot be deleted - ProtectedError."""
        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        with self.assertRaises(ProtectedError):
            self.subject.delete()

    def test_can_delete_inactive_enrollment_subject(self):
        """Subject can be deleted after all enrollments are marked inactive."""
        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="dropped",
            is_active=False
        )

        # Should be able to delete since is_active=False
        subject_id = self.subject.id
        self.subject.delete()

        self.assertFalse(Subject.objects.filter(id=subject_id).exists())

    def test_multiple_enrollments_protect_student_delete(self):
        """Student with multiple enrollments cannot be deleted."""
        for i in range(3):
            subject = Subject.objects.create(
                name="Subject{}".format(i),
                color="#000000"
            )
            SubjectEnrollment.objects.create(
                student=self.student,
                subject=subject,
                teacher=self.teacher,
                status="active",
                is_active=True
            )

        with self.assertRaises(ProtectedError):
            self.student.delete()

    def test_delete_all_enrollments_then_delete_student(self):
        """Can delete student after all their enrollments are removed."""
        for i in range(2):
            subject = Subject.objects.create(name="Subject{}".format(i))
            SubjectEnrollment.objects.create(
                student=self.student,
                subject=subject,
                teacher=self.teacher,
                status="active",
                is_active=True
            )

        # Delete all enrollments
        SubjectEnrollment.objects.filter(student=self.student).delete()

        # Now should be able to delete student
        student_id = self.student.id
        self.student.delete()

        self.assertFalse(User.objects.filter(id=student_id).exists())
