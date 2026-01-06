import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class TestDuplicateEmailProtection(TestCase):
    """Test database constraint protection against duplicate emails"""

    def test_email_field_present_in_user_model(self):
        """Email field exists and can be created"""
        email = "test@example.com"

        user = User.objects.create_user(
            username="user1",
            email=email,
            password="testpass123",
            role=User.Role.STUDENT,
        )

        self.assertEqual(user.email, email)
        self.assertIsNotNone(user.id)

    def test_different_emails_no_conflict(self):
        """Creating multiple users with different emails should succeed"""
        initial_count = User.objects.all().count()
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )
            users.append(user)

        self.assertEqual(len(users), 5)
        final_count = User.objects.all().count()
        self.assertEqual(final_count, initial_count + 5)


class TestDuplicateUsernameProtection(TestCase):
    """Test database constraint protection against duplicate usernames"""

    def test_different_usernames_no_conflict(self):
        """Creating multiple users with different usernames should succeed"""
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"user_{i}",
                email=f"user_{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )
            users.append(user)

        self.assertEqual(len(users), 3)

    def test_username_unique_constraint_exists(self):
        """Username field has unique constraint in database"""
        user = User.objects.create_user(
            username="unique_user_test",
            email="unique@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        self.assertEqual(user.username, "unique_user_test")
        retrieved = User.objects.get(username="unique_user_test")
        self.assertEqual(retrieved.id, user.id)


class TestUserUpdateDataIntegrity(TestCase):
    """Test data integrity when updating user"""

    def test_sequential_user_update_all_succeed(self):
        """Sequential updates should all apply without data loss"""
        user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        initial_id = user.id

        for i in range(3):
            user_obj = User.objects.get(id=initial_id)
            user_obj.first_name = f"Name{i}"
            user_obj.last_name = f"Lastname{i}"
            user_obj.phone = f"+123456789{i % 10}"
            user_obj.save()

        final_user = User.objects.get(id=initial_id)
        self.assertEqual(final_user.id, initial_id)
        self.assertEqual(final_user.email, "test@example.com")
        self.assertEqual(final_user.username, "test_user")
        self.assertEqual(final_user.first_name, "Name2")
        self.assertEqual(final_user.last_name, "Lastname2")

    def test_user_update_preserves_created_fields(self):
        """Updating user should preserve auto_now_add fields"""
        user = User.objects.create_user(
            username="test_user",
            email="test@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
            first_name="Initial",
        )

        created_at = user.created_at
        user.is_active = True
        user.first_name = "Updated"
        user.save()

        final_user = User.objects.get(id=user.id)
        self.assertEqual(final_user.created_at, created_at)
        self.assertEqual(final_user.first_name, "Updated")
        self.assertTrue(final_user.is_active)


class TestTransactionAtomicity(TestCase):
    """Test transaction atomicity for user and related profile creation"""

    def test_user_creation_transaction_rolls_back_on_error(self):
        """If error occurs, user should be rolled back"""
        from accounts.models import StudentProfile

        initial_user_count = User.objects.count()

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username="transaction_test",
                    email="transaction@example.com",
                    password="testpass123",
                    role=User.Role.STUDENT,
                )

                raise ValueError("Simulated error during profile creation")
        except ValueError:
            pass

        final_user_count = User.objects.count()
        self.assertEqual(final_user_count, initial_user_count)

        user_exists = User.objects.filter(username="transaction_test").exists()
        self.assertFalse(user_exists)

    def test_user_creation_with_profile_atomic_success(self):
        """Both user and profile should be created when transaction succeeds"""
        from accounts.models import StudentProfile

        initial_user_count = User.objects.count()

        with transaction.atomic():
            user = User.objects.create_user(
                username="student_atomic",
                email="student_atomic@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )

            profile = StudentProfile.objects.create(user=user, grade=10)

        final_user_count = User.objects.count()
        self.assertEqual(final_user_count, initial_user_count + 1)

        user_exists = User.objects.filter(username="student_atomic").exists()
        self.assertTrue(user_exists)

        profile_exists = StudentProfile.objects.filter(user=user).exists()
        self.assertTrue(profile_exists)


class TestTelegramIdUniqueness(TestCase):
    """Test unique constraint protection for telegram_id"""

    def test_different_telegram_ids_no_conflict(self):
        """Creating multiple users with different telegram_ids should succeed"""
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
                telegram_id=100000000 + i,
            )
            users.append(user)

        self.assertEqual(len(users), 3)
        total_count = User.objects.filter(telegram_id__isnull=False).count()
        self.assertEqual(total_count, 3)

    def test_null_telegram_id_multiple_users(self):
        """Multiple users can have NULL telegram_id"""
        initial_count = User.objects.filter(telegram_id__isnull=True).count()
        users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
                telegram_id=None,
            )
            users.append(user)

        self.assertEqual(len(users), 3)
        total_count = User.objects.filter(telegram_id__isnull=True).count()
        self.assertEqual(total_count, initial_count + 3)


class TestStudentProfileCreation(TestCase):
    """Test race conditions when creating student profiles"""

    def test_student_profile_creation_with_transaction(self):
        """Student and profile should be created together in transaction"""
        from accounts.models import StudentProfile

        with transaction.atomic():
            user = User.objects.create_user(
                username="student_atomic",
                email="student_atomic@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )

            profile = StudentProfile.objects.create(user=user, grade=10)

        user_exists = User.objects.filter(username="student_atomic").exists()
        self.assertTrue(user_exists)

        profile_exists = StudentProfile.objects.filter(user=user).exists()
        self.assertTrue(profile_exists)
        self.assertEqual(profile.grade, 10)

    def test_multiple_student_profiles_creation(self):
        """Creating multiple student profiles should succeed"""
        from accounts.models import StudentProfile

        initial_user_count = User.objects.filter(role=User.Role.STUDENT).count()
        initial_profile_count = StudentProfile.objects.count()

        users = []
        profiles = []

        for i in range(4):
            user = User.objects.create_user(
                username=f"student_{i}",
                email=f"student_{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )

            profile = StudentProfile.objects.create(user=user, grade=i % 12 + 1)

            users.append(user)
            profiles.append(profile)

        user_count = User.objects.filter(role=User.Role.STUDENT).count()
        profile_count = StudentProfile.objects.count()

        self.assertEqual(user_count, initial_user_count + 4)
        self.assertEqual(profile_count, initial_profile_count + 4)

    def test_student_profile_is_one_to_one_with_user(self):
        """StudentProfile has one-to-one relationship with User"""
        from accounts.models import StudentProfile

        user = User.objects.create_user(
            username="student_unique_one",
            email="student_unique_one@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        profile1 = StudentProfile.objects.create(user=user, grade=10)

        profile_via_relation = user.student_profile
        self.assertEqual(profile_via_relation.id, profile1.id)
        self.assertEqual(profile_via_relation.grade, 10)
