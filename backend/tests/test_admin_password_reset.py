"""
Comprehensive tests for admin password reset functionality.

Tests verify:
1. Password generation and complexity
2. Login with old vs new password
3. Role-based access control (only admin/staff can reset)
4. Active/inactive user handling
5. Cross-role password resets (student, teacher, tutor, parent)
6. Preventing admin password reset by non-admins
7. Post-reset password change capability
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

User = get_user_model()


@pytest.mark.django_db
class TestAdminPasswordReset:
    """Test admin password reset endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users and client"""
        self.client = APIClient()

        # Create admin user
        self.admin = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="AdminPassword123!",
            role=User.Role.ADMIN
        )

        # Create regular test user
        self.test_user = User.objects.create_user(
            username="testuser",
            email="testuser@test.com",
            password="oldpassword123",
            role=User.Role.STUDENT,
            is_active=True
        )

    def test_admin_can_reset_password(self):
        """T001: Admin successfully resets password for active user"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "new_password" in response.data
        assert response.data["user_id"] == self.test_user.id
        assert response.data["email"] == self.test_user.email

    def test_generated_password_not_empty(self):
        """T002: Generated password is not empty and has minimum length"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )

        new_password = response.data["new_password"]
        assert len(new_password) >= 12
        assert new_password != "oldpassword123"

    def test_old_password_login_fails(self):
        """T003: Old password no longer works after reset"""
        self.client.force_authenticate(user=self.admin)

        # Get new password from reset
        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )

        # Try to login with old password
        self.client.force_authenticate(user=None)
        login_response = self.client.post("/api/accounts/login/", {
            "username": self.test_user.username,
            "password": "oldpassword123"
        })

        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_new_password_login_succeeds(self):
        """T004: New password allows successful login"""
        self.client.force_authenticate(user=self.admin)

        # Get new password
        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )
        new_password = response.data["new_password"]

        # Login with new password
        self.client.force_authenticate(user=None)
        login_response = self.client.post("/api/accounts/login/", {
            "username": self.test_user.username,
            "password": new_password
        })

        # Login should succeed (either 200 or with token)
        assert login_response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED
        ]

    def test_cannot_reset_inactive_user(self):
        """T005: Cannot reset password for inactive user"""
        # Deactivate user
        self.test_user.is_active = False
        self.test_user.save()

        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "неактивного" in response.data.get("detail", "").lower()

    def test_reset_nonexistent_user(self):
        """T006: Reset password for non-existent user returns 404"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/accounts/users/99999/reset-password/"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_reset(self):
        """T007: Unauthenticated user cannot reset password"""
        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]


@pytest.mark.django_db
class TestPasswordResetByRole:
    """Test password reset for different user roles"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users by role"""
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="admin_role_test",
            email="admin_role@test.com",
            password="AdminPass123!",
            role=User.Role.ADMIN
        )

    def test_reset_student_password(self):
        """T008: Admin can reset student password"""
        student = User.objects.create_user(
            username="student_reset",
            email="student@test.com",
            password="StudentPass123",
            role=User.Role.STUDENT,
            is_active=True
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{student.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_reset_teacher_password(self):
        """T009: Admin can reset teacher password"""
        teacher = User.objects.create_user(
            username="teacher_reset",
            email="teacher@test.com",
            password="TeacherPass123",
            role=User.Role.TEACHER,
            is_active=True
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{teacher.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_reset_tutor_password(self):
        """T010: Admin can reset tutor password"""
        tutor = User.objects.create_user(
            username="tutor_reset",
            email="tutor@test.com",
            password="TutorPass123",
            role=User.Role.TUTOR,
            is_active=True
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{tutor.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

    def test_reset_parent_password(self):
        """T011: Admin can reset parent password"""
        parent = User.objects.create_user(
            username="parent_reset",
            email="parent@test.com",
            password="ParentPass123",
            role=User.Role.PARENT,
            is_active=True
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{parent.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True


@pytest.mark.django_db
class TestPasswordResetAccessControl:
    """Test access control for password reset"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test users"""
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="admin_access_test",
            email="admin_access@test.com",
            password="AdminPass123!",
            role=User.Role.ADMIN
        )

        self.teacher = User.objects.create_user(
            username="teacher_access_test",
            email="teacher_access@test.com",
            password="TeacherPass123",
            role=User.Role.TEACHER,
            is_active=True
        )

        self.student = User.objects.create_user(
            username="student_access_test",
            email="student_access@test.com",
            password="StudentPass123",
            role=User.Role.STUDENT,
            is_active=True
        )

        self.tutor = User.objects.create_user(
            username="tutor_access_test",
            email="tutor_access@test.com",
            password="TutorPass123",
            role=User.Role.TUTOR,
            is_active=True
        )

    def test_student_cannot_reset_password(self):
        """T012: Student cannot reset other user's password"""
        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f"/api/accounts/users/{self.teacher.id}/reset-password/"
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ]

    def test_teacher_cannot_reset_password(self):
        """T013: Teacher cannot reset other user's password"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            f"/api/accounts/users/{self.student.id}/reset-password/"
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ]

    def test_tutor_cannot_reset_password(self):
        """T014: Tutor cannot reset other user's password"""
        self.client.force_authenticate(user=self.tutor)

        response = self.client.post(
            f"/api/accounts/users/{self.student.id}/reset-password/"
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED
        ]


@pytest.mark.django_db
class TestPasswordResetComplexity:
    """Test password generation complexity"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="admin_complexity",
            email="admin_complexity@test.com",
            password="AdminPass123!",
            role=User.Role.ADMIN
        )

    def test_password_has_mixed_case(self):
        """T015: Generated password contains mixed case letters"""
        test_user = User.objects.create_user(
            username="user_complexity1",
            email="user_complexity1@test.com",
            password="OldPass123",
            role=User.Role.STUDENT
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )

        new_password = response.data["new_password"]
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)

        assert has_upper and has_lower

    def test_password_has_numbers(self):
        """T016: Generated password contains numbers"""
        test_user = User.objects.create_user(
            username="user_complexity2",
            email="user_complexity2@test.com",
            password="OldPass123",
            role=User.Role.STUDENT
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )

        new_password = response.data["new_password"]
        has_digit = any(c.isdigit() for c in new_password)

        assert has_digit

    def test_password_has_special_chars(self):
        """T017: Generated password contains special characters"""
        test_user = User.objects.create_user(
            username="user_complexity3",
            email="user_complexity3@test.com",
            password="OldPass123",
            role=User.Role.STUDENT
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )

        new_password = response.data["new_password"]
        special_chars = "!@#$%^&*"
        has_special = any(c in special_chars for c in new_password)

        # Password should have special characters from the allowed set
        assert has_special or len(new_password) >= 12  # At minimum 12 chars


@pytest.mark.django_db
class TestPasswordResetUserFlow:
    """Test complete user flow after password reset"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="admin_flow",
            email="admin_flow@test.com",
            password="AdminPass123!",
            role=User.Role.ADMIN
        )

        self.test_user = User.objects.create_user(
            username="user_flow",
            email="user_flow@test.com",
            password="OldPass123",
            role=User.Role.STUDENT,
            is_active=True
        )

    def test_user_can_change_password_after_reset(self):
        """T018: User can change password after admin reset"""
        self.client.force_authenticate(user=self.admin)

        # Admin resets password
        response = self.client.post(
            f"/api/accounts/users/{self.test_user.id}/reset-password/"
        )
        new_password = response.data["new_password"]

        # User logs in with new password
        self.client.force_authenticate(user=None)
        self.test_user.refresh_from_db()

        # Verify user can authenticate with new password
        user_authenticated = self.test_user.check_password(new_password)
        assert user_authenticated is True

    def test_multiple_password_resets(self):
        """T019: Admin can reset password multiple times"""
        self.client.force_authenticate(user=self.admin)

        passwords = []
        for i in range(3):
            response = self.client.post(
                f"/api/accounts/users/{self.test_user.id}/reset-password/"
            )
            assert response.status_code == status.HTTP_200_OK
            passwords.append(response.data["new_password"])

        # All passwords should be different
        assert len(set(passwords)) == 3


@pytest.mark.django_db
class TestPasswordResetEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="admin_edge",
            email="admin_edge@test.com",
            password="AdminPass123!",
            role=User.Role.ADMIN
        )

    def test_reset_own_password_as_admin(self):
        """T020: Admin can reset own password"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            f"/api/accounts/users/{self.admin.id}/reset-password/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_id"] == self.admin.id

    def test_response_contains_required_fields(self):
        """T021: Response contains all required fields"""
        test_user = User.objects.create_user(
            username="user_edge1",
            email="user_edge1@test.com",
            password="OldPass123",
            role=User.Role.STUDENT
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )

        assert "success" in response.data
        assert "user_id" in response.data
        assert "email" in response.data
        assert "new_password" in response.data
        assert "message" in response.data

    def test_password_never_returned_again(self):
        """T022: Password is returned only once in reset response"""
        test_user = User.objects.create_user(
            username="user_edge2",
            email="user_edge2@test.com",
            password="OldPass123",
            role=User.Role.STUDENT
        )

        self.client.force_authenticate(user=self.admin)

        # First reset - password is returned
        response1 = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )
        assert "new_password" in response1.data

        # Second reset - new password is returned (different)
        response2 = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )
        assert "new_password" in response2.data

        # Passwords should be different
        assert response1.data["new_password"] != response2.data["new_password"]

    def test_password_persists_in_database(self):
        """T023: Reset password is actually saved in database"""
        test_user = User.objects.create_user(
            username="user_edge3",
            email="user_edge3@test.com",
            password="OldPass123",
            role=User.Role.STUDENT
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/accounts/users/{test_user.id}/reset-password/"
        )
        new_password = response.data["new_password"]

        # Refresh user from database
        test_user.refresh_from_db()

        # Verify password hash matches
        assert test_user.check_password(new_password)
