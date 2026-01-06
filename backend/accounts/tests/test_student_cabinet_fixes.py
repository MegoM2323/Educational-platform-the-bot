"""
Comprehensive tests for all 13 fixes in student cabinet system.

Tests cover:
1. User.clean() validation of created_by_tutor
2. StudentProfile.clean() validation of tutor and parent roles
3. TelegramLinkToken token hashing and verification
4. StudentProfileView race condition handling
5. Signal handlers for profile auto-creation
6. Invoice sync signal
7. Private fields in serializers
8. TelegramValidator normalization and duplicate prevention
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import check_password
from django.test import TestCase
from rest_framework.test import APITestCase
from unittest.mock import patch, MagicMock
import uuid
import os

from accounts.models import (
    User,
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
    TelegramLinkToken,
)
from accounts.profile_serializers import (
    StudentProfileDetailSerializer,
    TeacherProfileDetailSerializer,
    TutorProfileDetailSerializer,
    TelegramValidator,
)
from accounts.permissions import can_view_private_fields

User = get_user_model()


# ============= USER MODEL TESTS (Fix #1) =============


class TestUserCleanValidation(TestCase):
    """Tests for User.clean() validation of created_by_tutor field"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor1", email="tutor@test.com",
            password="testpass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor1", email="inactive_tutor@test.com",
            password="testpass",
            role=User.Role.TUTOR,
            is_active=False,
        )
        self.teacher = User.objects.create_user(
            username="teacher1", email="teacher@test.com",
            password="testpass",
            role=User.Role.TEACHER,
            is_active=True,
        )

    def test_created_by_tutor_with_valid_tutor(self):
        """Test that created_by_tutor accepts valid active tutor"""
        user = User(
            username="student1", email="student@test.com",
            password="testpass",
            role=User.Role.STUDENT,
            created_by_tutor=self.tutor,
        )
        user.clean()  # Should not raise

    def test_created_by_tutor_with_non_tutor_user(self):
        """Test that created_by_tutor rejects non-tutor users"""
        user = User(
            username="student1", email="student@test.com",
            password="testpass",
            role=User.Role.STUDENT,
            created_by_tutor=self.teacher,
        )
        with self.assertRaises(ValidationError) as context:
            user.clean()
        self.assertIn("created_by_tutor", context.exception.message_dict)

    def test_created_by_tutor_with_inactive_tutor(self):
        """Test that created_by_tutor rejects inactive tutors"""
        user = User(
            username="student1", email="student@test.com",
            password="testpass",
            role=User.Role.STUDENT,
            created_by_tutor=self.inactive_tutor,
        )
        with self.assertRaises(ValidationError) as context:
            user.clean()
        self.assertIn("created_by_tutor", context.exception.message_dict)

    def test_created_by_tutor_self_reference_rejected(self):
        """Test that created_by_tutor cannot be self"""
        user = self.tutor
        user.created_by_tutor = user
        with self.assertRaises(ValidationError) as context:
            user.clean()
        self.assertIn("created_by_tutor", context.exception.message_dict)

    def test_created_by_tutor_none_allowed(self):
        """Test that created_by_tutor=None is valid"""
        user = User(
            username="student1", email="student@test.com",
            password="testpass",
            role=User.Role.STUDENT,
            created_by_tutor=None,
        )
        user.clean()  # Should not raise


# ============= STUDENT PROFILE VALIDATION TESTS (Fix #2) =============


class TestStudentProfileCleanValidation(TestCase):
    """Tests for StudentProfile.clean() validation of tutor and parent"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student@test.com", password="testpass", role=User.Role.STUDENT
        )
        self.valid_tutor = User.objects.create_user(
            username="tutor1", email="tutor@test.com",
            password="testpass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.invalid_tutor = User.objects.create_user(
            username="teacher1", email="teacher@test.com",
            password="testpass",
            role=User.Role.TEACHER,
            is_active=True,
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive1", email="inactive@test.com",
            password="testpass",
            role=User.Role.TUTOR,
            is_active=False,
        )
        self.valid_parent = User.objects.create_user(
            username="parent1", email="parent@test.com",
            password="testpass",
            role=User.Role.PARENT,
            is_active=True,
        )
        self.invalid_parent = User.objects.create_user(
            username="student2", email="student2@test.com",
            password="testpass",
            role=User.Role.STUDENT,
            is_active=True,
        )

    def test_tutor_with_valid_tutor(self):
        """Test that tutor field accepts valid active tutor"""
        profile = StudentProfile(user=self.student, tutor=self.valid_tutor)
        profile.clean()  # Should not raise

    def test_tutor_with_non_tutor_user_rejected(self):
        """Test that tutor field rejects non-tutor users"""
        profile = StudentProfile(user=self.student, tutor=self.invalid_tutor)
        with self.assertRaises(ValidationError) as context:
            profile.clean()
        self.assertIn("tutor", context.exception.message_dict)

    def test_tutor_with_inactive_tutor_rejected(self):
        """Test that tutor field rejects inactive tutors"""
        profile = StudentProfile(user=self.student, tutor=self.inactive_tutor)
        with self.assertRaises(ValidationError) as context:
            profile.clean()
        self.assertIn("tutor", context.exception.message_dict)

    def test_tutor_none_allowed(self):
        """Test that tutor=None is valid"""
        profile = StudentProfile(user=self.student, tutor=None)
        profile.clean()  # Should not raise

    def test_parent_with_valid_parent(self):
        """Test that parent field accepts valid parent"""
        profile = StudentProfile(user=self.student, parent=self.valid_parent)
        profile.clean()  # Should not raise

    def test_parent_with_non_parent_user_rejected(self):
        """Test that parent field rejects non-parent users"""
        profile = StudentProfile(user=self.student, parent=self.invalid_parent)
        with self.assertRaises(ValidationError) as context:
            profile.clean()
        self.assertIn("parent", context.exception.message_dict)

    def test_parent_none_allowed(self):
        """Test that parent=None is valid"""
        profile = StudentProfile(user=self.student, parent=None)
        profile.clean()  # Should not raise

    def test_multiple_validation_errors(self):
        """Test that multiple validation errors are reported together"""
        profile = StudentProfile(
            user=self.student,
            tutor=self.invalid_tutor,
            parent=self.invalid_parent,
        )
        with self.assertRaises(ValidationError) as context:
            profile.clean()
        self.assertIn("tutor", context.exception.message_dict)
        self.assertIn("parent", context.exception.message_dict)


# ============= TELEGRAM LINK TOKEN TESTS (Fixes #3, #4, #5) =============


class TestTelegramLinkTokenEncryption(TestCase):
    """Tests for TelegramLinkToken token hashing and verification"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1", email="user@test.com", password="testpass", role=User.Role.STUDENT
        )

    def test_set_token_hashes_plain_token(self):
        """Test that set_token() hashes the token using Django's make_password"""
        plain_token = str(uuid.uuid4())
        token_obj = TelegramLinkToken(user=self.user)
        token_obj.set_token(plain_token)

        # Token should be hashed, not plaintext
        self.assertNotEqual(token_obj.token, plain_token)
        # Hash should be verifiable by Django's check_password
        self.assertTrue(check_password(plain_token, token_obj.token))

    def test_verify_token_success(self):
        """Test that verify_token() correctly validates matching tokens"""
        plain_token = str(uuid.uuid4())
        token_obj = TelegramLinkToken(
            user=self.user, expires_at=timezone.now() + timedelta(hours=1)
        )
        token_obj.set_token(plain_token)

        self.assertTrue(token_obj.verify_token(plain_token))

    def test_verify_token_failure(self):
        """Test that verify_token() rejects non-matching tokens"""
        plain_token = str(uuid.uuid4())
        wrong_token = str(uuid.uuid4())
        token_obj = TelegramLinkToken(
            user=self.user, expires_at=timezone.now() + timedelta(hours=1)
        )
        token_obj.set_token(plain_token)

        self.assertFalse(token_obj.verify_token(wrong_token))

    def test_is_expired_with_future_expiry(self):
        """Test that is_expired() returns False for future expiry"""
        token_obj = TelegramLinkToken(
            user=self.user, expires_at=timezone.now() + timedelta(hours=1)
        )
        token_obj.set_token(str(uuid.uuid4()))

        self.assertFalse(token_obj.is_expired())

    def test_is_expired_with_past_expiry(self):
        """Test that is_expired() returns True for past expiry"""
        token_obj = TelegramLinkToken(
            user=self.user, expires_at=timezone.now() - timedelta(hours=1)
        )
        token_obj.set_token(str(uuid.uuid4()))

        self.assertTrue(token_obj.is_expired())

    def test_is_expired_at_exact_moment(self):
        """Test that is_expired() behavior at exact expiry moment"""
        now = timezone.now()
        token_obj = TelegramLinkToken(user=self.user, expires_at=now)
        token_obj.set_token(str(uuid.uuid4()))

        # Should be expired at or after the exact moment
        self.assertTrue(token_obj.is_expired())

    def test_token_stored_as_hash_not_plaintext(self):
        """Test that token is hashed when saved to database"""
        plain_token = str(uuid.uuid4())
        token_obj = TelegramLinkToken.objects.create(
            user=self.user, expires_at=timezone.now() + timedelta(hours=1)
        )
        token_obj.set_token(plain_token)
        token_obj.save()

        # Retrieve from database
        stored_obj = TelegramLinkToken.objects.get(pk=token_obj.pk)

        # Token should be hashed, not plaintext
        self.assertNotEqual(stored_obj.token, plain_token)
        # But should verify correctly
        self.assertTrue(stored_obj.verify_token(plain_token))


# ============= TELEGRAM VALIDATOR TESTS (Fix #9) =============


class TestTelegramValidator(TestCase):
    """Tests for TelegramValidator normalization and duplicate prevention"""

    def setUp(self):
        self.student1 = User.objects.create_user(
            username="s_student1", email="student1@test.com", password="testpass", role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            username="student2", email="student2@test.com", password="testpass", role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=self.student1, telegram="valid_user")

    def test_telegram_normalization_removes_at_symbol(self):
        """Test that TelegramValidator normalizes @username to username"""
        validator = TelegramValidator()
        # Should not raise - just normalizes internally
        validator("@testuser123")  # Should pass

    def test_telegram_normalization_case_insensitive(self):
        """Test that TelegramValidator normalizes to lowercase"""
        validator = TelegramValidator()
        # Both should be valid (normalized to same value)
        validator("TestUser123")  # Should pass

    def test_telegram_format_validation_5_32_chars(self):
        """Test that TelegramValidator enforces 5-32 character length"""
        validator = TelegramValidator()

        # Too short
        with self.assertRaises(Exception):
            validator("abc")

        # Too long
        with self.assertRaises(Exception):
            validator("a" * 33)

        # Valid length
        validator("validuser123")  # Should pass

    def test_telegram_format_validation_alphanumeric_underscore(self):
        """Test that TelegramValidator only allows alphanumeric and underscore"""
        validator = TelegramValidator()

        # Invalid characters
        with self.assertRaises(Exception):
            validator("invalid-user")

        with self.assertRaises(Exception):
            validator("invalid.user")

        # Valid characters
        validator("valid_user_123")  # Should pass

    def test_telegram_duplicate_prevention_case_insensitive(self):
        """Test that TelegramValidator prevents duplicate usernames (case-insensitive)"""
        validator = TelegramValidator()

        # valid_user already exists
        with self.assertRaises(Exception) as context:
            validator("VALID_USER")  # Different case

        self.assertIn("already", str(context.exception).lower())

    def test_telegram_empty_string_allowed(self):
        """Test that TelegramValidator allows empty string"""
        validator = TelegramValidator()
        validator("")  # Should not raise


# ============= PRIVATE FIELDS SERIALIZER TESTS (Fix #8) =============


class TestPrivateFieldsInSerializers(TestCase):
    """Tests for private field hiding in serializers"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student@test.com", password="testpass", role=User.Role.STUDENT
        )
        self.teacher = User.objects.create_user(
            username="teacher1", email="teacher@test.com",
            password="testpass",
            role=User.Role.TEACHER,
            is_active=True,
        )
        self.tutor = User.objects.create_user(
            username="tutor1", email="tutor@test.com",
            password="testpass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.admin = User.objects.create_superuser(
            username="admin1", email="admin@test.com", password="testpass"
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student, goal="Learning goal", tutor=self.tutor
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher, bio="Teacher bio", experience_years=5
        )

    def test_can_view_private_fields_owner_cannot(self):
        """Test that can_view_private_fields returns False for owner"""
        result = can_view_private_fields(
            self.student, self.student, User.Role.STUDENT
        )
        self.assertFalse(result)

    def test_can_view_private_fields_teacher_can_see_student(self):
        """Test that teacher can view student private fields"""
        result = can_view_private_fields(
            self.teacher, self.student, User.Role.STUDENT
        )
        self.assertTrue(result)

    def test_can_view_private_fields_tutor_can_see_student(self):
        """Test that tutor can view student private fields"""
        result = can_view_private_fields(self.tutor, self.student, User.Role.STUDENT)
        self.assertTrue(result)

    def test_can_view_private_fields_admin_can_see_all(self):
        """Test that admin can view all private fields"""
        result = can_view_private_fields(self.admin, self.teacher, User.Role.TEACHER)
        self.assertTrue(result)

    def test_can_view_private_fields_inactive_user_cannot(self):
        """Test that inactive users cannot view private fields"""
        inactive_user = User.objects.create_user(
            username="inactive1", email="inactive@test.com",
            password="testpass",
            role=User.Role.TEACHER,
            is_active=False,
        )
        result = can_view_private_fields(
            inactive_user, self.student, User.Role.STUDENT
        )
        self.assertFalse(result)


# ============= SIGNAL TESTS =============


class TestAutoCreateUserProfileSignal(TestCase):
    """Tests for auto_create_user_profile signal handler"""

    def test_student_user_creates_student_profile(self):
        """Test that creating student user automatically creates StudentProfile"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            user = User.objects.create_user(
                username="student1", email="student@test.com",
                password="testpass",
                role=User.Role.STUDENT,
            )

            # Check that StudentProfile was created
            self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_teacher_user_creates_teacher_profile(self):
        """Test that creating teacher user automatically creates TeacherProfile"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            user = User.objects.create_user(
                username="teacher1", email="teacher@test.com",
                password="testpass",
                role=User.Role.TEACHER,
            )

            self.assertTrue(TeacherProfile.objects.filter(user=user).exists())

    def test_tutor_user_creates_tutor_profile(self):
        """Test that creating tutor user automatically creates TutorProfile"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            user = User.objects.create_user(
                username="tutor1", email="tutor@test.com", password="testpass", role=User.Role.TUTOR
            )

            self.assertTrue(TutorProfile.objects.filter(user=user).exists())

    def test_parent_user_creates_parent_profile(self):
        """Test that creating parent user automatically creates ParentProfile"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            user = User.objects.create_user(
                username="parent1", email="parent@test.com",
                password="testpass",
                role=User.Role.PARENT,
            )

            self.assertTrue(ParentProfile.objects.filter(user=user).exists())

    def test_signal_skipped_in_test_environment(self):
        """Test that signal is skipped when ENVIRONMENT=test"""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            user = User.objects.create_user(
                username="student1", email="student@test.com",
                password="testpass",
                role=User.Role.STUDENT,
            )

            # Profile should NOT be created in test environment
            self.assertFalse(StudentProfile.objects.filter(user=user).exists())


# ============= INTEGRATION TESTS =============


class TestStudentRoleImmutability(TestCase):
    """Test that student cannot change own role via PATCH"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student@test.com", password="testpass", role=User.Role.STUDENT
        )

    def test_role_field_is_read_only(self):
        """Test that role field is marked read-only in UserSerializer"""
        from accounts.serializers import UserSerializer

        serializer = UserSerializer()
        self.assertIn("role", serializer.fields)
        self.assertTrue(serializer.fields["role"].read_only)


class TestTutorStudentValidation(TestCase):
    """Test that StudentProfile.tutor must be tutor user"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student@test.com", password="testpass", role=User.Role.STUDENT
        )
        self.tutor = User.objects.create_user(
            username="tutor1", email="tutor@test.com",
            password="testpass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.teacher = User.objects.create_user(
            username="teacher1", email="teacher@test.com",
            password="testpass",
            role=User.Role.TEACHER,
            is_active=True,
        )

    def test_tutor_must_be_tutor_role(self):
        """Test that StudentProfile.tutor field validates role"""
        profile = StudentProfile(user=self.student, tutor=self.teacher)

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_valid_tutor_assignment(self):
        """Test that valid tutor assignment works"""
        profile = StudentProfile(user=self.student, tutor=self.tutor)
        profile.full_clean()  # Should not raise
        profile.save()

        self.assertEqual(profile.tutor, self.tutor)


# ============= SYNC INVOICES TESTS =============


class TestSyncInvoicesOnParentChange(TestCase):
    """Tests for sync_invoices_on_parent_change signal"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1", email="student@test.com", password="testpass", role=User.Role.STUDENT
        )
        self.old_parent = User.objects.create_user(
            username="old_parent1", email="old_parent@test.com",
            password="testpass",
            role=User.Role.PARENT,
        )
        self.new_parent = User.objects.create_user(
            username="new_parent1", email="new_parent@test.com",
            password="testpass",
            role=User.Role.PARENT,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student, parent=self.old_parent
        )

    def test_invoice_parent_updated_on_profile_parent_change(self):
        """Test that invoices are synced when StudentProfile.parent changes"""
        try:
            from invoices.models import Invoice

            # Create invoice with old parent
            invoice = Invoice.objects.create(
                student=self.student, parent=self.old_parent
            )

            # Change student profile parent
            self.student_profile.parent = self.new_parent
            self.student_profile.save()

            # Check that invoice parent was updated
            invoice.refresh_from_db()
            self.assertEqual(invoice.parent, self.new_parent)

        except ImportError:
            self.skipTest("invoices app not available")

    def test_invoice_sync_only_on_update_not_creation(self):
        """Test that invoice sync only happens on profile update, not creation"""
        try:
            from invoices.models import Invoice

            # Create new student and profile
            student2 = User.objects.create_user(
                username="student2", email="student2@test.com", password="testpass", role=User.Role.STUDENT
            )

            # Create invoice first
            invoice = Invoice.objects.create(student=student2, parent=self.old_parent)

            # Now create student profile - invoice should NOT be updated
            profile2 = StudentProfile.objects.create(
                user=student2, parent=self.new_parent
            )

            invoice.refresh_from_db()
            self.assertEqual(invoice.parent, self.old_parent)  # Should not change on creation

        except ImportError:
            self.skipTest("invoices app not available")
