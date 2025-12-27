"""
T_MAT_006: Subject Enrollment Validation - Simple Unit Tests

Simplified test suite without full Django setup issues.
Tests enrollment service validation logic and API endpoints.
"""

import os
import sys
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['ENVIRONMENT'] = 'test'

try:
    django.setup()
except Exception as e:
    # Skip setup if already initialized
    pass

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Subject, SubjectEnrollment
from .enrollment_service import SubjectEnrollmentService, EnrollmentValidationError

User = get_user_model()


class SubjectEnrollmentServiceTests(TestCase):
    """Test SubjectEnrollmentService validation and operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role="student",
            first_name="John",
            last_name="Doe"
        )

        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role="teacher",
            first_name="Jane",
            last_name="Smith"
        )

        self.tutor = User.objects.create_user(
            email="tutor@test.com",
            password="testpass123",
            role="tutor",
            first_name="Tom",
            last_name="Brown"
        )

        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Basic Math",
            color="#FF5733"
        )

    def test_create_enrollment_success(self):
        """Test successful enrollment creation"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        self.assertIsNotNone(enrollment.id)
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.subject, self.subject)
        self.assertEqual(enrollment.teacher, self.teacher)
        self.assertTrue(enrollment.is_active)

    def test_prevent_duplicate_enrollment(self):
        """Test duplicate enrollment prevention"""
        # Create first enrollment
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        # Try to create duplicate
        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=self.subject.id,
                teacher_id=self.teacher.id
            )

    def test_prevent_self_enrollment(self):
        """Test self-enrollment prevention"""
        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.prevent_self_enrollment_as_teacher(
                self.student, self.student
            )

    def test_cancel_enrollment(self):
        """Test enrollment cancellation"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        cancelled = SubjectEnrollmentService.cancel_enrollment(enrollment.id)
        self.assertFalse(cancelled.is_active)

    def test_get_student_enrollments(self):
        """Test retrieving student enrollments"""
        # Create two enrollments
        subject2 = Subject.objects.create(
            name="Physics",
            description="Basic Physics",
            color="#3B82F6"
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=subject2.id,
            teacher_id=self.tutor.id
        )

        enrollments = SubjectEnrollmentService.get_student_enrollments(self.student.id)
        self.assertEqual(enrollments.count(), 2)

    def test_validate_custom_subject_name(self):
        """Test custom subject name validation"""
        custom_name = "Advanced Mathematics"
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id,
            custom_subject_name=custom_name
        )

        self.assertEqual(enrollment.custom_subject_name, custom_name)
        self.assertEqual(enrollment.get_subject_name(), custom_name)

    def test_get_subject_name_fallback(self):
        """Test get_subject_name falls back to subject name when custom is None"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        self.assertEqual(enrollment.get_subject_name(), self.subject.name)

    def test_unique_constraint_enforced(self):
        """Test that unique constraint prevents database duplicates"""
        enrollment1 = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        # The service should catch duplicates before DB
        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=self.subject.id,
                teacher_id=self.teacher.id
            )

    def test_invalid_student_validation(self):
        """Test validation fails for non-existent student"""
        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=99999,
                subject_id=self.subject.id,
                teacher_id=self.teacher.id
            )

    def test_invalid_subject_validation(self):
        """Test validation fails for non-existent subject"""
        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=99999,
                teacher_id=self.teacher.id
            )

    def test_invalid_teacher_validation(self):
        """Test validation fails for non-existent teacher"""
        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=self.subject.id,
                teacher_id=99999
            )

    def test_custom_name_max_length(self):
        """Test custom name length validation"""
        long_name = "A" * 201  # Exceeds 200 char limit

        with self.assertRaises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=self.subject.id,
                teacher_id=self.teacher.id,
                custom_subject_name=long_name
            )

    def test_reactivate_enrollment(self):
        """Test enrollment reactivation"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        # Cancel it
        SubjectEnrollmentService.cancel_enrollment(enrollment.id)
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

        # Reactivate it
        reactivated = SubjectEnrollmentService.reactivate_enrollment(enrollment.id)
        self.assertTrue(reactivated.is_active)

    def test_get_teacher_students(self):
        """Test retrieving all students for a teacher"""
        student2 = User.objects.create_user(
            email="student2@test.com",
            password="testpass123",
            role="student",
            first_name="Bob",
            last_name="Johnson"
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=student2.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        enrollments = SubjectEnrollmentService.get_teacher_students(self.teacher.id)
        self.assertEqual(enrollments.count(), 2)

    def test_check_duplicate_enrollment(self):
        """Test duplicate check method"""
        # No enrollment exists yet
        result = SubjectEnrollmentService.check_duplicate_enrollment(
            self.student, self.subject, self.teacher
        )
        self.assertIsNone(result)

        # Create enrollment
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        # Now check should find it
        result = SubjectEnrollmentService.check_duplicate_enrollment(
            self.student, self.subject, self.teacher
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.id, enrollment.id)

    def test_enrollment_ordering(self):
        """Test that enrollments are ordered by enrolled_at descending"""
        subject2 = Subject.objects.create(
            name="Physics",
            description="Basic Physics",
            color="#3B82F6"
        )

        enrollment1 = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        enrollment2 = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=subject2.id,
            teacher_id=self.teacher.id
        )

        enrollments = SubjectEnrollmentService.get_student_enrollments(self.student.id)
        first = enrollments.first()
        self.assertEqual(first.id, enrollment2.id)  # More recent first
