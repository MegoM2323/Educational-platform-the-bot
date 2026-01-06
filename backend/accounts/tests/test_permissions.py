import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from rest_framework.test import APIRequestFactory

from accounts.permissions import (
    IsTutorOrAdmin,
    TutorCanManageStudentProfiles,
    IsStudentOwner,
    IsStaffOrAdmin,
    IsStudent,
    IsTeacher,
    IsTutor,
    IsParent,
    can_view_private_fields,
    get_private_fields_for_role,
)
from accounts.models import StudentProfile

User = get_user_model()


class TestCanViewPrivateFields(TestCase):
    """Tests for can_view_private_fields() function"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass123",
        )
        self.inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )

    def test_inactive_viewer_cannot_see_private_fields(self):
        """Test: is_active check - inactive user cannot see private fields"""
        result = can_view_private_fields(self.inactive_user, self.student, "student")
        assert result is False

    def test_admin_can_see_student_private_fields(self):
        """Test: admin sees all private fields"""
        result = can_view_private_fields(self.admin, self.student, "student")
        assert result is True

    def test_staff_can_see_student_private_fields(self):
        """Test: staff user (is_staff=True) sees private fields"""
        staff = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_staff=True,
        )
        result = can_view_private_fields(staff, self.student, "student")
        assert result is True

    def test_owner_cannot_see_own_private_fields(self):
        """Test: owner of profile does not see their own private fields"""
        result = can_view_private_fields(self.student, self.student, "student")
        assert result is False

    def test_teacher_can_see_student_private_fields(self):
        """Test: teacher sees student's private fields (goal, tutor, parent)"""
        result = can_view_private_fields(self.teacher, self.student, "student")
        assert result is True

    def test_tutor_can_see_student_private_fields(self):
        """Test: tutor sees student's private fields"""
        result = can_view_private_fields(self.tutor, self.student, "student")
        assert result is True

    def test_student_cannot_see_other_student_private_fields(self):
        """Test: student cannot see other student's private fields"""
        other_student = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        result = can_view_private_fields(self.student, other_student, "student")
        assert result is False

    def test_parent_cannot_see_student_private_fields(self):
        """Test: parent cannot see student's private fields"""
        parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
        )
        result = can_view_private_fields(parent, self.student, "student")
        assert result is False

    def test_admin_can_see_teacher_private_fields(self):
        """Test: admin sees teacher's private fields (bio, experience_years)"""
        result = can_view_private_fields(self.admin, self.teacher, "teacher")
        assert result is True

    def test_teacher_cannot_see_other_teacher_private_fields(self):
        """Test: teacher cannot see other teacher's private fields"""
        other_teacher = User.objects.create_user(
            username="teacher2",
            email="teacher2@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )
        result = can_view_private_fields(self.teacher, other_teacher, "teacher")
        assert result is False

    def test_parent_has_no_private_fields(self):
        """Test: parent profile has no private fields"""
        parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
        )
        result = can_view_private_fields(self.teacher, parent, "parent")
        assert result is False  # Parent has no private fields


class TestGetPrivateFieldsForRole(TestCase):
    """Tests for get_private_fields_for_role() function"""

    def test_student_private_fields(self):
        fields = get_private_fields_for_role(User.Role.STUDENT)
        assert "goal" in fields
        assert "tutor" in fields
        assert "parent" in fields
        assert len(fields) == 3

    def test_teacher_private_fields(self):
        fields = get_private_fields_for_role(User.Role.TEACHER)
        assert "bio" in fields
        assert "experience_years" in fields
        assert len(fields) == 2

    def test_tutor_private_fields(self):
        fields = get_private_fields_for_role(User.Role.TUTOR)
        assert "bio" in fields
        assert "experience_years" in fields
        assert len(fields) == 2

    def test_parent_private_fields_empty(self):
        fields = get_private_fields_for_role(User.Role.PARENT)
        assert fields == []


class TestIsStaffOrAdminPermission(TestCase):
    """Tests for IsStaffOrAdmin permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsStaffOrAdmin()

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_staff=True,
            is_active=True,
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass123",
        )

    def test_staff_user_has_permission(self):
        """Test: staff user (is_staff=True) has access"""
        request = self.factory.get("/")
        request.user = self.staff
        assert self.permission.has_permission(request, None) is True

    def test_superuser_has_permission(self):
        """Test: superuser has access"""
        request = self.factory.get("/")
        request.user = self.admin
        assert self.permission.has_permission(request, None) is True

    def test_tutor_denied_permission(self):
        """Test: TUTOR does NOT have access (not admin-only)"""
        request = self.factory.get("/")
        request.user = self.tutor
        assert self.permission.has_permission(request, None) is False

    def test_student_denied_permission(self):
        """Test: student denied access"""
        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_permission(request, None) is False

    def test_inactive_user_denied_permission(self):
        """Test: inactive user denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_user
        assert self.permission.has_permission(request, None) is False

    def test_unauthenticated_user_denied_permission(self):
        """Test: unauthenticated user denied access"""
        request = self.factory.get("/")
        request.user = None
        assert self.permission.has_permission(request, None) is False


class TestIsTutorOrAdminPermission(TestCase):
    """Tests for IsTutorOrAdmin permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsTutorOrAdmin()

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass123",
        )

    def test_tutor_has_permission(self):
        """Test: active tutor has access"""
        request = self.factory.get("/")
        request.user = self.tutor
        assert self.permission.has_permission(request, None) is True

    def test_admin_has_permission(self):
        """Test: admin has access"""
        request = self.factory.get("/")
        request.user = self.admin
        assert self.permission.has_permission(request, None) is True

    def test_student_denied_permission(self):
        """Test: student denied access"""
        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_permission(request, None) is False

    def test_inactive_tutor_denied_permission(self):
        """Test: inactive tutor denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_tutor
        assert self.permission.has_permission(request, None) is False


class TestTutorCanManageStudentProfilesPermission(TestCase):
    """Tests for TutorCanManageStudentProfiles permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = TutorCanManageStudentProfiles()

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            tutor=self.tutor,
            grade="10",
        )

    def test_tutor_can_manage_own_students(self):
        """Test: tutor can manage their own students"""
        request = self.factory.patch("/")
        request.user = self.tutor
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_inactive_tutor_cannot_manage_students(self):
        """Test: inactive tutor denied access"""
        student2 = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        student_profile2 = StudentProfile.objects.create(
            user=student2,
            tutor=self.inactive_tutor,
            grade="10",
        )
        request = self.factory.patch("/")
        request.user = self.inactive_tutor
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, student_profile2) is False

    def test_student_can_edit_own_profile(self):
        """Test: student can edit their own profile"""
        request = self.factory.patch("/")
        request.user = self.student
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_student_cannot_edit_other_students(self):
        """Test: student cannot edit other students"""
        other_student = User.objects.create_user(
            username="other_student",
            email="other_student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        request = self.factory.patch("/")
        request.user = other_student
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is False

    def test_admin_can_manage_any_profile(self):
        """Test: admin can manage any student profile"""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass123",
        )
        request = self.factory.patch("/")
        request.user = admin
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_anyone_can_read_student_profile(self):
        """Test: all active users can read student profile"""
        other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        request = self.factory.get("/")
        request.user = other_user
        request.method = "GET"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True


class TestIsStudentOwnerPermission(TestCase):
    """Tests for IsStudentOwner permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsStudentOwner()

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.inactive_student = User.objects.create_user(
            username="inactive_student",
            email="inactive@test.com",
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
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            tutor=self.tutor,
            grade="10",
        )
        self.inactive_student_profile = StudentProfile.objects.create(
            user=self.inactive_student,
            tutor=self.tutor,
            grade="10",
        )

    def test_student_can_edit_own_profile(self):
        """Test: student can edit their own profile"""
        request = self.factory.patch("/")
        request.user = self.student
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_inactive_student_cannot_edit_profile(self):
        """Test: inactive student denied access"""
        request = self.factory.patch("/")
        request.user = self.inactive_student
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.inactive_student_profile) is False

    def test_tutor_can_edit_assigned_student_profile(self):
        """Test: tutor can edit their assigned student's profile"""
        request = self.factory.patch("/")
        request.user = self.tutor
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_tutor_cannot_edit_unassigned_student_profile(self):
        """Test: tutor cannot edit unassigned student"""
        other_tutor = User.objects.create_user(
            username="tutor2",
            email="tutor2@test.com",
            password="pass123",
            role=User.Role.TUTOR,
        )
        request = self.factory.patch("/")
        request.user = other_tutor
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is False

    def test_admin_can_edit_any_profile(self):
        """Test: admin can edit any student profile"""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass123",
        )
        request = self.factory.patch("/")
        request.user = admin
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_anyone_can_read_student_profile(self):
        """Test: all active users can read student profile"""
        other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        request = self.factory.get("/")
        request.user = other_user
        request.method = "GET"
        assert self.permission.has_object_permission(request, None, self.student_profile) is True

    def test_student_cannot_edit_other_student_profile(self):
        """Test: student cannot edit another student's profile"""
        other_student = User.objects.create_user(
            username="other_student",
            email="other_student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        request = self.factory.patch("/")
        request.user = other_student
        request.method = "PATCH"
        assert self.permission.has_object_permission(request, None, self.student_profile) is False


class TestIsStudentPermission(TestCase):
    """Tests for IsStudent permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsStudent()

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
        )
        self.inactive_student = User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )

    def test_student_has_permission(self):
        """Test: student has access"""
        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_permission(request, None) is True

    def test_tutor_denied_permission(self):
        """Test: tutor denied access"""
        request = self.factory.get("/")
        request.user = self.tutor
        assert self.permission.has_permission(request, None) is False

    def test_inactive_student_denied_permission(self):
        """Test: inactive student denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_student
        assert self.permission.has_permission(request, None) is False


class TestIsTeacherPermission(TestCase):
    """Tests for IsTeacher permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsTeacher()

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        self.inactive_teacher = User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=False,
        )

    def test_teacher_has_permission(self):
        """Test: teacher has access"""
        request = self.factory.get("/")
        request.user = self.teacher
        assert self.permission.has_permission(request, None) is True

    def test_student_denied_permission(self):
        """Test: student denied access"""
        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_permission(request, None) is False

    def test_inactive_teacher_denied_permission(self):
        """Test: inactive teacher denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_teacher
        assert self.permission.has_permission(request, None) is False


class TestIsTutorPermission(TestCase):
    """Tests for IsTutor permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsTutor()

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
        )

    def test_tutor_has_permission(self):
        """Test: tutor has access"""
        request = self.factory.get("/")
        request.user = self.tutor
        assert self.permission.has_permission(request, None) is True

    def test_student_denied_permission(self):
        """Test: student denied access"""
        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_permission(request, None) is False

    def test_inactive_tutor_denied_permission(self):
        """Test: inactive tutor denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_tutor
        assert self.permission.has_permission(request, None) is False


class TestIsParentPermission(TestCase):
    """Tests for IsParent permission class"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsParent()

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
        )
        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        self.inactive_parent = User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=False,
        )

    def test_parent_has_permission(self):
        """Test: parent has access"""
        request = self.factory.get("/")
        request.user = self.parent
        assert self.permission.has_permission(request, None) is True

    def test_student_denied_permission(self):
        """Test: student denied access"""
        request = self.factory.get("/")
        request.user = self.student
        assert self.permission.has_permission(request, None) is False

    def test_inactive_parent_denied_permission(self):
        """Test: inactive parent denied access"""
        request = self.factory.get("/")
        request.user = self.inactive_parent
        assert self.permission.has_permission(request, None) is False
