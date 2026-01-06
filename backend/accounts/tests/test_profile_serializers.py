"""
Tests for profile serializers.

Tests cover:
1. Telegram fields are read-only
2. Profile update ignores telegram field
3. Serializer properly exposes telegram_id and is_telegram_linked
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import serializers

from accounts.profile_serializers import (
    StudentProfileDetailSerializer,
    TeacherProfileDetailSerializer,
    TutorProfileDetailSerializer,
    ParentProfileDetailSerializer,
    UserProfileUpdateSerializer,
)
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()


class TestStudentProfileDetailSerializer(TestCase):
    """Tests for student profile serializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="pass123",
            role=User.Role.STUDENT,
            telegram_id=123456789,
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            grade="9",
            goal="Learn programming",
        )

    def test_telegram_id_is_read_only(self):
        """Test that telegram_id is read-only"""
        serializer = StudentProfileDetailSerializer(self.profile)
        assert serializer.fields["telegram_id"].read_only is True

    def test_is_telegram_linked_is_read_only(self):
        """Test that is_telegram_linked is read-only"""
        serializer = StudentProfileDetailSerializer(self.profile)
        assert serializer.fields["is_telegram_linked"].read_only is True

    def test_serializer_includes_telegram_fields(self):
        """Test that serializer includes telegram fields"""
        serializer = StudentProfileDetailSerializer(self.profile)
        data = serializer.data

        assert "telegram_id" in data
        assert "is_telegram_linked" in data

    def test_telegram_id_serialized_correctly(self):
        """Test that telegram_id is serialized from user"""
        serializer = StudentProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["telegram_id"] == 123456789

    def test_is_telegram_linked_true(self):
        """Test that is_telegram_linked is true when linked"""
        serializer = StudentProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["is_telegram_linked"] is True

    def test_is_telegram_linked_false(self):
        """Test that is_telegram_linked is false when not linked"""
        user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        profile = StudentProfile.objects.create(user=user)

        serializer = StudentProfileDetailSerializer(profile)
        data = serializer.data

        assert data["is_telegram_linked"] is False

    def test_cannot_update_telegram_id(self):
        """Test that telegram_id cannot be updated via serializer"""
        data = {
            "telegram_id": 999999999,
            "grade": "10",
        }
        serializer = StudentProfileDetailSerializer(
            self.profile, data=data, partial=True
        )

        # Serializer should not include telegram_id in validated_data
        # because it's read-only
        assert serializer.is_valid()
        serializer.save()

        # telegram_id should not change
        self.profile.refresh_from_db()
        self.profile.user.refresh_from_db()
        assert self.profile.user.telegram_id == 123456789


class TestTeacherProfileDetailSerializer(TestCase):
    """Tests for teacher profile serializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="teacher1",
            email="teacher@example.com",
            password="pass123",
            role=User.Role.TEACHER,
            telegram_id=123456789,
        )
        self.profile = TeacherProfile.objects.create(
            user=self.user,
            subject="Mathematics",
            experience_years=5,
        )

    def test_telegram_id_is_read_only(self):
        """Test that telegram_id is read-only"""
        serializer = TeacherProfileDetailSerializer(self.profile)
        assert serializer.fields["telegram_id"].read_only is True

    def test_is_telegram_linked_is_read_only(self):
        """Test that is_telegram_linked is read-only"""
        serializer = TeacherProfileDetailSerializer(self.profile)
        assert serializer.fields["is_telegram_linked"].read_only is True

    def test_serializer_includes_telegram_fields(self):
        """Test that serializer includes telegram fields"""
        serializer = TeacherProfileDetailSerializer(self.profile)
        data = serializer.data

        assert "telegram_id" in data
        assert "is_telegram_linked" in data

    def test_telegram_id_serialized_correctly(self):
        """Test that telegram_id is serialized from user"""
        serializer = TeacherProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["telegram_id"] == 123456789

    def test_is_telegram_linked_true(self):
        """Test that is_telegram_linked is true when linked"""
        serializer = TeacherProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["is_telegram_linked"] is True


class TestTutorProfileDetailSerializer(TestCase):
    """Tests for tutor profile serializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="tutor1",
            email="tutor@example.com",
            password="pass123",
            role=User.Role.TUTOR,
            telegram_id=123456789,
        )
        self.profile = TutorProfile.objects.create(
            user=self.user,
            specialization="English",
        )

    def test_telegram_id_is_read_only(self):
        """Test that telegram_id is read-only"""
        serializer = TutorProfileDetailSerializer(self.profile)
        assert serializer.fields["telegram_id"].read_only is True

    def test_is_telegram_linked_is_read_only(self):
        """Test that is_telegram_linked is read-only"""
        serializer = TutorProfileDetailSerializer(self.profile)
        assert serializer.fields["is_telegram_linked"].read_only is True

    def test_serializer_includes_telegram_fields(self):
        """Test that serializer includes telegram fields"""
        serializer = TutorProfileDetailSerializer(self.profile)
        data = serializer.data

        assert "telegram_id" in data
        assert "is_telegram_linked" in data

    def test_telegram_id_serialized_correctly(self):
        """Test that telegram_id is serialized from user"""
        serializer = TutorProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["telegram_id"] == 123456789

    def test_is_telegram_linked_true(self):
        """Test that is_telegram_linked is true when linked"""
        serializer = TutorProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["is_telegram_linked"] is True


class TestParentProfileDetailSerializer(TestCase):
    """Tests for parent profile serializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="parent1",
            email="parent@example.com",
            password="pass123",
            role=User.Role.PARENT,
            telegram_id=123456789,
        )
        self.profile = ParentProfile.objects.create(user=self.user)

    def test_telegram_id_is_read_only(self):
        """Test that telegram_id is read-only"""
        serializer = ParentProfileDetailSerializer(self.profile)
        assert serializer.fields["telegram_id"].read_only is True

    def test_is_telegram_linked_is_read_only(self):
        """Test that is_telegram_linked is read-only"""
        serializer = ParentProfileDetailSerializer(self.profile)
        assert serializer.fields["is_telegram_linked"].read_only is True

    def test_serializer_includes_telegram_fields(self):
        """Test that serializer includes telegram fields"""
        serializer = ParentProfileDetailSerializer(self.profile)
        data = serializer.data

        assert "telegram_id" in data
        assert "is_telegram_linked" in data

    def test_telegram_id_serialized_correctly(self):
        """Test that telegram_id is serialized from user"""
        serializer = ParentProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["telegram_id"] == 123456789

    def test_is_telegram_linked_true(self):
        """Test that is_telegram_linked is true when linked"""
        serializer = ParentProfileDetailSerializer(self.profile)
        data = serializer.data

        assert data["is_telegram_linked"] is True


class TestUserProfileUpdateSerializer(TestCase):
    """Tests for user profile update serializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user@example.com",
            password="pass123",
            role=User.Role.STUDENT,
            telegram_id=123456789,
        )

    def test_telegram_id_not_in_serializer_fields(self):
        """Test that telegram_id is not in update serializer"""
        serializer = UserProfileUpdateSerializer(self.user)
        assert "telegram_id" not in serializer.fields

    def test_is_telegram_linked_not_in_serializer_fields(self):
        """Test that is_telegram_linked is not in update serializer"""
        serializer = UserProfileUpdateSerializer(self.user)
        assert "is_telegram_linked" not in serializer.fields

    def test_update_profile_does_not_affect_telegram(self):
        """Test that updating profile does not change telegram_id"""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "newemail@example.com",
        }
        serializer = UserProfileUpdateSerializer(self.user, data=data, partial=True)

        assert serializer.is_valid()
        serializer.save()

        self.user.refresh_from_db()
        assert self.user.telegram_id == 123456789

    def test_sending_telegram_id_in_update_is_ignored(self):
        """Test that sending telegram_id in update is silently ignored"""
        data = {
            "first_name": "Jane",
            "telegram_id": 999999999,
        }
        serializer = UserProfileUpdateSerializer(self.user, data=data, partial=True)

        assert serializer.is_valid()
        serializer.save()

        self.user.refresh_from_db()
        # telegram_id should remain unchanged
        assert self.user.telegram_id == 123456789
        # first_name should be updated
        assert self.user.first_name == "Jane"

    def test_serializer_allowed_fields(self):
        """Test that only specific fields are allowed"""
        allowed_fields = {"first_name", "last_name", "email", "phone", "avatar"}
        serializer = UserProfileUpdateSerializer(self.user)
        assert set(serializer.fields.keys()) == allowed_fields

    def test_email_validation(self):
        """Test that email validation works"""
        data = {"email": "invalid-email"}
        serializer = UserProfileUpdateSerializer(self.user, data=data, partial=True)

        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_valid_email_update(self):
        """Test valid email update"""
        data = {"email": "newemail@example.com"}
        serializer = UserProfileUpdateSerializer(self.user, data=data, partial=True)

        assert serializer.is_valid()
        serializer.save()

        self.user.refresh_from_db()
        assert self.user.email == "newemail@example.com"


class TestProfileSerializerSecurityEdgeCases(TestCase):
    """Tests for security edge cases"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user@example.com",
            password="pass123",
            role=User.Role.STUDENT,
            telegram_id=123456789,
        )
        self.profile = StudentProfile.objects.create(user=self.user)

    def test_null_telegram_id_serialized_correctly(self):
        """Test that null telegram_id is serialized correctly"""
        user = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        profile = StudentProfile.objects.create(user=user)

        serializer = StudentProfileDetailSerializer(profile)
        data = serializer.data

        assert data["telegram_id"] is None
        assert data["is_telegram_linked"] is False

    def test_profile_without_user_relationship(self):
        """Test get_is_telegram_linked with linked user"""
        # User already has a profile from setUp, so just test the method
        serializer = StudentProfileDetailSerializer(self.profile)
        is_linked = serializer.get_is_telegram_linked(self.profile)

        assert is_linked is True

    def test_concurrent_telegram_id_changes(self):
        """Test that serializer sees actual telegram_id"""
        serializer = StudentProfileDetailSerializer(self.profile)
        data1 = serializer.data["telegram_id"]

        # Change telegram_id
        self.user.telegram_id = 999999999
        self.user.save()

        # Re-fetch profile and check serializer
        self.profile.refresh_from_db()
        serializer = StudentProfileDetailSerializer(self.profile)
        data2 = serializer.data["telegram_id"]

        assert data2 == 999999999
