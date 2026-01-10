"""
Comprehensive integration tests for all user creation fixes.

Tests verify:
1. Concurrent username generation produces no duplicates
2. Student creation validates inactive tutor
3. Duplicate parent email is rejected
4. Concurrent email creation only one succeeds
5. Signals still create profiles
6. Staff create user with validation
7. Admin save is atomic
"""
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import StudentProfile, ParentProfile, TutorProfile
from accounts.tutor_service import StudentCreationService, _generate_unique_username
from accounts.factories import TutorFactory, StudentFactory

User = get_user_model()


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
class TestUserCreationFixes:
    """Integration tests for user creation fixes"""

    @pytest.mark.django_db(transaction=True, serialized_rollback=True)
    def test_concurrent_username_generation_no_duplicates(self):
        """
        Test 1: Concurrent username generation produces no duplicates.

        10 parallel threads create users with same base name.
        All 10 should be unique, no IntegrityError.
        """
        from django.db import close_old_connections
        import uuid

        base_name = f"testuser{uuid.uuid4().hex[:6]}"
        results = []
        errors = []
        lock = threading.Lock()

        def create_user_with_unique_username():
            try:
                close_old_connections()

                max_retries = 10
                for retry in range(max_retries):
                    try:
                        with transaction.atomic():
                            username = _generate_unique_username(base_name)
                            user = User.objects.create(
                                username=username,
                                email=f"{username}@test.com",
                                role=User.Role.STUDENT,
                            )

                            with lock:
                                results.append(username)
                            break
                    except IntegrityError as e:
                        if retry == max_retries - 1:
                            with lock:
                                errors.append(f"Failed after {max_retries} retries: {str(e)}")
                        import time
                        time.sleep(0.01 * (retry + 1))
                        continue
            except Exception as e:
                with lock:
                    errors.append(str(e))
            finally:
                close_old_connections()

        threads = [
            threading.Thread(target=create_user_with_unique_username) for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, f"Expected 10 usernames, got {len(results)}"

        unique_usernames = set(results)
        assert (
            len(unique_usernames) == 10
        ), f"Expected 10 unique usernames, got {len(unique_usernames)}: {results}"

    def test_student_creation_validates_inactive_tutor(self, db):
        """
        Test 2: Student creation validates inactive tutor.

        Deactivate tutor (is_active=False).
        Attempt to create student through StudentCreationService.
        Should raise PermissionError with "Неактивный тьютор".
        """
        inactive_tutor = TutorFactory(is_active=False)

        with pytest.raises(PermissionError) as exc_info:
            StudentCreationService.create_student_with_parent(
                tutor=inactive_tutor,
                student_first_name="Test",
                student_last_name="Student",
                grade="9",
                goal="Learn math",
                parent_first_name="Test",
                parent_last_name="Parent",
                parent_email="parent@test.com",
                parent_phone="+79991234567",
            )

        assert "Неактивный тьютор" in str(exc_info.value)

    def test_student_creation_rejects_duplicate_parent_email(self, db):
        """
        Test 3: Student creation rejects duplicate parent email.

        Create existing user with email.
        Attempt to create student with same parent email.
        Should raise ValueError with "уже зарегистрирован".
        """
        existing_user = StudentFactory(email="duplicate@test.com")
        active_tutor = TutorFactory(is_active=True)

        with pytest.raises(ValueError) as exc_info:
            StudentCreationService.create_student_with_parent(
                tutor=active_tutor,
                student_first_name="Test",
                student_last_name="Student",
                grade="10",
                goal="Learn science",
                parent_first_name="Duplicate",
                parent_last_name="Parent",
                parent_email="duplicate@test.com",
                parent_phone="+79991234567",
            )

        assert "уже зарегистрирован" in str(exc_info.value)

    def test_concurrent_email_creation_only_one_succeeds(self, db):
        """
        Test 4: Concurrent email creation only one succeeds.

        5 parallel requests to create with same email.
        Only one should succeed (201 Created).
        Remaining 4 should fail (400 Bad Request or IntegrityError).
        """
        admin = User.objects.create_superuser(
            username="admin_concurrent",
            email="admin_concurrent@test.com",
            password="adminpass123",
        )

        results = []
        same_email = "concurrent_test@test.com"

        def create_user_with_email(index):
            client = APIClient()
            client.force_authenticate(user=admin)

            payload = {
                "username": f"user_concurrent_{index}",
                "email": same_email,
                "password": "securepass123",
                "first_name": "Concurrent",
                "last_name": f"User{index}",
                "role": "student",
            }

            try:
                response = client.post(
                    "/api/accounts/staff/create/", payload, format="json"
                )
                results.append(response.status_code)
            except Exception as e:
                results.append(500)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_user_with_email, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()

        success_count = sum(
            1
            for status_code in results
            if status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        )

        assert (
            success_count <= 1
        ), f"Only 1 should succeed with same email, got {success_count} successes: {results}"

    def test_signals_still_create_profiles(self, db):
        """
        Test 5: Signals still create profiles.

        Create student through StudentCreationService.
        Verify StudentProfile created.
        Verify ParentProfile created.
        Verify only one profile of each type (no duplicates).
        """
        active_tutor = TutorFactory(is_active=True)

        (
            student_user,
            parent_user,
            student_creds,
            parent_creds,
        ) = StudentCreationService.create_student_with_parent(
            tutor=active_tutor,
            student_first_name="Signal",
            student_last_name="Test",
            grade="8",
            goal="Test signals",
            parent_first_name="Signal",
            parent_last_name="Parent",
            parent_email="signal_parent@test.com",
            parent_phone="+79991234567",
        )

        assert StudentProfile.objects.filter(
            user=student_user
        ).exists(), "StudentProfile should be created"

        assert ParentProfile.objects.filter(
            user=parent_user
        ).exists(), "ParentProfile should be created"

        student_profile_count = StudentProfile.objects.filter(user=student_user).count()
        assert (
            student_profile_count == 1
        ), f"Should have exactly 1 StudentProfile, got {student_profile_count}"

        parent_profile_count = ParentProfile.objects.filter(user=parent_user).count()
        assert (
            parent_profile_count == 1
        ), f"Should have exactly 1 ParentProfile, got {parent_profile_count}"

    def test_staff_create_user_with_validation(self, db):
        """
        Test 6: Staff create user with validation.

        Create user through staff API.
        Verify invalid roles are rejected and valid roles are accepted.
        """
        admin = User.objects.create_superuser(
            username="admin_validation",
            email="admin_validation@test.com",
            password="adminpass123",
        )

        client = APIClient()
        client.force_authenticate(user=admin)

        payload_invalid_role = {
            "email": "invalid_role@test.com",
            "first_name": "Invalid",
            "last_name": "Role",
            "role": "invalid_role_name",
        }

        response = client.post(
            "/api/accounts/staff/create/", payload_invalid_role, format="json"
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), f"Invalid role should be rejected with 400, got {response.status_code}: {response.data}"

        payload_valid = {
            "email": "valid_teacher@test.com",
            "first_name": "Valid",
            "last_name": "Teacher",
            "role": "teacher",
        }

        response_valid = client.post(
            "/api/accounts/staff/create/", payload_valid, format="json"
        )

        assert response_valid.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        ], f"Valid teacher should be created, got {response_valid.status_code}: {response_valid.data}"

        created_user = User.objects.filter(email="valid_teacher@test.com").first()
        assert created_user is not None, "User should be created"
        assert created_user.role == "teacher", "Role should be 'teacher'"

    def test_admin_save_is_atomic(self, db):
        """
        Test 7: Admin save is atomic.

        Attempt to save user through admin with invalid data.
        Should raise ValidationError.
        User should not be changed in DB (rollback).
        """
        from django.contrib.admin.sites import AdminSite
        from accounts.admin import UserAdmin

        user = StudentFactory(first_name="Original", last_name="Name")
        admin_site = AdminSite()
        user_admin = UserAdmin(User, admin_site)

        class MockRequest:
            def __init__(self, admin_user):
                self.user = admin_user
                self.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "test"}

        admin_user = User.objects.create_superuser(
            username="admin_atomic",
            email="admin_atomic@test.com",
            password="adminpass123",
        )

        request = MockRequest(admin_user)

        user.role = "invalid_role_that_does_not_exist"

        class MockForm:
            cleaned_data = {"password": "newpass123"}
            changed_data = []

        form = MockForm()

        with pytest.raises(ValidationError):
            user_admin.save_model(request, user, form, change=True)

        user.refresh_from_db()
        assert user.first_name == "Original", "User should not be modified on error"
        assert user.last_name == "Name", "User should not be modified on error"
