import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db import transaction

from chat.permissions import (
    check_parent_access_to_room,
    check_teacher_access_to_room,
)
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment, Subject

User = get_user_model()


class TestCheckParentAccessToRoom(TestCase):
    """Tests for check_parent_access_to_room() function"""

    def setUp(self):
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

        # Create student profiles with parent
        StudentProfile.objects.create(
            user=self.student1,
            grade="10A",
            parent=self.parent,
        )

    def test_inactive_parent_denied_access(self):
        """Test: is_active check - inactive parent denied access"""
        result = check_parent_access_to_room(self.inactive_parent, None, add_to_participants=False)
        assert result is False

    def test_non_parent_role_denied_access(self):
        """Test: non-parent role denied access"""
        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )
        result = check_parent_access_to_room(teacher, None, add_to_participants=False)
        assert result is False


class TestCheckTeacherAccessToRoom(TestCase):
    """Tests for check_teacher_access_to_room() function"""

    def setUp(self):
        self.subject = Subject.objects.create(name="Mathematics")

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=True,
        )

        self.inactive_teacher = User.objects.create_user(
            username="inactive_teacher",
            email="inactive_teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=False,
        )

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
            is_active=True,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True,
        )

        # Create student profile with tutor
        StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            tutor=self.tutor,
        )

        # Create enrollment
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
        )

    def test_inactive_teacher_denied_access(self):
        """Test: is_active check - inactive teacher denied access"""
        result = check_teacher_access_to_room(self.inactive_teacher, None, add_to_participants=False)
        assert result is False

    def test_non_teacher_role_denied_access(self):
        """Test: non-teacher role denied access"""
        result = check_teacher_access_to_room(self.tutor, None, add_to_participants=False)
        assert result is False


class TestDeactivatedUserAccess(TestCase):
    """Tests for deactivated user restrictions in chat permissions"""

    def setUp(self):
        self.subject = Subject.objects.create(name="Mathematics")

        self.inactive_teacher = User.objects.create_user(
            username="inactive_teacher",
            email="inactive_teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
            is_active=False,
        )

        self.inactive_parent = User.objects.create_user(
            username="inactive_parent",
            email="inactive_parent@test.com",
            password="pass123",
            role=User.Role.PARENT,
            is_active=False,
        )

    def test_deactivated_teacher_denied(self):
        """Test: deactivated teacher denied access"""
        result = check_teacher_access_to_room(self.inactive_teacher, None, add_to_participants=False)
        assert result is False

    def test_deactivated_parent_denied(self):
        """Test: deactivated parent denied access"""
        result = check_parent_access_to_room(self.inactive_parent, None, add_to_participants=False)
        assert result is False
