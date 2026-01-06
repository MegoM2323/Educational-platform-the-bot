import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from accounts.serializers import (
    StudentListSerializer,
    StudentDetailSerializer,
    UserPublicSerializer,
    StudentProfileUpdateSerializer,
)

User = get_user_model()


class TestStudentListSerializer(TestCase):
    """Tests for StudentListSerializer"""

    def setUp(self):
        self.factory = APIRequestFactory()

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
            first_name="John",
            last_name="Tutor",
        )

        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="inactive_tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
            first_name="Inactive",
            last_name="Tutor",
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
            first_name="Mary",
            last_name="Parent",
        )

        self.inactive_parent = User.objects.create_user(
            username="inactive_parent",
            email="inactive_parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=False,
            first_name="Inactive",
            last_name="Parent",
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Alice",
            last_name="Student",
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            goal="Prepare for exams",
            tutor=self.tutor,
            parent=self.parent,
        )

    def test_student_list_serializer_includes_avatar(self):
        """Test: avatar field is included in tutor_info"""
        serializer = StudentListSerializer(self.student_profile)
        data = serializer.data
        assert "tutor_info" in data
        assert "avatar" in data["tutor_info"]

    def test_student_list_serializer_excludes_email(self):
        """Test: email is not exposed in tutor_info"""
        serializer = StudentListSerializer(self.student_profile)
        data = serializer.data
        tutor_info = data.get("tutor_info")
        assert tutor_info is not None
        assert "email" not in tutor_info

    def test_student_list_serializer_tutor_info_structure(self):
        """Test: tutor_info has correct structure: id, name, avatar"""
        serializer = StudentListSerializer(self.student_profile)
        data = serializer.data
        tutor_info = data["tutor_info"]
        assert "id" in tutor_info
        assert "name" in tutor_info
        assert "avatar" in tutor_info
        assert tutor_info["id"] == self.tutor.id
        assert tutor_info["name"] == "John Tutor"

    def test_student_list_serializer_parent_info_structure(self):
        """Test: parent_info has correct structure: id, name, avatar"""
        serializer = StudentListSerializer(self.student_profile)
        data = serializer.data
        parent_info = data["parent_info"]
        assert "id" in parent_info
        assert "name" in parent_info
        assert "avatar" in parent_info
        assert parent_info["id"] == self.parent.id
        assert parent_info["name"] == "Mary Parent"

    def test_student_list_serializer_inactive_tutor_returns_none(self):
        """Test: inactive tutor is excluded from response"""
        student2 = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=student2,
            grade="10B",
            tutor=self.inactive_tutor,
        )
        serializer = StudentListSerializer(profile)
        data = serializer.data
        assert data["tutor_info"] is None

    def test_student_list_serializer_inactive_parent_returns_none(self):
        """Test: inactive parent is excluded from response"""
        student3 = User.objects.create_user(
            username="student3",
            email="student3@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=student3,
            grade="10C",
            parent=self.inactive_parent,
        )
        serializer = StudentListSerializer(profile)
        data = serializer.data
        assert data["parent_info"] is None

    def test_student_list_serializer_null_tutor(self):
        """Test: null tutor returns None"""
        student4 = User.objects.create_user(
            username="student4",
            email="student4@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=student4,
            grade="10D",
        )
        serializer = StudentListSerializer(profile)
        data = serializer.data
        assert data["tutor_info"] is None

    def test_student_list_serializer_null_parent(self):
        """Test: null parent returns None"""
        student5 = User.objects.create_user(
            username="student5",
            email="student5@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=student5,
            grade="10E",
        )
        serializer = StudentListSerializer(profile)
        data = serializer.data
        assert data["parent_info"] is None


class TestStudentDetailSerializer(TestCase):
    """Tests for StudentDetailSerializer"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
            first_name="John",
            last_name="Tutor",
        )

        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="inactive_tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
            first_name="Inactive",
            last_name="Tutor",
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
            first_name="Mary",
            last_name="Parent",
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="Alice",
            last_name="Student",
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            goal="Prepare for exams",
            tutor=self.tutor,
            parent=self.parent,
        )

    def test_student_detail_serializer_includes_avatar(self):
        """Test: avatar field is included in tutor_info"""
        serializer = StudentDetailSerializer(self.student_profile)
        data = serializer.data
        assert "tutor_info" in data
        assert "avatar" in data["tutor_info"]

    def test_student_detail_serializer_excludes_email(self):
        """Test: email is not exposed in tutor_info"""
        serializer = StudentDetailSerializer(self.student_profile)
        data = serializer.data
        tutor_info = data.get("tutor_info")
        assert tutor_info is not None
        assert "email" not in tutor_info

    def test_student_detail_serializer_tutor_info_structure(self):
        """Test: tutor_info has correct structure: id, name, avatar"""
        serializer = StudentDetailSerializer(self.student_profile)
        data = serializer.data
        tutor_info = data["tutor_info"]
        assert "id" in tutor_info
        assert "name" in tutor_info
        assert "avatar" in tutor_info
        assert tutor_info["id"] == self.tutor.id
        assert tutor_info["name"] == "John Tutor"

    def test_student_detail_serializer_inactive_tutor_returns_none(self):
        """Test: inactive tutor is excluded"""
        student2 = User.objects.create_user(
            username="student2_detail",
            email="student2_detail@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=student2,
            grade="10B",
            tutor=self.inactive_tutor,
        )
        serializer = StudentDetailSerializer(profile)
        data = serializer.data
        assert data["tutor_info"] is None

    def test_student_detail_serializer_wrong_role_tutor_returns_none(self):
        """Test: wrong role tutor is excluded"""
        student3 = User.objects.create_user(
            username="student3_detail",
            email="student3_detail@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
            first_name="Wrong",
            last_name="Role",
        )
        profile = StudentProfile.objects.create(
            user=student3,
            grade="10C",
            tutor=teacher,  # Wrong role, should be TUTOR
        )
        serializer = StudentDetailSerializer(profile)
        data = serializer.data
        assert data["tutor_info"] is None

    def test_student_detail_serializer_null_tutor(self):
        """Test: null tutor returns None"""
        student4 = User.objects.create_user(
            username="student4_detail",
            email="student4_detail@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )
        profile = StudentProfile.objects.create(
            user=student4,
            grade="10D",
        )
        serializer = StudentDetailSerializer(profile)
        data = serializer.data
        assert data["tutor_info"] is None


class TestUserPublicSerializer(TestCase):
    """Tests for UserPublicSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
            first_name="John",
            last_name="Doe",
        )

    def test_user_public_serializer_excludes_email(self):
        """Test: email is not exposed in public serializer"""
        serializer = UserPublicSerializer(self.user)
        data = serializer.data
        assert "email" not in data

    def test_user_public_serializer_includes_required_fields(self):
        """Test: public serializer includes required fields"""
        serializer = UserPublicSerializer(self.user)
        data = serializer.data
        assert "id" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "role" in data
        assert "is_active" in data

    def test_user_public_serializer_includes_full_name(self):
        """Test: full_name field is computed"""
        serializer = UserPublicSerializer(self.user)
        data = serializer.data
        assert "full_name" in data
        assert data["full_name"] == "John Doe"


class TestStudentProfileUpdateSerializer(TestCase):
    """Tests for StudentProfileUpdateSerializer (admin update)"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="inactive_tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
        )

        self.inactive_parent = User.objects.create_user(
            username="inactive_parent",
            email="inactive_parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=False,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
        )

    def test_validate_tutor_active_tutor(self):
        """Test: validate_tutor accepts active tutor"""
        serializer = StudentProfileUpdateSerializer(data={"tutor": self.tutor.id})
        assert serializer.is_valid()

    def test_validate_tutor_rejects_inactive_tutor(self):
        """Test: validate_tutor rejects inactive tutor"""
        serializer = StudentProfileUpdateSerializer(data={"tutor": self.inactive_tutor.id})
        # validate_tutor is called during validation
        assert not serializer.is_valid()
        assert "tutor" in serializer.errors

    def test_validate_tutor_rejects_wrong_role(self):
        """Test: validate_tutor rejects user without TUTOR role"""
        student = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        serializer = StudentProfileUpdateSerializer(data={"tutor": student.id})
        assert not serializer.is_valid()
        assert "tutor" in serializer.errors

    def test_validate_parent_active_parent(self):
        """Test: validate_parent accepts active parent"""
        serializer = StudentProfileUpdateSerializer(data={"parent": self.parent.id})
        assert serializer.is_valid()

    def test_validate_parent_rejects_inactive_parent(self):
        """Test: validate_parent rejects inactive parent"""
        serializer = StudentProfileUpdateSerializer(data={"parent": self.inactive_parent.id})
        assert not serializer.is_valid()
        assert "parent" in serializer.errors

    def test_validate_parent_rejects_wrong_role(self):
        """Test: validate_parent rejects user without PARENT role"""
        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )
        serializer = StudentProfileUpdateSerializer(data={"parent": teacher.id})
        assert not serializer.is_valid()
        assert "parent" in serializer.errors

    def test_validate_tutor_null_allowed(self):
        """Test: tutor can be null"""
        serializer = StudentProfileUpdateSerializer(data={"tutor": None})
        assert serializer.is_valid()

    def test_validate_parent_null_allowed(self):
        """Test: parent can be null"""
        serializer = StudentProfileUpdateSerializer(data={"parent": None})
        assert serializer.is_valid()


class TestStudentProfileClean(TestCase):
    """Tests for StudentProfile.clean() model validation"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="inactive_tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=False,
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
        )

        self.inactive_parent = User.objects.create_user(
            username="inactive_parent",
            email="inactive_parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=False,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )

    def test_clean_valid_tutor_passes(self):
        """Test: clean() passes with active tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
        )
        # Should not raise
        profile.clean()

    def test_clean_inactive_tutor_raises_validation_error(self):
        """Test: clean() raises ValidationError for inactive tutor"""
        from django.core.exceptions import ValidationError

        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.inactive_tutor,
        )
        with pytest.raises(ValidationError):
            profile.clean()

    def test_clean_invalid_tutor_role_raises_validation_error(self):
        """Test: clean() raises ValidationError for user with wrong role"""
        from django.core.exceptions import ValidationError

        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=teacher,
        )
        with pytest.raises(ValidationError):
            profile.clean()

    def test_clean_valid_parent_passes(self):
        """Test: clean() passes with active parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.parent,
        )
        # Should not raise
        profile.clean()

    def test_clean_inactive_parent_raises_validation_error(self):
        """Test: clean() raises ValidationError for inactive parent"""
        from django.core.exceptions import ValidationError

        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.inactive_parent,
        )
        with pytest.raises(ValidationError):
            profile.clean()

    def test_clean_invalid_parent_role_raises_validation_error(self):
        """Test: clean() raises ValidationError for user with wrong role"""
        from django.core.exceptions import ValidationError

        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=teacher,
        )
        with pytest.raises(ValidationError):
            profile.clean()

    def test_clean_null_tutor_passes(self):
        """Test: clean() passes with null tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
        )
        # Should not raise
        profile.clean()

    def test_clean_null_parent_passes(self):
        """Test: clean() passes with null parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
        )
        # Should not raise
        profile.clean()

    def test_clean_both_tutor_and_parent_valid(self):
        """Test: clean() passes with both valid tutor and parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
            parent=self.parent,
        )
        # Should not raise
        profile.clean()
