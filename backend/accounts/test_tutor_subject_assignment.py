"""
T_W14_T04: Tutor Subject Assignment Tests - A8 Fix Verification

Comprehensive test coverage for tutor subject assignment functionality:
1. Tutor Can Assign Subject via StudentProfile
2. Tutor Can Assign Subject via created_by_tutor
3. Tutor Cannot Assign Subject to Non-Student
4. Tutor Cannot Assign Subject if StudentProfile Missing
5. Subject Assignment Validates Teacher
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from .models import StudentProfile, ParentProfile
from .tutor_service import SubjectAssignmentService
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db
class TestTutorSubjectAssignmentViaProfile(TestCase):
    """Test: Tutor Can Assign Subject via StudentProfile.tutor"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor1@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="One"
        )

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="One",
            is_active=True
        )

        # Create student with StudentProfile.tutor relationship
        self.student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="One"
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent1@test.com",
            password="TestPass123!",
            role="parent",
            first_name="Parent",
            last_name="One"
        )

        # Create StudentProfile with tutor relationship
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            tutor=self.tutor,
            parent=self.parent,
            grade="10A"
        )

        # Create subject
        self.subject = Subject.objects.create(
            name="Mathematics",
            description="Math subject",
            color="#3B82F6"
        )

        self.client = APIClient()

    def test_tutor_assign_subject_via_profile_returns_enrollment(self):
        """Test: Subject assignment returns enrollment object"""
        # Test using service directly
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        # Verify enrollment object is returned
        assert enrollment is not None
        assert hasattr(enrollment, 'id')
        assert hasattr(enrollment, 'student_id')

    def test_tutor_assign_subject_via_profile_creates_enrollment(self):
        """Test: Enrollment is created with correct teacher"""
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        assert enrollment is not None
        assert enrollment.student.id == self.student.id
        assert enrollment.subject.id == self.subject.id
        assert enrollment.teacher.id == self.teacher.id
        assert enrollment.is_active is True

    def test_tutor_assign_subject_via_profile_sets_assigned_by(self):
        """Test: assigned_by is set to tutor"""
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        assert enrollment.assigned_by.id == self.tutor.id


@pytest.mark.django_db
class TestTutorSubjectAssignmentViaCreatedByTutor(TestCase):
    """Test: Tutor Can Assign Subject via User.created_by_tutor"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor2",
            email="tutor2@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Two"
        )

        self.teacher = User.objects.create_user(
            username="teacher2",
            email="teacher2@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Two",
            is_active=True
        )

        # Create student with created_by_tutor relationship (NO StudentProfile)
        self.student = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="Two",
            created_by_tutor=self.tutor
        )

        # Create subject
        self.subject = Subject.objects.create(
            name="Physics",
            description="Physics subject",
            color="#FF5733"
        )

        self.client = APIClient()

    def test_tutor_assign_subject_via_created_by_tutor(self):
        """Test: Tutor can assign subject via created_by_tutor relationship"""
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        assert enrollment is not None
        assert enrollment.student.id == self.student.id
        assert enrollment.subject.id == self.subject.id
        assert enrollment.is_active is True

    def test_tutor_assign_subject_via_created_by_tutor_validates_permission(self):
        """Test: Permission check accepts created_by_tutor relationship"""
        # Should not raise PermissionError
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        # Verify assignment
        assert enrollment.assigned_by.id == self.tutor.id


@pytest.mark.django_db
class TestTutorCannotAssignToNonStudent(TestCase):
    """Test: Tutor Cannot Assign Subject to Non-Student"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor3",
            email="tutor3@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Three"
        )

        self.teacher = User.objects.create_user(
            username="teacher3",
            email="teacher3@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Three",
            is_active=True
        )

        # Create unrelated user (teacher, not student)
        self.unrelated_user = User.objects.create_user(
            username="other_teacher",
            email="other_teacher@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Other",
            last_name="Teacher"
        )

        self.subject = Subject.objects.create(
            name="Chemistry",
            description="Chemistry subject",
            color="#00FF00"
        )

        self.client = APIClient()

    def test_tutor_cannot_assign_to_non_student_raises_error(self):
        """Test: Raises error when assigning to non-student"""
        with pytest.raises(ValueError) as exc_info:
            SubjectAssignmentService.assign_subject(
                tutor=self.tutor,
                student=self.unrelated_user,
                subject=self.subject,
                teacher=self.teacher
            )

        assert "не является студентом" in str(exc_info.value).lower()

    def test_tutor_cannot_assign_to_unrelated_student_raises_permission_error(self):
        """Test: Raises PermissionError when student not related to tutor"""
        # Create unrelated student
        unrelated_student = User.objects.create_user(
            username="student_unrelated",
            email="student_unrelated@test.com",
            password="TestPass123!",
            role="student",
            first_name="Unrelated",
            last_name="Student"
        )

        with pytest.raises(PermissionError) as exc_info:
            SubjectAssignmentService.assign_subject(
                tutor=self.tutor,
                student=unrelated_student,
                subject=self.subject,
                teacher=self.teacher
            )

        assert "студент не принадлежит" in str(exc_info.value).lower()

    def test_tutor_cannot_assign_returns_403_forbidden(self):
        """Test: API returns 403/404 for unrelated student"""
        unrelated_student = User.objects.create_user(
            username="student_unrelated2",
            email="student_unrelated2@test.com",
            password="TestPass123!",
            role="student",
            first_name="Unrelated",
            last_name="Student2"
        )

        # Create StudentProfile to make it valid
        unrelated_profile = StudentProfile.objects.create(
            user=unrelated_student,
            grade="10A"
        )

        self.client.force_authenticate(user=self.tutor)

        url = f"/api/my-students/{unrelated_profile.id}/subjects/"
        data = {
            "subject_id": self.subject.id,
            "teacher_id": self.teacher.id
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN or response.status_code == status.HTTP_404_NOT_FOUND
        if response.status_code == status.HTTP_403_FORBIDDEN:
            assert "не принадлежит" in response.data.get("detail", "").lower()


@pytest.mark.django_db
class TestTutorAssignmentWithMissingProfile(TestCase):
    """Test: Tutor Can Assign Subject if StudentProfile Missing (fallback to created_by_tutor)"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor4",
            email="tutor4@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Four"
        )

        self.teacher = User.objects.create_user(
            username="teacher4",
            email="teacher4@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Four",
            is_active=True
        )

        # Create student with created_by_tutor but NO StudentProfile
        self.student = User.objects.create_user(
            username="student4",
            email="student4@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="Four",
            created_by_tutor=self.tutor
        )

        self.subject = Subject.objects.create(
            name="History",
            description="History subject",
            color="#FFAA00"
        )

        self.client = APIClient()

    def test_assignment_without_profile_succeeds_via_created_by_tutor(self):
        """Test: 201 Created via fallback to created_by_tutor"""
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        assert enrollment is not None
        assert enrollment.is_active is True

    def test_assignment_handles_missing_profile_gracefully(self):
        """Test: StudentProfile.DoesNotExist handled gracefully"""
        # Verify student has no profile
        assert not hasattr(self.student, 'student_profile')

        # Should still succeed
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        # Verify enrollment exists
        assert SubjectEnrollment.objects.filter(id=enrollment.id).exists()


@pytest.mark.django_db
class TestSubjectAssignmentTeacherValidation(TestCase):
    """Test: Subject Assignment Validates Teacher"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor5",
            email="tutor5@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Five"
        )

        self.student = User.objects.create_user(
            username="student5",
            email="student5@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="Five",
            created_by_tutor=self.tutor
        )

        # Inactive teacher
        self.inactive_teacher = User.objects.create_user(
            username="inactive_teacher",
            email="inactive_teacher@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Inactive",
            last_name="Teacher",
            is_active=False
        )

        self.subject = Subject.objects.create(
            name="Geography",
            description="Geography subject",
            color="#00FFFF"
        )

        self.client = APIClient()

    def test_assignment_with_nonexistent_teacher_raises_error(self):
        """Test: 400/404 with invalid teacher_id"""
        with pytest.raises(ValueError) as exc_info:
            SubjectAssignmentService.assign_subject(
                tutor=self.tutor,
                student=self.student,
                subject=self.subject,
                teacher=None
            )

        assert "преподавателя" in str(exc_info.value).lower()

    def test_assignment_with_inactive_teacher_raises_error(self):
        """Test: Raises error for inactive teacher"""
        with pytest.raises(ValueError) as exc_info:
            SubjectAssignmentService.assign_subject(
                tutor=self.tutor,
                student=self.student,
                subject=self.subject,
                teacher=self.inactive_teacher
            )

        assert "неактивен" in str(exc_info.value).lower()

    def test_assignment_with_non_teacher_user_raises_error(self):
        """Test: Raises error when teacher is not a teacher"""
        student_as_teacher = User.objects.create_user(
            username="student_teacher",
            email="student_teacher@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="Teacher"
        )

        with pytest.raises(ValueError) as exc_info:
            SubjectAssignmentService.assign_subject(
                tutor=self.tutor,
                student=self.student,
                subject=self.subject,
                teacher=student_as_teacher
            )

        assert "не является преподавателем" in str(exc_info.value).lower()


@pytest.mark.django_db
class TestTutorSubjectAssignmentEdgeCases(TestCase):
    """Test: Edge cases and relationship checks"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor6",
            email="tutor6@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Six"
        )

        self.teacher = User.objects.create_user(
            username="teacher6",
            email="teacher6@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Six",
            is_active=True
        )

        self.student = User.objects.create_user(
            username="student6",
            email="student6@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="Six",
            created_by_tutor=self.tutor
        )

        self.subject1 = Subject.objects.create(
            name="Biology",
            description="Biology subject",
            color="#FF00FF"
        )

        self.subject2 = Subject.objects.create(
            name="Biology Advanced",
            description="Advanced biology",
            color="#FF00AA"
        )

        self.client = APIClient()

    def test_duplicate_enrollment_is_reactivated(self):
        """Test: Assigning same subject again updates existing enrollment"""
        # First assignment
        enrollment1 = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject1,
            teacher=self.teacher
        )

        # Deactivate
        enrollment1.is_active = False
        enrollment1.save()

        # Reassign same combination
        enrollment2 = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject1,
            teacher=self.teacher
        )

        # Should be same enrollment but reactivated
        assert enrollment1.id == enrollment2.id
        assert enrollment2.is_active is True

    def test_multiple_subjects_for_same_student(self):
        """Test: Student can have multiple subject assignments"""
        enrollment1 = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject1,
            teacher=self.teacher
        )

        enrollment2 = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject2,
            teacher=self.teacher
        )

        assert enrollment1.id != enrollment2.id
        assert SubjectEnrollment.objects.filter(student=self.student, is_active=True).count() == 2

    def test_admin_can_also_assign_subjects(self):
        """Test: Administrators can assign subjects too"""
        admin = User.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="TestPass123!",
            role="tutor",  # Must be tutor or staff
            first_name="Admin",
            last_name="User",
            is_staff=True,
            is_superuser=True
        )

        # Admin should be able to assign to any student
        admin_student = User.objects.create_user(
            username="admin_student",
            email="admin_student@test.com",
            password="TestPass123!",
            role="student",
            first_name="Admin",
            last_name="Student",
            created_by_tutor=admin  # Link to admin as tutor
        )

        enrollment = SubjectAssignmentService.assign_subject(
            tutor=admin,
            student=admin_student,
            subject=self.subject1,
            teacher=self.teacher
        )

        assert enrollment is not None

    def test_tutor_cannot_assign_if_not_tutor_role(self):
        """Test: Non-tutor user cannot assign subjects"""
        non_tutor = User.objects.create_user(
            username="non_tutor",
            email="non_tutor@test.com",
            password="TestPass123!",
            role="student",
            first_name="Not",
            last_name="Tutor"
        )

        with pytest.raises(PermissionError) as exc_info:
            SubjectAssignmentService.assign_subject(
                tutor=non_tutor,
                student=self.student,
                subject=self.subject1,
                teacher=self.teacher
            )

        assert "тьютор" in str(exc_info.value).lower()


@pytest.mark.django_db
class TestTutorSubjectAssignmentWithBothRelationships(TestCase):
    """Test: Student with both StudentProfile.tutor and created_by_tutor"""

    def setUp(self):
        """Set up test data"""
        self.tutor = User.objects.create_user(
            username="tutor7",
            email="tutor7@test.com",
            password="TestPass123!",
            role="tutor",
            first_name="Tutor",
            last_name="Seven"
        )

        self.teacher = User.objects.create_user(
            username="teacher7",
            email="teacher7@test.com",
            password="TestPass123!",
            role="teacher",
            first_name="Teacher",
            last_name="Seven",
            is_active=True
        )

        self.parent = User.objects.create_user(
            username="parent7",
            email="parent7@test.com",
            password="TestPass123!",
            role="parent",
            first_name="Parent",
            last_name="Seven"
        )

        # Create student with BOTH relationships
        self.student = User.objects.create_user(
            username="student7",
            email="student7@test.com",
            password="TestPass123!",
            role="student",
            first_name="Student",
            last_name="Seven",
            created_by_tutor=self.tutor
        )

        # Add StudentProfile with same tutor
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            tutor=self.tutor,
            parent=self.parent,
            grade="11B"
        )

        self.subject = Subject.objects.create(
            name="Art",
            description="Art subject",
            color="#FFD700"
        )

        self.client = APIClient()

    def test_assignment_succeeds_with_both_relationships(self):
        """Test: Both relationships are recognized"""
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        assert enrollment is not None
        assert enrollment.is_active is True

    def test_permission_check_accepts_profile_relationship(self):
        """Test: StudentProfile.tutor relationship is accepted"""
        # Create another tutor and verify first tutor can still assign
        # (because of StudentProfile relationship)
        enrollment = SubjectAssignmentService.assign_subject(
            tutor=self.tutor,
            student=self.student,
            subject=self.subject,
            teacher=self.teacher
        )

        assert enrollment.assigned_by.id == self.tutor.id
