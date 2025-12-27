"""
T_MAT_006: Subject Enrollment Validation Test Suite

Comprehensive test coverage for subject enrollment:
1. Duplicate enrollment prevention
2. User role validation
3. Subject existence verification
4. Atomic enrollment operations
5. Enrollment lifecycle management
6. Self-enrollment prevention
7. Permission checks
8. Edge cases
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from rest_framework import status

from .models import Subject, SubjectEnrollment, TeacherSubject
from .enrollment_service import SubjectEnrollmentService, EnrollmentValidationError

User = get_user_model()


@pytest.mark.django_db
class TestEnrollmentValidation(TestCase):
    """Test enrollment validation functionality"""

    def setUp(self):
        """Set up test data"""
        # Create users with different roles
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

        self.other_student = User.objects.create_user(
            email="other_student@test.com",
            password="testpass123",
            role="student",
            first_name="Bob",
            last_name="Johnson"
        )

        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            role="admin",
            first_name="Admin",
            last_name="User"
        )

        # Create subjects
        self.subject1 = Subject.objects.create(
            name="Mathematics",
            description="Basic math",
            color="#FF5733"
        )

        self.subject2 = Subject.objects.create(
            name="Physics",
            description="Basic physics",
            color="#3B82F6"
        )

        self.client = APIClient()

    # Test 1: Validate user role
    def test_validate_student_role(self):
        """Test validating student role"""
        assert SubjectEnrollmentService.validate_user_role(self.student)

    def test_validate_teacher_role(self):
        """Test validating teacher role"""
        assert SubjectEnrollmentService.validate_user_role(self.teacher)

    def test_validate_tutor_role(self):
        """Test validating tutor role"""
        assert SubjectEnrollmentService.validate_user_role(self.tutor)

    def test_validate_invalid_role(self):
        """Test validation fails for invalid role"""
        invalid_user = User.objects.create_user(
            email="invalid@test.com",
            password="testpass123",
            role="invalid",
            first_name="Invalid",
            last_name="User"
        )

        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.validate_user_role(invalid_user)

    # Test 2: Validate subject exists
    def test_validate_subject_exists(self):
        """Test subject existence validation"""
        subject = SubjectEnrollmentService.validate_subject_exists(self.subject1.id)
        assert subject.id == self.subject1.id

    def test_validate_subject_not_exists(self):
        """Test validation fails for non-existent subject"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.validate_subject_exists(99999)

    # Test 3: Validate teacher exists
    def test_validate_teacher_exists(self):
        """Test teacher existence validation"""
        teacher = SubjectEnrollmentService.validate_teacher_exists(self.teacher.id)
        assert teacher.id == self.teacher.id

    def test_validate_teacher_with_tutor_role(self):
        """Test tutor is accepted as teacher"""
        teacher = SubjectEnrollmentService.validate_teacher_exists(self.tutor.id)
        assert teacher.id == self.tutor.id

    def test_validate_teacher_not_exists(self):
        """Test validation fails for non-existent teacher"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.validate_teacher_exists(99999)

    def test_validate_student_as_teacher_fails(self):
        """Test validation fails if student is treated as teacher"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.validate_teacher_exists(self.student.id)

    # Test 4: Validate student exists
    def test_validate_student_exists(self):
        """Test student existence validation"""
        student = SubjectEnrollmentService.validate_student_exists(self.student.id)
        assert student.id == self.student.id

    def test_validate_student_not_exists(self):
        """Test validation fails for non-existent student"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.validate_student_exists(99999)

    # Test 5: Prevent self-enrollment
    def test_prevent_self_enrollment(self):
        """Test that user cannot enroll as both student and teacher"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.prevent_self_enrollment_as_teacher(
                self.student, self.student
            )

    def test_prevent_self_enrollment_teacher(self):
        """Test teacher cannot enroll self"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.prevent_self_enrollment_as_teacher(
                self.teacher, self.teacher
            )

    def test_different_users_pass(self):
        """Test different users pass self-enrollment check"""
        result = SubjectEnrollmentService.prevent_self_enrollment_as_teacher(
            self.student, self.teacher
        )
        # Should not raise exception

    # Test 6: Check duplicate enrollment
    def test_check_duplicate_enrollment_not_exists(self):
        """Test duplicate check when enrollment doesn't exist"""
        result = SubjectEnrollmentService.check_duplicate_enrollment(
            self.student, self.subject1, self.teacher
        )
        assert result is None

    def test_check_duplicate_enrollment_exists(self):
        """Test duplicate check when enrollment exists"""
        # Create an enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject1,
            teacher=self.teacher
        )

        # Check for duplicate
        result = SubjectEnrollmentService.check_duplicate_enrollment(
            self.student, self.subject1, self.teacher
        )
        assert result is not None
        assert result.id == enrollment.id

    # Test 7: Create enrollment successfully
    def test_create_enrollment_success(self):
        """Test successful enrollment creation"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        assert enrollment.id is not None
        assert enrollment.student == self.student
        assert enrollment.subject == self.subject1
        assert enrollment.teacher == self.teacher
        assert enrollment.is_active is True

    def test_create_enrollment_with_custom_name(self):
        """Test enrollment creation with custom subject name"""
        custom_name = "Advanced Mathematics"
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id,
            custom_subject_name=custom_name
        )

        assert enrollment.custom_subject_name == custom_name
        assert enrollment.get_subject_name() == custom_name

    def test_create_enrollment_with_assigned_by(self):
        """Test enrollment creation with assigned_by user"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id,
            assigned_by=self.tutor
        )

        assert enrollment.assigned_by == self.tutor

    def test_create_enrollment_duplicate_fails(self):
        """Test duplicate enrollment prevention"""
        # Create first enrollment
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        # Try to create duplicate
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=self.subject1.id,
                teacher_id=self.teacher.id
            )

    def test_create_enrollment_invalid_student(self):
        """Test enrollment fails with invalid student"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=99999,
                subject_id=self.subject1.id,
                teacher_id=self.teacher.id
            )

    def test_create_enrollment_invalid_subject(self):
        """Test enrollment fails with invalid subject"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=99999,
                teacher_id=self.teacher.id
            )

    def test_create_enrollment_invalid_teacher(self):
        """Test enrollment fails with invalid teacher"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.create_enrollment(
                student_id=self.student.id,
                subject_id=self.subject1.id,
                teacher_id=99999
            )

    # Test 8: Cancel enrollment
    def test_cancel_enrollment_success(self):
        """Test successful enrollment cancellation"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        cancelled = SubjectEnrollmentService.cancel_enrollment(enrollment.id)
        assert cancelled.is_active is False

    def test_cancel_already_inactive(self):
        """Test cancelling already inactive enrollment fails"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.cancel_enrollment(enrollment.id)

        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.cancel_enrollment(enrollment.id)

    def test_cancel_nonexistent_enrollment(self):
        """Test cancelling non-existent enrollment fails"""
        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.cancel_enrollment(99999)

    # Test 9: Reactivate enrollment
    def test_reactivate_enrollment_success(self):
        """Test successful enrollment reactivation"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.cancel_enrollment(enrollment.id)
        reactivated = SubjectEnrollmentService.reactivate_enrollment(enrollment.id)
        assert reactivated.is_active is True

    def test_reactivate_active_enrollment_fails(self):
        """Test reactivating active enrollment fails"""
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        with pytest.raises(EnrollmentValidationError):
            SubjectEnrollmentService.reactivate_enrollment(enrollment.id)

    # Test 10: Get student enrollments
    def test_get_student_enrollments(self):
        """Test retrieving all student enrollments"""
        # Create multiple enrollments
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject2.id,
            teacher_id=self.tutor.id
        )

        enrollments = SubjectEnrollmentService.get_student_enrollments(self.student.id)
        assert enrollments.count() == 2

    def test_get_student_enrollments_exclude_inactive(self):
        """Test inactive enrollments are excluded by default"""
        enrollment1 = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        enrollment2 = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject2.id,
            teacher_id=self.tutor.id
        )

        # Cancel one enrollment
        SubjectEnrollmentService.cancel_enrollment(enrollment1.id)

        # Get active only (default)
        active_enrollments = SubjectEnrollmentService.get_student_enrollments(
            self.student.id,
            include_inactive=False
        )
        assert active_enrollments.count() == 1

    def test_get_student_enrollments_include_inactive(self):
        """Test including inactive enrollments"""
        enrollment1 = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        enrollment2 = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject2.id,
            teacher_id=self.tutor.id
        )

        # Cancel one enrollment
        SubjectEnrollmentService.cancel_enrollment(enrollment1.id)

        # Get all including inactive
        all_enrollments = SubjectEnrollmentService.get_student_enrollments(
            self.student.id,
            include_inactive=True
        )
        assert all_enrollments.count() == 2

    # Test 11: Get teacher students
    def test_get_teacher_students(self):
        """Test retrieving all students for a teacher"""
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=self.other_student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        enrollments = SubjectEnrollmentService.get_teacher_students(self.teacher.id)
        assert enrollments.count() == 2

    def test_get_teacher_students_by_subject(self):
        """Test retrieving students for a teacher filtered by subject"""
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject1.id,
            teacher_id=self.teacher.id
        )

        SubjectEnrollmentService.create_enrollment(
            student_id=self.other_student.id,
            subject_id=self.subject2.id,
            teacher_id=self.teacher.id
        )

        # Get students for subject1 only
        enrollments = SubjectEnrollmentService.get_teacher_students(
            self.teacher.id,
            subject_id=self.subject1.id
        )
        assert enrollments.count() == 1
        assert enrollments.first().student == self.student


@pytest.mark.django_db
class TestEnrollmentAPI(TransactionTestCase):
    """Test enrollment API endpoints"""

    def setUp(self):
        """Set up test data"""
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

        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Basic math",
            color="#FF5733"
        )

        self.client = APIClient()

    def test_enroll_subject_success(self):
        """Test successful enrollment via API"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            f'/api/materials/subjects/{self.subject.id}/enroll/',
            {
                'student_id': self.student.id,
                'teacher_id': self.teacher.id,
                'custom_subject_name': 'Advanced Math'
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['enrollment']['student'] == self.student.id

    def test_enroll_subject_duplicate_fails(self):
        """Test duplicate enrollment fails"""
        self.client.force_authenticate(user=self.teacher)

        # First enrollment
        self.client.post(
            f'/api/materials/subjects/{self.subject.id}/enroll/',
            {
                'student_id': self.student.id,
                'teacher_id': self.teacher.id
            }
        )

        # Duplicate enrollment attempt
        response = self.client.post(
            f'/api/materials/subjects/{self.subject.id}/enroll/',
            {
                'student_id': self.student.id,
                'teacher_id': self.teacher.id
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unenroll_subject_success(self):
        """Test successful unenrollment via API"""
        # Create enrollment
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.delete(
            f'/api/materials/subjects/{self.subject.id}/unenroll/?enrollment_id={enrollment.id}'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

    def test_my_enrollments_endpoint(self):
        """Test getting current user's enrollments"""
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/materials/subjects/my-enrollments/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['count'] == 1

    def test_enrollment_status_endpoint(self):
        """Test checking enrollment status"""
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            f'/api/materials/subjects/{self.subject.id}/enrollment-status/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['enrolled'] is True

    def test_enrollment_status_not_enrolled(self):
        """Test enrollment status when not enrolled"""
        self.client.force_authenticate(user=self.student)

        response = self.client.get(
            f'/api/materials/subjects/{self.subject.id}/enrollment-status/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['enrolled'] is False

    def test_teacher_students_endpoint(self):
        """Test getting teacher's students"""
        SubjectEnrollmentService.create_enrollment(
            student_id=self.student.id,
            subject_id=self.subject.id,
            teacher_id=self.teacher.id
        )

        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f'/api/materials/teachers/{self.teacher.id}/students/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
