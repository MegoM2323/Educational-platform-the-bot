import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


@override_settings(ROOT_URLCONF="config.urls")
class TestChangePasswordWithTokenAuth(TestCase):
    """Test: change_password endpoint with TokenAuthentication"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="oldpassword123",
            role=User.Role.STUDENT,
        )
        # Create token for the user
        self.token = Token.objects.create(user=self.user)

    def test_change_password_with_token_auth_success(self):
        """Test successful password change with Token authentication"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("success") is True
        assert "message" in response.data

        # Verify password was actually changed
        self.user.refresh_from_db()
        assert self.user.check_password("newpassword123")

    def test_change_password_without_auth_fails(self):
        """Test password change without authentication returns 401"""
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_with_wrong_old_password_fails(self):
        """Test password change with wrong old password fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "wrongoldpassword",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data.get("success") is False

    def test_change_password_with_mismatched_passwords_fails(self):
        """Test password change with mismatched new passwords fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
                "new_password_confirm": "differentpassword123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data.get("success") is False

    def test_change_password_missing_fields(self):
        """Test password change with missing fields fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "oldpassword123",
                # Missing new_password and new_password_confirm
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data.get("success") is False

    def test_change_password_with_session_auth(self):
        """Test password change with session authentication also works"""
        # Use force_authenticate to simulate session-based auth
        self.client.force_authenticate(user=self.user)

        # Now change password using session authentication
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "oldpassword123",
                "new_password": "newpassword456",
                "new_password_confirm": "newpassword456",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("success") is True

        # Verify password was changed
        self.user.refresh_from_db()
        assert self.user.check_password("newpassword456")

    def test_change_password_preserves_user_data(self):
        """Test that password change doesn't affect other user data"""
        original_username = self.user.username
        original_email = self.user.email

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/accounts/change-password/",
            {
                "old_password": "oldpassword123",
                "new_password": "newpassword123",
                "new_password_confirm": "newpassword123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        self.user.refresh_from_db()
        assert self.user.username == original_username
        assert self.user.email == original_email
