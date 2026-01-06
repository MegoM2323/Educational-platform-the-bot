import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()


class TestStudentProfileClean(TestCase):
    """Tests for StudentProfile.clean() validation"""

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

        self.wrong_role_user = User.objects.create_user(
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

    def test_clean_valid_tutor_passes(self):
        """Test: StudentProfile.clean() accepts active tutor with correct role"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
        )
        # Should not raise ValidationError
        profile.clean()

    def test_clean_inactive_tutor_raises_error(self):
        """Test: StudentProfile.clean() rejects inactive tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.inactive_tutor,
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.clean()
        errors = exc_info.value.error_dict
        assert "tutor" in errors

    def test_clean_invalid_tutor_role_raises_error(self):
        """Test: StudentProfile.clean() rejects user with wrong role as tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.wrong_role_user,
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.clean()
        errors = exc_info.value.error_dict
        assert "tutor" in errors

    def test_clean_valid_parent_passes(self):
        """Test: StudentProfile.clean() accepts active parent with correct role"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.parent,
        )
        # Should not raise ValidationError
        profile.clean()

    def test_clean_inactive_parent_raises_error(self):
        """Test: StudentProfile.clean() rejects inactive parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.inactive_parent,
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.clean()
        errors = exc_info.value.error_dict
        assert "parent" in errors

    def test_clean_invalid_parent_role_raises_error(self):
        """Test: StudentProfile.clean() rejects user with wrong role as parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.wrong_role_user,
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.clean()
        errors = exc_info.value.error_dict
        assert "parent" in errors

    def test_clean_null_tutor_passes(self):
        """Test: StudentProfile.clean() accepts null tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=None,
        )
        # Should not raise ValidationError
        profile.clean()

    def test_clean_null_parent_passes(self):
        """Test: StudentProfile.clean() accepts null parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=None,
        )
        # Should not raise ValidationError
        profile.clean()

    def test_clean_both_valid_tutor_and_parent_passes(self):
        """Test: StudentProfile.clean() accepts both valid tutor and parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
            parent=self.parent,
        )
        # Should not raise ValidationError
        profile.clean()

    def test_clean_both_invalid_tutor_and_parent_raises_errors(self):
        """Test: StudentProfile.clean() raises errors for both invalid tutor and parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.inactive_tutor,
            parent=self.inactive_parent,
        )
        with pytest.raises(ValidationError) as exc_info:
            profile.clean()
        errors = exc_info.value.error_dict
        # At least one error should be present
        assert len(errors) > 0


class TestStudentProfileSave(TestCase):
    """Tests for StudentProfile.save() with full_clean()"""

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
            is_active=True,
        )

    def test_save_with_valid_tutor_succeeds(self):
        """Test: StudentProfile saves successfully with valid tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
        )
        profile.full_clean()
        profile.save()
        # Should be saved without errors
        assert profile.id is not None

    def test_save_with_inactive_tutor_raises_error(self):
        """Test: StudentProfile.save() with full_clean() raises error for inactive tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            tutor=self.inactive_tutor,
        )
        with pytest.raises(ValidationError):
            profile.full_clean()

    def test_save_with_valid_parent_succeeds(self):
        """Test: StudentProfile saves successfully with valid parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.parent,
        )
        profile.full_clean()
        profile.save()
        # Should be saved without errors
        assert profile.id is not None

    def test_save_with_inactive_parent_raises_error(self):
        """Test: StudentProfile.save() with full_clean() raises error for inactive parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
            parent=self.inactive_parent,
        )
        with pytest.raises(ValidationError):
            profile.full_clean()

    def test_save_with_null_tutor_succeeds(self):
        """Test: StudentProfile saves successfully with null tutor"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
        )
        profile.full_clean()
        profile.save()
        assert profile.id is not None

    def test_save_with_null_parent_succeeds(self):
        """Test: StudentProfile saves successfully with null parent"""
        profile = StudentProfile(
            user=self.student,
            grade="10A",
        )
        profile.full_clean()
        profile.save()
        assert profile.id is not None


class TestUserModel(TestCase):
    """Tests for User model"""

    def test_user_role_choices(self):
        """Test: User model has all role choices"""
        assert User.Role.STUDENT == "student"
        assert User.Role.TEACHER == "teacher"
        assert User.Role.TUTOR == "tutor"
        assert User.Role.PARENT == "parent"

    def test_user_creation_with_role(self):
        """Test: User can be created with role"""
        user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        assert user.role == User.Role.STUDENT

    def test_user_is_active_default_true(self):
        """Test: User is_active defaults to True"""
        user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="pass123",
        )
        assert user.is_active is True

    def test_user_can_be_deactivated(self):
        """Test: User can be deactivated"""
        user = User.objects.create_user(
            username="test",
            email="test@test.com",
            password="pass123",
        )
        user.is_active = False
        user.save()
        user.refresh_from_db()
        assert user.is_active is False


class TestStudentProfileModel(TestCase):
    """Tests for StudentProfile model"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

    def test_student_profile_creation(self):
        """Test: StudentProfile can be created"""
        profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
        )
        assert profile.user == self.student
        assert profile.grade == "10A"

    def test_student_profile_with_tutor(self):
        """Test: StudentProfile can have tutor"""
        profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
        )
        assert profile.tutor == self.tutor

    def test_student_profile_with_parent(self):
        """Test: StudentProfile can have parent"""
        profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            parent=self.parent,
        )
        assert profile.parent == self.parent

    def test_student_profile_default_values(self):
        """Test: StudentProfile has proper default values"""
        profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
        )
        assert profile.progress_percentage == 0
        assert profile.streak_days == 0
        assert profile.total_points == 0
        assert profile.accuracy_percentage == 0

    def test_student_profile_str(self):
        """Test: StudentProfile string representation"""
        profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
        )
        assert str(profile) == f"Профиль студента: {self.student.get_full_name()}"


class TestTeacherProfileModel(TestCase):
    """Tests for TeacherProfile model"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )

    def test_teacher_profile_creation(self):
        """Test: TeacherProfile can be created"""
        profile = TeacherProfile.objects.create(
            user=self.teacher,
        )
        assert profile.user == self.teacher

    def test_teacher_profile_with_subject(self):
        """Test: TeacherProfile can have subject"""
        profile = TeacherProfile.objects.create(
            user=self.teacher,
            subject="Mathematics",
        )
        assert profile.subject == "Mathematics"

    def test_teacher_profile_experience_years(self):
        """Test: TeacherProfile can have experience_years"""
        profile = TeacherProfile.objects.create(
            user=self.teacher,
            experience_years=5,
        )
        assert profile.experience_years == 5

    def test_teacher_profile_str(self):
        """Test: TeacherProfile string representation"""
        profile = TeacherProfile.objects.create(
            user=self.teacher,
        )
        assert str(profile) == f"Профиль преподавателя: {self.teacher.get_full_name()}"


class TestTutorProfileModel(TestCase):
    """Tests for TutorProfile model"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

    def test_tutor_profile_creation(self):
        """Test: TutorProfile can be created"""
        profile = TutorProfile.objects.create(
            user=self.tutor,
        )
        assert profile.user == self.tutor

    def test_tutor_profile_with_specialization(self):
        """Test: TutorProfile can have specialization"""
        profile = TutorProfile.objects.create(
            user=self.tutor,
            specialization="English",
        )
        assert profile.specialization == "English"

    def test_tutor_profile_experience_years(self):
        """Test: TutorProfile can have experience_years"""
        profile = TutorProfile.objects.create(
            user=self.tutor,
            experience_years=3,
        )
        assert profile.experience_years == 3

    def test_tutor_profile_str(self):
        """Test: TutorProfile string representation"""
        profile = TutorProfile.objects.create(
            user=self.tutor,
        )
        assert str(profile) == f"Профиль тьютора: {self.tutor.get_full_name()}"


class TestParentProfileModel(TestCase):
    """Tests for ParentProfile model"""

    def setUp(self):
        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=True,
        )

        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

    def test_parent_profile_creation(self):
        """Test: ParentProfile can be created"""
        profile = ParentProfile.objects.create(
            user=self.parent,
        )
        assert profile.user == self.parent

    def test_parent_profile_children_property(self):
        """Test: ParentProfile.children returns children"""
        profile = ParentProfile.objects.create(
            user=self.parent,
        )

        StudentProfile.objects.create(
            user=self.student1,
            grade="10A",
            parent=self.parent,
        )
        StudentProfile.objects.create(
            user=self.student2,
            grade="10B",
            parent=self.parent,
        )

        children = list(profile.children)
        assert len(children) == 2
        assert self.student1 in children
        assert self.student2 in children

    def test_parent_profile_str(self):
        """Test: ParentProfile string representation"""
        profile = ParentProfile.objects.create(
            user=self.parent,
        )
        assert str(profile) == f"Профиль родителя: {self.parent.get_full_name()}"
