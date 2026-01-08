import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from accounts.models import User, StudentProfile


@pytest.mark.django_db
class TestProfileValidationOnCreation(TestCase):
    """Тесты валидации профиля через clean()"""

    def test_studentprofile_clean_validates_tutor_role(self):
        """StudentProfile.clean() проверяет роль тьютора"""
        wrong_role_user = User.objects.create(
            username="wrong_role_1",
            email="wrong_role1@test.com",
            role=User.Role.STUDENT,
        )

        student = User.objects.create(
            username="student_clean_1",
            email="student_clean1@test.com",
            role=User.Role.STUDENT,
        )
        student_profile = StudentProfile.objects.create(user=student)
        student_profile.tutor = wrong_role_user

        with pytest.raises(ValidationError) as exc_info:
            student_profile.clean()

        assert "тьютор" in str(exc_info.value).lower() or "tutor" in str(exc_info.value).lower()

    def test_studentprofile_clean_validates_tutor_is_active(self):
        """StudentProfile.clean() проверяет что тьютор активный"""
        inactive_tutor = User.objects.create(
            username="inactive_tutor_1",
            email="inactive_tutor1@test.com",
            role=User.Role.TUTOR,
            is_active=False,
        )

        student = User.objects.create(
            username="student_clean_2",
            email="student_clean2@test.com",
            role=User.Role.STUDENT,
        )
        student_profile = StudentProfile.objects.create(user=student)
        student_profile.tutor = inactive_tutor

        with pytest.raises(ValidationError) as exc_info:
            student_profile.clean()

        assert "активн" in str(exc_info.value).lower() or "active" in str(exc_info.value).lower()

    def test_studentprofile_clean_validates_parent_role(self):
        """StudentProfile.clean() проверяет роль родителя"""
        wrong_role_user = User.objects.create(
            username="wrong_parent_role_1",
            email="wrong_parent_role1@test.com",
            role=User.Role.TEACHER,
        )

        student = User.objects.create(
            username="student_clean_3",
            email="student_clean3@test.com",
            role=User.Role.STUDENT,
        )
        student_profile = StudentProfile.objects.create(user=student)
        student_profile.parent = wrong_role_user

        with pytest.raises(ValidationError) as exc_info:
            student_profile.clean()

        assert "родител" in str(exc_info.value).lower() or "parent" in str(exc_info.value).lower()

    def test_studentprofile_clean_validates_parent_is_active(self):
        """StudentProfile.clean() проверяет что родитель активный"""
        inactive_parent = User.objects.create(
            username="inactive_parent_1",
            email="inactive_parent1@test.com",
            role=User.Role.PARENT,
            is_active=False,
        )

        student = User.objects.create(
            username="student_clean_4",
            email="student_clean4@test.com",
            role=User.Role.STUDENT,
        )
        student_profile = StudentProfile.objects.create(user=student)
        student_profile.parent = inactive_parent

        with pytest.raises(ValidationError) as exc_info:
            student_profile.clean()

        assert "активн" in str(exc_info.value).lower() or "active" in str(exc_info.value).lower()

    def test_valid_student_profile_passes_clean(self):
        """Валидный StudentProfile проходит clean()"""
        active_tutor = User.objects.create(
            username="active_tutor_1",
            email="active_tutor1@test.com",
            role=User.Role.TUTOR,
            is_active=True,
        )
        active_parent = User.objects.create(
            username="active_parent_1",
            email="active_parent1@test.com",
            role=User.Role.PARENT,
            is_active=True,
        )

        student = User.objects.create(
            username="student_clean_5",
            email="student_clean5@test.com",
            role=User.Role.STUDENT,
        )
        student_profile = StudentProfile.objects.create(user=student)
        student_profile.tutor = active_tutor
        student_profile.parent = active_parent

        student_profile.clean()
