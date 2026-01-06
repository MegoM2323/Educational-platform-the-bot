import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from materials.permissions import (
    StudentEnrollmentPermission,
    MaterialSubmissionEnrollmentPermission,
)
from materials.models import SubjectEnrollment, Subject, Material
from accounts.models import StudentProfile

User = get_user_model()


class TestStudentEnrollmentPermission(TestCase):
    """Tests for StudentEnrollmentPermission"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = StudentEnrollmentPermission()

        self.subject = Subject.objects.create(name="Mathematics")

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.inactive_student = User.objects.create_user(
            username="inactive_student",
            email="inactive_student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )

        # Create enrollment
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True,
        )

        # Create material
        self.material = Material.objects.create(
            title="Test Material",
            subject=self.subject,
            author=self.teacher,
            status="active",
        )

    def test_inactive_user_denied_access(self):
        """Test: is_active check - inactive student denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_student
        assert self.permission.has_object_permission(request, None, self.material) is False

    def test_admin_can_access_any_material(self):
        """Test: admin can access any material"""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass123",
        )
        request = self.factory.get("/")
        request.user = admin
        assert self.permission.has_object_permission(request, None, self.material) is True

    def test_staff_can_access_any_material(self):
        """Test: staff can access any material"""
        staff = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_staff=True,
        )
        request = self.factory.get("/")
        request.user = staff
        assert self.permission.has_object_permission(request, None, self.material) is True

    def test_teacher_can_access_own_material(self):
        """Test: teacher can access their own material"""
        request = self.factory.get("/")
        request.user = self.teacher
        assert self.permission.has_object_permission(request, None, self.material) is True

    def test_enrolled_student_can_access_material(self):
        """Test: enrolled student can access material"""
        request = self.factory.get("/")
        request.user = self.student
        self.material.assigned_to.add(self.student)
        assert self.permission.has_object_permission(request, None, self.material) is True

    def test_public_material_accessible_to_all_active_students(self):
        """Test: public material accessible to all active students"""
        public_material = Material.objects.create(
            title="Public Material",
            subject=self.subject,
            author=self.teacher,
            status="active",
            is_public=True,
        )

        other_student = User.objects.create_user(
            username="other_student",
            email="other_student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

        request = self.factory.get("/")
        request.user = other_student
        # Student without enrollment can still access public material
        assert self.permission.has_object_permission(request, None, public_material) is True

    def test_deactivated_users_denied_access(self):
        """Test: deactivated users cannot access materials"""
        request = self.factory.get("/")
        request.user = self.inactive_student
        assert self.permission.has_object_permission(request, None, self.material) is False

    def test_tutor_can_access_student_materials(self):
        """Test: tutor can access materials of their students"""
        tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

        # Create student with this tutor
        StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            tutor=tutor,
        )

        request = self.factory.get("/")
        request.user = tutor
        assert self.permission.has_object_permission(request, None, self.material) is True


class TestMaterialSubmissionEnrollmentPermission(TestCase):
    """Tests for MaterialSubmissionEnrollmentPermission"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = MaterialSubmissionEnrollmentPermission()

        self.subject = Subject.objects.create(name="Mathematics")

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.inactive_student = User.objects.create_user(
            username="inactive_student",
            email="inactive_student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

    def test_only_students_can_submit(self):
        """Test: only students can submit (POST)"""
        request = self.factory.post("/")
        request.user = self.tutor
        request.method = "POST"
        assert self.permission.has_permission(request, None) is False

    def test_teacher_cannot_submit_materials(self):
        """Test: teachers/tutors cannot submit answers on their own materials"""
        request = self.factory.post("/")
        request.user = self.teacher
        request.method = "POST"
        assert self.permission.has_permission(request, None) is False

    def test_tutor_cannot_submit_materials(self):
        """Test: tutors cannot submit answers"""
        request = self.factory.post("/")
        request.user = self.tutor
        request.method = "POST"
        assert self.permission.has_permission(request, None) is False

    def test_inactive_student_denied_submission(self):
        """Test: is_active check - inactive student cannot submit"""
        request = self.factory.post("/")
        request.user = self.inactive_student
        request.method = "POST"
        assert self.permission.has_permission(request, None) is False

    def test_active_student_can_submit(self):
        """Test: active student can submit"""
        request = self.factory.post("/")
        request.user = self.student
        request.method = "POST"
        assert self.permission.has_permission(request, None) is True

    def test_student_can_view_submission(self):
        """Test: student can view (GET) submissions"""
        request = self.factory.get("/")
        request.user = self.student
        request.method = "GET"
        # has_permission checks for authenticated user
        assert self.permission.has_permission(request, None) is True

    def test_inactive_student_cannot_view_submission(self):
        """Test: inactive student cannot view submissions"""
        request = self.factory.get("/")
        request.user = self.inactive_student
        request.method = "GET"
        assert self.permission.has_permission(request, None) is False

    def test_unauthenticated_user_denied(self):
        """Test: unauthenticated user denied"""
        request = self.factory.post("/")
        request.user = None
        request.method = "POST"
        assert self.permission.has_permission(request, None) is False


class TestStudentEnrollmentPermissionIntegration(TestCase):
    """Integration tests for StudentEnrollmentPermission"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = StudentEnrollmentPermission()

        self.subject = Subject.objects.create(name="Mathematics")

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True,
        )

    def test_student_enrollment_check(self):
        """Test: student enrollment is checked"""
        material = Material.objects.create(
            title="Test Material",
            subject=self.subject,
            author=self.teacher,
            status="active",
        )
        material.assigned_to.add(self.student)

        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_object_permission(request, None, material) is True

    def test_student_without_enrollment_denied(self):
        """Test: student without enrollment denied"""
        other_subject = Subject.objects.create(name="Chemistry")
        material = Material.objects.create(
            title="Chemistry Material",
            subject=other_subject,
            author=self.teacher,
            status="active",
        )
        material.assigned_to.add(self.student)

        request = self.factory.get("/")
        request.user = self.student
        # Student not enrolled in this subject
        assert self.permission.has_object_permission(request, None, material) is False


class TestDeactivatedUsersPermissions(TestCase):
    """Tests for deactivated user restrictions across permission classes"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.enrollment_permission = StudentEnrollmentPermission()
        self.submission_permission = MaterialSubmissionEnrollmentPermission()

        self.subject = Subject.objects.create(name="Mathematics")

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )

        self.deactivated_student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )

        self.enrollment = SubjectEnrollment.objects.create(
            student=self.deactivated_student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True,
        )

        self.material = Material.objects.create(
            title="Test Material",
            subject=self.subject,
            author=self.teacher,
            status="active",
        )

    def test_deactivated_student_cannot_view_materials(self):
        """Test: deactivated student cannot view materials"""
        request = self.factory.get("/")
        request.user = self.deactivated_student
        assert self.enrollment_permission.has_object_permission(request, None, self.material) is False

    def test_deactivated_student_cannot_submit_answers(self):
        """Test: deactivated student cannot submit answers"""
        request = self.factory.post("/")
        request.user = self.deactivated_student
        request.method = "POST"
        assert self.submission_permission.has_permission(request, None) is False

    def test_deactivated_student_cannot_view_submissions(self):
        """Test: deactivated student cannot view submissions"""
        request = self.factory.get("/")
        request.user = self.deactivated_student
        request.method = "GET"
        assert self.submission_permission.has_permission(request, None) is False
