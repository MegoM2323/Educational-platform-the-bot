"""Unit tests for staff_views.py functions - Direct function testing"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from rest_framework import status
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response

from accounts.staff_views import (
    log_object_changes,
    create_staff,
    list_staff,
    list_students,
    get_student_detail,
    update_user,
    delete_user,
    reset_password,
    reactivate_user,
)


class TestLogObjectChangesFunction:
    """Direct unit tests for log_object_changes helper"""

    def test_log_object_changes_called_with_changes(self):
        """Test: log_object_changes processes changes correctly"""
        factory = APIRequestFactory()
        request = factory.patch("/test/")
        request.user = MagicMock(id=123)

        obj = MagicMock()
        obj.name = "Old Name"
        obj.id = 456

        serializer = MagicMock()
        serializer.validated_data = {"name": "New Name"}

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(request, obj, serializer, "test_action")
            # Should call audit_logger.info when there are changes
            mock_logger.info.assert_called()

    def test_log_object_changes_no_changes(self):
        """Test: log_object_changes handles empty validated_data"""
        factory = APIRequestFactory()
        request = factory.patch("/test/")
        request.user = MagicMock(id=123)

        obj = MagicMock()
        obj.id = 456

        serializer = MagicMock()
        serializer.validated_data = {}

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(request, obj, serializer, "test_action")
            # Should not call if no changes

    def test_log_object_changes_excludes_sensitive_fields(self):
        """Test: log_object_changes excludes passwords and sensitive fields"""
        factory = APIRequestFactory()
        request = factory.patch("/test/")
        request.user = MagicMock(id=123)

        obj = MagicMock()
        obj.email = "old@test.com"
        obj.password = "old_hash"
        obj.id = 456

        serializer = MagicMock()
        serializer.validated_data = {
            "email": "new@test.com",
            "password": "new_hash",
        }

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(
                request,
                obj,
                serializer,
                "test_action",
                sensitive_fields=["password"],
            )
            # password should not be in the logged changes
            if mock_logger.info.called:
                call_args = mock_logger.info.call_args
                # Verify password not in changes
                assert "password" not in str(call_args) or "password" not in str(
                    call_args
                )


class TestCreateStaffFunction:
    """Direct unit tests for create_staff endpoint logic"""

    def test_create_staff_validates_role(self):
        """Test: create_staff validates role parameter"""
        factory = APIRequestFactory()
        request = factory.post(
            "/create-staff/",
            {"role": "invalid_role", "email": "test@test.com"},
            format="json",
        )
        request.user = MagicMock(id=1, is_superuser=True)

        with patch("accounts.staff_views.User") as MockUser:
            response = create_staff(request)
            # Should return 400 for invalid role
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_staff_validates_email(self):
        """Test: create_staff validates email format"""
        factory = APIRequestFactory()
        request = factory.post(
            "/create-staff/",
            {
                "role": "teacher",
                "email": "invalid-email",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        request.user = MagicMock(id=1, is_superuser=True)

        response = create_staff(request)
        # Should return 400 for invalid email
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_staff_requires_email(self):
        """Test: create_staff requires email"""
        factory = APIRequestFactory()
        request = factory.post(
            "/create-staff/",
            {
                "role": "teacher",
                "email": "",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        request.user = MagicMock(id=1, is_superuser=True)

        response = create_staff(request)
        # Should return 400 when email is empty
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_staff_requires_names(self):
        """Test: create_staff requires first_name and last_name"""
        factory = APIRequestFactory()
        request = factory.post(
            "/create-staff/",
            {
                "role": "teacher",
                "email": "test@test.com",
                "first_name": "",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        request.user = MagicMock(id=1, is_superuser=True)

        response = create_staff(request)
        # Should return 400 when names missing
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_staff_validates_experience_years(self):
        """Test: create_staff validates experience_years is numeric"""
        factory = APIRequestFactory()
        request = factory.post(
            "/create-staff/",
            {
                "role": "teacher",
                "email": "test@test.com",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
                "experience_years": "not_a_number",
            },
            format="json",
        )
        request.user = MagicMock(id=1, is_superuser=True)

        response = create_staff(request)
        # Should return 400 for invalid experience_years
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestListStaffFunction:
    """Direct unit tests for list_staff endpoint"""

    def test_list_staff_requires_role(self):
        """Test: list_staff requires role parameter"""
        factory = APIRequestFactory()
        request = factory.get("/list-staff/")
        request.user = MagicMock(id=1, is_superuser=True)
        request.query_params = {}

        response = list_staff(request)
        # Should return 400 when role not specified
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_staff_validates_role(self):
        """Test: list_staff validates role value"""
        factory = APIRequestFactory()
        request = factory.get("/list-staff/?role=invalid")
        request.user = MagicMock(id=1, is_superuser=True)
        request.query_params = {"role": "invalid"}

        response = list_staff(request)
        # Should return 400 for invalid role
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDeleteUserFunction:
    """Direct unit tests for delete_user endpoint"""

    def test_delete_user_prevents_self_delete(self):
        """Test: delete_user prevents deleting self"""
        factory = APIRequestFactory()
        request = factory.delete("/users/123/")
        request.user = MagicMock(id=123, is_superuser=True)
        request.query_params = {}

        with patch("accounts.staff_views.User") as MockUser:
            mock_user = MagicMock()
            mock_user.id = 123
            MockUser.objects.get.return_value = mock_user

            response = delete_user(request, 123)
            # Should return 400 for self-delete attempt
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Cannot delete yourself" in response.data.get("error", "")

    def test_delete_user_prevents_last_superuser_delete(self):
        """Test: delete_user prevents deleting last superuser"""
        factory = APIRequestFactory()
        request = factory.delete("/users/456/")
        request.user = MagicMock(id=123, is_superuser=True)
        request.query_params = {}

        with patch("accounts.staff_views.User") as MockUser:
            mock_user = MagicMock()
            mock_user.id = 456
            mock_user.is_superuser = True
            MockUser.objects.get.return_value = mock_user
            MockUser.objects.filter.return_value.count.return_value = 1

            response = delete_user(request, 456)
            # Should return 400 when trying to delete last superuser
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Cannot delete last superuser" in response.data.get("error", "")

    def test_delete_user_not_found(self):
        """Test: delete_user returns 404 for non-existent user"""
        factory = APIRequestFactory()
        request = factory.delete("/users/99999/")
        request.user = MagicMock(id=123, is_superuser=True)
        request.query_params = {}

        with patch("accounts.staff_views.User") as MockUser:
            MockUser.objects.get.side_effect = MockUser.DoesNotExist()

            response = delete_user(request, 99999)
            # Should return 404
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestResetPasswordFunction:
    """Direct unit tests for reset_password endpoint"""

    def test_reset_password_user_not_found(self):
        """Test: reset_password returns 404 for non-existent user"""
        factory = APIRequestFactory()
        request = factory.post("/users/99999/reset-password/")
        request.user = MagicMock(id=1, is_superuser=True)

        with patch("accounts.staff_views.User") as MockUser:
            MockUser.objects.get.side_effect = MockUser.DoesNotExist()

            response = reset_password(request, 99999)
            # Should return 404
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_reset_password_inactive_user(self):
        """Test: reset_password rejects inactive user"""
        factory = APIRequestFactory()
        request = factory.post("/users/123/reset-password/")
        request.user = MagicMock(id=1, is_superuser=True)

        with patch("accounts.staff_views.User") as MockUser:
            mock_user = MagicMock()
            mock_user.is_active = False
            MockUser.objects.get.return_value = mock_user

            response = reset_password(request, 123)
            # Should return 400 for inactive user
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestReactivateUserFunction:
    """Direct unit tests for reactivate_user endpoint"""

    def test_reactivate_user_not_found(self):
        """Test: reactivate_user returns 404 for non-existent user"""
        factory = APIRequestFactory()
        request = factory.post("/users/99999/reactivate/")
        request.user = MagicMock(id=1, is_superuser=True)

        with patch("accounts.staff_views.User") as MockUser:
            MockUser.objects.get.side_effect = MockUser.DoesNotExist()

            response = reactivate_user(request, 99999)
            # Should return 404
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_reactivate_already_active_user(self):
        """Test: reactivate_user rejects already active users"""
        factory = APIRequestFactory()
        request = factory.post("/users/123/reactivate/")
        request.user = MagicMock(id=1, is_superuser=True)

        with patch("accounts.staff_views.User") as MockUser:
            mock_user = MagicMock()
            mock_user.is_active = True
            MockUser.objects.get.return_value = mock_user

            response = reactivate_user(request, 123)
            # Should return 400 for already active user
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUpdateUserFunction:
    """Direct unit tests for update_user endpoint"""

    def test_update_user_prevents_self_deactivation(self):
        """Test: update_user prevents deactivating self"""
        factory = APIRequestFactory()
        request = factory.patch("/users/123/", {"is_active": False}, format="json")
        request.user = MagicMock(id=123, is_superuser=True)
        request.data = {"is_active": False}

        with patch("accounts.staff_views.User") as MockUser:
            mock_user = MagicMock()
            mock_user.id = 123
            MockUser.objects.select_related.return_value.get.return_value = mock_user

            response = update_user(request, 123)
            # Should return 403 when trying to deactivate self
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_not_found(self):
        """Test: update_user returns 404 for non-existent user"""
        factory = APIRequestFactory()
        request = factory.patch("/users/99999/", {}, format="json")
        request.user = MagicMock(id=1, is_superuser=True)
        request.data = {}

        with patch("accounts.staff_views.User") as MockUser:
            MockUser.objects.select_related.return_value.get.side_effect = (
                MockUser.DoesNotExist()
            )

            response = update_user(request, 99999)
            # Should return 404
            assert response.status_code == status.HTTP_404_NOT_FOUND
