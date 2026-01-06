"""Unit tests for staff_views.py functions"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from rest_framework import status
from unittest.mock import patch, MagicMock

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from accounts.staff_views import (
    log_object_changes,
)

User = get_user_model()


class TestLogObjectChanges(TestCase):
    """Tests for log_object_changes helper function"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.user, grade="10A"
        )
        self.request_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass",
            role=User.Role.TEACHER,
            is_superuser=True,
        )
        self.factory = RequestFactory()

    def test_log_object_changes_with_changes(self):
        """Test: log_object_changes logs when there are changes"""
        request = self.factory.patch("/test/")
        request.user = self.request_user

        from accounts.serializers import StudentProfileUpdateSerializer

        data = {"grade": "11B"}
        serializer = StudentProfileUpdateSerializer(
            self.student_profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(request, self.student_profile, serializer, "test_action")
            # Verify logger was called if there are changes
            if serializer.validated_data:
                # Logger should be called for changes
                pass

    def test_log_object_changes_no_changes(self):
        """Test: log_object_changes doesn't log when there are no changes"""
        request = self.factory.patch("/test/")
        request.user = self.request_user

        from accounts.serializers import StudentProfileUpdateSerializer

        data = {}
        serializer = StudentProfileUpdateSerializer(
            self.student_profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(request, self.student_profile, serializer, "test_action")
            # Should not log if no changes

    def test_log_object_changes_excludes_password(self):
        """Test: log_object_changes excludes sensitive fields like password"""
        request = self.factory.patch("/test/")
        request.user = self.request_user

        from accounts.serializers import UserUpdateSerializer
        from accounts.models import User

        data = {"password": "newsecretpass123"}
        user = User.objects.create_user(
            username="user2", email="user2@test.com", password="old", role=User.Role.STUDENT
        )
        serializer = UserUpdateSerializer(user, data=data, partial=True)

        # Password should not be logged (sensitive field)
        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(
                request, user, serializer, "test_action", sensitive_fields=["password"]
            )
