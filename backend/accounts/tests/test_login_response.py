"""
Test H3: Verify login endpoint returns complete user information.

Requirements:
- HTTP 200 OK on successful login
- Response contains: success, data (with token, user, message)
- User object includes: id, email, role, first_name, last_name, phone, avatar, full_name
- Token is valid for subsequent authenticated requests
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


@override_settings(ROOT_URLCONF="config.urls")
class TestLoginResponseStructure(TestCase):
    """Test H3: Login endpoint returns proper user information"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            phone="+1234567890",
            password="testpass123",
            role=User.Role.STUDENT,
        )

    def test_login_returns_http_200(self):
        """Login should return HTTP 200 OK"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_login_response_has_success_true(self):
        """Login response should have success=true"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        assert response.data.get("success") is True

    def test_login_response_has_data_wrapper(self):
        """Login response should have data wrapper"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        assert "data" in response.data
        assert isinstance(response.data["data"], dict)

    def test_login_response_includes_token(self):
        """Login response should include token"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        data = response.data.get("data", {})
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

    def test_login_response_includes_user_object(self):
        """Login response should include user object with all required fields"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        data = response.data.get("data", {})
        assert "user" in data
        user = data["user"]

        # Check required fields
        required_fields = [
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "full_name",
        ]
        for field in required_fields:
            assert field in user, f"Missing required field: {field}"

    def test_login_response_user_has_correct_values(self):
        """User object should contain correct values"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        user = response.data["data"]["user"]

        assert user["email"] == "test@example.com"
        assert user["first_name"] == "John"
        assert user["last_name"] == "Doe"
        assert user["role"] == "student"
        assert user["full_name"] == "John Doe"
        assert user["id"] == self.user.id

    def test_login_response_includes_optional_fields(self):
        """User object should include optional fields like phone, avatar"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        user = response.data["data"]["user"]

        assert "phone" in user
        assert "avatar" in user
        assert "is_verified" in user
        assert "is_active" in user
        assert "date_joined" in user
        assert user["phone"] == "+1234567890"

    def test_login_response_includes_role_display(self):
        """User object should include role_display (localized role name)"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        user = response.data["data"]["user"]
        assert "role_display" in user
        assert user["role_display"] == "Студент"  # Russian display

    def test_login_response_includes_message(self):
        """Login response should include success message"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        data = response.data.get("data", {})
        assert "message" in data
        assert "успеш" in data["message"].lower()  # Success message in Russian

    def test_returned_token_is_valid(self):
        """Token returned in login response should be valid for authenticated requests"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        token = response.data["data"]["token"]

        # Use token to access protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        profile_response = self.client.get("/api/auth/me/")

        assert profile_response.status_code == status.HTTP_200_OK
        assert profile_response.data["data"]["user"]["email"] == "test@example.com"

    def test_token_stored_in_database(self):
        """Token returned should be stored in Token table"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        token_key = response.data["data"]["token"]

        # Verify token exists in database
        token = Token.objects.get(key=token_key)
        assert token.user == self.user

    def test_login_with_username(self):
        """Login should also work with username"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "testuser",
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("success") is True
        assert "token" in response.data["data"]
        assert response.data["data"]["user"]["email"] == "test@example.com"

    def test_inactive_user_cannot_login(self):
        """Inactive user should not be able to login"""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data.get("success") is False

    def test_wrong_password_returns_401(self):
        """Wrong password should return 401 Unauthorized"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "wrongpassword",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data.get("success") is False

    def test_nonexistent_user_returns_401(self):
        """Non-existent user should return 401 Unauthorized"""
        response = self.client.post(
            "/api/auth/login/",
            {
                "email": "nonexistent@example.com",
                "password": "somepassword",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data.get("success") is False

    def test_different_user_roles(self):
        """Login response should work for all user roles"""
        roles_to_test = [
            (User.Role.TEACHER, "Преподаватель"),
            (User.Role.TUTOR, "Тьютор"),
            (User.Role.PARENT, "Родитель"),
        ]

        for role, role_display in roles_to_test:
            user = User.objects.create_user(
                username=f"user_{role}",
                email=f"{role}@example.com",
                first_name="Test",
                last_name="User",
                password="testpass123",
                role=role,
            )

            response = self.client.post(
                "/api/auth/login/",
                {
                    "email": f"{role}@example.com",
                    "password": "testpass123",
                },
                format="json",
            )

            assert response.status_code == status.HTTP_200_OK
            user_data = response.data["data"]["user"]
            assert user_data["role"] == role.value
            assert user_data["role_display"] == role_display

    def test_multiple_consecutive_logins(self):
        """Each login should create new token, invalidate old ones"""
        response1 = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        token1 = response1.data["data"]["token"]

        response2 = self.client.post(
            "/api/auth/login/",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        token2 = response2.data["data"]["token"]

        # Tokens should be different (old token should be deleted)
        assert token1 != token2

        # Only new token should be valid
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token1}")
        response = self.client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token2}")
        response = self.client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
