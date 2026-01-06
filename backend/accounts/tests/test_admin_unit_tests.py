import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import StudentProfile

User = get_user_model()


class TestStudentProfileValidation(TestCase):
    """Unit tests for StudentProfile model validation"""

    def test_student_profile_requires_grade(self):
        """Test: StudentProfile grade field is required"""
        student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        with pytest.raises(Exception):
            StudentProfile.objects.create(user=student, grade=None)

    def test_student_profile_accepts_valid_grade(self):
        """Test: StudentProfile accepts grade 1-12"""
        student = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5)
        assert profile.grade == 5
        assert profile.user == student

    def test_student_profile_goal_optional(self):
        """Test: StudentProfile goal field is optional"""
        student = User.objects.create_user(
            username="student3",
            email="student3@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5, goal="")
        assert profile.goal == ""

    def test_student_profile_goal_max_length_1000(self):
        """Test: StudentProfile goal field max length is 1000"""
        student = User.objects.create_user(
            username="student4",
            email="student4@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        long_goal = "x" * 1000
        profile = StudentProfile.objects.create(user=student, grade=5, goal=long_goal)
        assert len(profile.goal) == 1000

    def test_student_profile_tutor_optional(self):
        """Test: StudentProfile tutor field is optional"""
        student = User.objects.create_user(
            username="student5",
            email="student5@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5, tutor=None)
        assert profile.tutor is None

    def test_student_profile_parent_optional(self):
        """Test: StudentProfile parent field is optional"""
        student = User.objects.create_user(
            username="student6",
            email="student6@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5, parent=None)
        assert profile.parent is None

    def test_student_profile_all_fields_populated(self):
        """Test: StudentProfile can have all fields populated"""
        tutor = User.objects.create_user(
            username="tutor",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR
        )

        parent = User.objects.create_user(
            username="parent",
            email="parent@test.com",
            password="pass123",
            role=User.Role.PARENT
        )

        student = User.objects.create_user(
            username="student7",
            email="student7@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=student,
            grade=10,
            goal="Master Math",
            tutor=tutor,
            parent=parent
        )

        assert profile.user == student
        assert profile.grade == 10
        assert profile.goal == "Master Math"
        assert profile.tutor == tutor
        assert profile.parent == parent

    def test_student_profile_default_values(self):
        """Test: StudentProfile has correct default values"""
        student = User.objects.create_user(
            username="student8",
            email="student8@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5)

        assert profile.progress_percentage == 0
        assert profile.total_points == 0
        assert profile.streak_days == 0
        assert profile.accuracy_percentage == 0

    def test_student_profile_user_oneto_one_relationship(self):
        """Test: StudentProfile has OneToOne relationship with User"""
        student = User.objects.create_user(
            username="student9",
            email="student9@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=student, grade=5)

        assert student.student_profile.grade == 5
        assert student.student_profile.user == student

    def test_user_string_representation(self):
        """Test: User __str__ shows role information"""
        user = User.objects.create_user(
            username="test_user",
            email="test@test.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
            role=User.Role.STUDENT
        )

        str_repr = str(user)
        assert "John Doe" in str_repr
        assert "Student" in str_repr or "student" in str_repr


class TestUserModelValidation(TestCase):
    """Unit tests for User model validation"""

    def test_user_creation_with_role(self):
        """Test: User can be created with role"""
        user = User.objects.create_user(
            username="user_with_role",
            email="user@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        assert user.role == User.Role.STUDENT
        assert user.is_active is True

    def test_user_creation_all_roles(self):
        """Test: User can be created with all available roles"""
        roles = [User.Role.STUDENT, User.Role.TEACHER, User.Role.TUTOR, User.Role.PARENT]

        for i, role in enumerate(roles):
            user = User.objects.create_user(
                username=f"user_{role}",
                email=f"{role}{i}@test.com",
                password="pass123",
                role=role
            )
            assert user.role == role

    def test_user_default_role_is_student(self):
        """Test: Default user role is STUDENT"""
        user = User.objects.create_user(
            username="default_role_user",
            email="default@test.com",
            password="pass123"
        )

        assert user.role == User.Role.STUDENT

    def test_user_is_active_default_true(self):
        """Test: User is_active defaults to True"""
        user = User.objects.create_user(
            username="active_user",
            email="active@test.com",
            password="pass123"
        )

        assert user.is_active is True

    def test_user_can_be_deactivated(self):
        """Test: User can be deactivated (is_active=False)"""
        user = User.objects.create_user(
            username="deactivate_user",
            email="deactivate@test.com",
            password="pass123",
            is_active=True
        )

        assert user.is_active is True

        user.is_active = False
        user.save()
        user.refresh_from_db()

        assert user.is_active is False

    def test_user_with_phone_number(self):
        """Test: User can have phone number"""
        user = User.objects.create_user(
            username="phone_user",
            email="phone@test.com",
            password="pass123",
            phone="+1234567890"
        )

        assert user.phone == "+1234567890"

    def test_user_phone_optional(self):
        """Test: User phone number is optional"""
        user = User.objects.create_user(
            username="no_phone_user",
            email="nophone@test.com",
            password="pass123"
        )

        assert user.phone == ""

    def test_superuser_creation(self):
        """Test: Superuser can be created"""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123"
        )

        assert admin.is_superuser is True
        assert admin.is_staff is True
        assert admin.is_active is True

    def test_user_with_first_and_last_name(self):
        """Test: User can have first and last name"""
        user = User.objects.create_user(
            username="named_user",
            email="named@test.com",
            password="pass123",
            first_name="John",
            last_name="Doe"
        )

        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.get_full_name() == "John Doe"

    def test_user_email_is_unique(self):
        """Test: User email must be unique"""
        User.objects.create_user(
            username="user1",
            email="duplicate@test.com",
            password="pass123"
        )

        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="user2",
                email="duplicate@test.com",
                password="pass123"
            )


class TestAdminWorkflowScenarios(TestCase):
    """Integration-level tests for admin workflow scenarios"""

    def test_create_student_then_assign_tutor(self):
        """Test: Create student then assign tutor"""
        tutor = User.objects.create_user(
            username="tutor",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR
        )

        student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5)
        assert profile.tutor is None

        profile.tutor = tutor
        profile.save()

        profile.refresh_from_db()
        assert profile.tutor == tutor

    def test_create_student_assign_both_tutor_and_parent(self):
        """Test: Create student and assign both tutor and parent"""
        tutor = User.objects.create_user(
            username="tutor2",
            email="tutor2@test.com",
            password="pass123",
            role=User.Role.TUTOR
        )

        parent = User.objects.create_user(
            username="parent2",
            email="parent2@test.com",
            password="pass123",
            role=User.Role.PARENT
        )

        student = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=student,
            grade=5,
            tutor=tutor,
            parent=parent
        )

        assert profile.tutor == tutor
        assert profile.parent == parent

    def test_soft_delete_student_keeps_profile(self):
        """Test: Soft delete keeps StudentProfile"""
        student = User.objects.create_user(
            username="student_soft_delete",
            email="student_soft_delete@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=student, grade=5)

        assert user.is_active is True
        user.is_active = False
        user.save()
        user.refresh_from_db()

        profile = StudentProfile.objects.get(user=student)
        assert profile is not None

    def test_update_student_grade_and_goal(self):
        """Test: Update student grade and goal"""
        student = User.objects.create_user(
            username="student_update",
            email="student_update@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=student, grade=5, goal="")
        assert profile.grade == 5
        assert profile.goal == ""

        profile.grade = 10
        profile.goal = "Master All Subjects"
        profile.save()

        profile.refresh_from_db()
        assert profile.grade == 10
        assert profile.goal == "Master All Subjects"

    def test_hard_delete_removes_everything(self):
        """Test: Hard delete removes User and StudentProfile"""
        student = User.objects.create_user(
            username="student_hard_delete",
            email="student_hard_delete@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=student, grade=5)
        student_id = student.id

        student.delete()

        from django.core.exceptions import ObjectDoesNotExist
        with pytest.raises(User.DoesNotExist):
            User.objects.get(id=student_id)

        with pytest.raises(StudentProfile.DoesNotExist):
            StudentProfile.objects.get(user_id=student_id)
