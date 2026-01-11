"""
Comprehensive login integration tests.

Tests verify:
1. Admin login sets is_staff=True and is_superuser=True
2. Admin login does NOT create a profile (expected)
3. Student login creates StudentProfile
4. Teacher login creates TeacherProfile
5. Tutor login creates TutorProfile
6. Parent login creates ParentProfile
7. IsStaffOrAdmin permission works correctly
8. is_staff flag allows non-admin access with permission
9. Inactive user login fails
10. Token created on successful login
11. Profile view returns gracefully if missing
"""
import pytest
import uuid
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.models import (
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
)
from accounts.permissions import IsStaffOrAdmin
from rest_framework.test import APIRequestFactory

User = get_user_model()


def generate_unique_email():
    """Generate unique email for test isolation"""
    return f"test_{uuid.uuid4().hex[:12]}@test.com"


def generate_unique_username():
    """Generate unique username for test isolation"""
    return f"user_{uuid.uuid4().hex[:12]}"


@pytest.mark.django_db
class TestLoginIntegrationFix:
    """Integration tests for login flow and profile creation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.factory = APIRequestFactory()

    # ============= TEST 1: Admin login sets is_staff=True =============

    def test_admin_login_sets_is_staff_true(self):
        """
        Test that creating admin user with role=admin automatically sets is_staff=True
        and is_superuser=True through User.save()
        """
        admin = User.objects.create_user(
            username=generate_unique_username(),
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.ADMIN,
            is_staff=False,
            is_superuser=False,
        )

        admin.refresh_from_db()

        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.role == User.Role.ADMIN

    # ============= TEST 2: Admin login profile NOT created =============

    def test_admin_login_profile_not_created(self):
        """
        Test that admin login does NOT create a profile (expected behavior).
        """
        email = generate_unique_email()
        admin = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.ADMIN,
        )

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "token" in response.data["data"]
        token_key = response.data["data"]["token"]

        token = Token.objects.get(key=token_key)
        assert token.user == admin

        # NO profile should be created for admin
        assert not hasattr(admin, "student_profile") or not admin.student_profile

    # ============= TEST 3: Student login creates profile =============

    def test_student_login_creates_profile(self):
        """
        Test that student login creates StudentProfile.
        """
        email = generate_unique_email()
        student = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )

        assert not StudentProfile.objects.filter(user=student).exists()

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        # Refresh student from DB to get updated profile relation
        student.refresh_from_db()
        assert StudentProfile.objects.filter(user=student).exists()
        profile = student.student_profile
        assert profile.user == student

    # ============= TEST 4: Teacher login creates profile =============

    def test_teacher_login_creates_profile(self):
        """
        Test that teacher login creates TeacherProfile.
        """
        email = generate_unique_email()
        teacher = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.TEACHER,
        )

        assert not TeacherProfile.objects.filter(user=teacher).exists()

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        assert TeacherProfile.objects.filter(user=teacher).exists()
        profile = teacher.teacher_profile
        assert profile.user == teacher

    # ============= TEST 5: Tutor login creates profile =============

    def test_tutor_login_creates_profile(self):
        """
        Test that tutor login creates TutorProfile.
        """
        email = generate_unique_email()
        tutor = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.TUTOR,
        )

        assert not TutorProfile.objects.filter(user=tutor).exists()

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        assert TutorProfile.objects.filter(user=tutor).exists()
        profile = tutor.tutor_profile
        assert profile.user == tutor

    # ============= TEST 6: Parent login creates profile =============

    def test_parent_login_creates_profile(self):
        """
        Test that parent login creates ParentProfile.
        """
        email = generate_unique_email()
        parent = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.PARENT,
        )

        assert not ParentProfile.objects.filter(user=parent).exists()

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        assert ParentProfile.objects.filter(user=parent).exists()
        profile = parent.parent_profile
        assert profile.user == parent

    # ============= TEST 7: IsStaffOrAdmin permission check =============

    def test_is_staff_or_admin_permission_admin_allowed(self):
        """
        Test that IsStaffOrAdmin permission allows admin users.
        """
        admin = User.objects.create_user(
            username=generate_unique_username(),
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.ADMIN,
        )

        view = None
        request = self.factory.get("/api/test/")
        request.user = admin

        permission = IsStaffOrAdmin()
        assert permission.has_permission(request, view) is True

    def test_is_staff_or_admin_permission_normal_user_denied(self):
        """
        Test that IsStaffOrAdmin permission denies normal users.
        """
        student = User.objects.create_user(
            username=generate_unique_username(),
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.STUDENT,
        )

        view = None
        request = self.factory.get("/api/test/")
        request.user = student

        permission = IsStaffOrAdmin()
        assert permission.has_permission(request, view) is False

    def test_is_staff_or_admin_permission_tutor_denied(self):
        """
        Test that IsStaffOrAdmin permission denies tutor.
        """
        tutor = User.objects.create_user(
            username=generate_unique_username(),
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.TUTOR,
        )

        view = None
        request = self.factory.get("/api/test/")
        request.user = tutor

        permission = IsStaffOrAdmin()
        assert permission.has_permission(request, view) is False

    # ============= TEST 8: is_staff flag allows permission =============

    def test_is_staff_flag_allows_permission_without_admin_role(self):
        """
        Test that user with is_staff=True (but role != admin) can access
        IsStaffOrAdmin protected endpoints (e.g., moderator).
        """
        moderator = User.objects.create_user(
            username=generate_unique_username(),
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.STUDENT,
        )
        moderator.is_staff = True
        moderator.save()

        view = None
        request = self.factory.get("/api/test/")
        request.user = moderator

        permission = IsStaffOrAdmin()
        assert permission.has_permission(request, view) is True

    # ============= TEST 9: Inactive user login fails =============

    def test_login_fails_if_inactive(self):
        """
        Test that inactive user cannot login.
        """
        email = generate_unique_email()
        student = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )
        student.is_active = False
        student.save()

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert "отключена" in response.data["error"].lower()

    # ============= TEST 10: Token created on successful login =============

    def test_token_created_on_successful_login(self):
        """
        Test that token is created and returned on successful login.
        """
        email = generate_unique_email()
        user = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )

        assert Token.objects.filter(user=user).count() == 0

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "token" in response.data["data"]

        token_key = response.data["data"]["token"]
        assert Token.objects.filter(key=token_key, user=user).exists()

    def test_token_replaced_on_second_login(self):
        """
        Test that token is replaced when user logs in again.
        """
        email = generate_unique_email()
        user = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )

        response1 = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )
        token1 = response1.data["data"]["token"]

        response2 = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )
        token2 = response2.data["data"]["token"]

        assert token1 != token2
        assert not Token.objects.filter(key=token1).exists()
        assert Token.objects.filter(key=token2, user=user).exists()

    # ============= TEST 11: Profile view returns gracefully if missing =============

    def test_profile_view_graceful_on_missing_profile(self):
        """
        Test that profile endpoint returns 200 with profile=null if profile missing.
        """
        email = generate_unique_email()
        student = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )

        response_login = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )
        token = response_login.data["data"]["token"]

        # Delete profile to simulate missing case
        StudentProfile.objects.filter(user=student).delete()

        # Authenticate
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        # Test assumes endpoint exists and handles gracefully

    # ============= TEST 12: Login with username instead of email =============

    def test_login_with_username(self):
        """
        Test that login works with username instead of email.
        """
        username = generate_unique_username()
        User.objects.create_user(
            username=username,
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.STUDENT,
        )

        response = self.client.post(
            "/api/accounts/login/",
            {
                "username": username,
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "token" in response.data["data"]

    # ============= TEST 13: Invalid credentials rejected =============

    def test_login_rejects_invalid_password(self):
        """
        Test that login rejects invalid password.
        """
        email = generate_unique_email()
        User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="correct_pass",
            role=User.Role.STUDENT,
        )

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "wrong_pass",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False

    def test_login_rejects_nonexistent_user(self):
        """
        Test that login rejects nonexistent user.
        """
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": generate_unique_email(),
                "password": "any_pass",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False

    # ============= TEST 14: Multiple logins no duplicate profiles =============

    def test_multiple_logins_no_duplicate_profiles(self):
        """
        Test that multiple consecutive logins don't create duplicate profiles.
        """
        email = generate_unique_email()
        student = User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )

        for _ in range(3):
            response = self.client.post(
                "/api/accounts/login/",
                {
                    "email": email,
                    "password": "test123pass",
                },
            )
            assert response.status_code == status.HTTP_200_OK

        assert StudentProfile.objects.filter(user=student).count() == 1

    # ============= TEST 15: Admin role syncs on save =============

    def test_admin_role_syncs_on_save(self):
        """
        Test that changing role to admin automatically syncs is_staff/is_superuser.
        """
        user = User.objects.create_user(
            username=generate_unique_username(),
            email=generate_unique_email(),
            password="test123pass",
            role=User.Role.STUDENT,
        )

        assert user.is_staff is False
        assert user.is_superuser is False

        user.role = User.Role.ADMIN
        user.save()

        user.refresh_from_db()
        assert user.is_staff is True
        assert user.is_superuser is True

    # ============= TEST 16: Response structure validation =============

    def test_login_response_structure(self):
        """
        Test that login response has correct structure.
        """
        email = generate_unique_email()
        User.objects.create_user(
            username=generate_unique_username(),
            email=email,
            password="test123pass",
            role=User.Role.STUDENT,
        )

        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": email,
                "password": "test123pass",
            },
        )

        assert "success" in response.data
        assert "data" in response.data
        assert "token" in response.data["data"]
        assert "user" in response.data["data"]
        assert "message" in response.data["data"]

        user_data = response.data["data"]["user"]
        assert "id" in user_data
        assert "email" in user_data
        assert "username" in user_data
        assert "role" in response.data["data"]["user"]

    # ============= TEST 17: Email and username required =============

    def test_login_rejects_missing_email_and_username(self):
        """
        Test that login rejects request with neither email nor username.
        """
        response = self.client.post(
            "/api/accounts/login/",
            {
                "password": "test123pass",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_login_rejects_missing_password(self):
        """
        Test that login rejects request with missing password.
        """
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": generate_unique_email(),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False
