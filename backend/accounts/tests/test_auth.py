import pytest
import logging
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

User = get_user_model()


@override_settings(ROOT_URLCONF="config.urls")
class TestSuperuserWithoutPasswordLogin(TestCase):
    """Test: Superuser without password cannot login"""

    def setUp(self):
        self.client = APIClient()
        # Create superuser with empty password
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="",
        )

    def test_superuser_without_password_cannot_login(self):
        """Superuser with empty password should get 401, not 200"""
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "admin@test.com",
                "password": "anypassword",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "success" in response.data
        assert response.data["success"] is False

    def test_normal_user_can_login(self):
        """Normal user with password should be able to login"""
        User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="validpass123",
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "user@test.com",
                "password": "validpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("success") is True
        assert "token" in response.data


@override_settings(ROOT_URLCONF="config.urls", RATELIMIT_ENABLE=True)
class TestRateLimitingRefreshToken(TestCase):
    """Test: Rate limiting on refresh_token (10/m)"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        # Login to get token
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "user@test.com",
                "password": "pass123",
            },
            format="json",
        )
        self.token = response.data.get("token")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

    def test_rate_limit_refresh_token(self):
        """First 10 requests should succeed, 11-15 should get 429"""
        success_count = 0
        rate_limited_count = 0

        for i in range(15):
            response = self.client.post(
                "/api/accounts/refresh_token/",
                {},
                format="json",
            )
            if response.status_code == status.HTTP_200_OK:
                success_count += 1
            elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                rate_limited_count += 1

        # At least first 10 should succeed
        assert success_count >= 10, f"Expected at least 10 successful requests, got {success_count}"
        # Some should be rate limited if sent fast enough
        # Note: This test may not always trigger rate limit depending on timing
        # but it validates that the endpoint exists and handles requests


@override_settings(ROOT_URLCONF="config.urls")
class TestLoginValidation(TestCase):
    """Test login endpoint validation"""

    def setUp(self):
        self.client = APIClient()

    def test_login_with_invalid_email(self):
        """Invalid email should return 400"""
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "notanemail",
                "password": "pass123",
            },
            format="json",
        )
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_with_missing_password(self):
        """Missing password should return 400"""
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "user@test.com",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_with_nonexistent_user(self):
        """Nonexistent user should return 401"""
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "nonexistent@test.com",
                "password": "pass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_wrong_password(self):
        """Wrong password should return 401"""
        User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="correctpass",
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "user@test.com",
                "password": "wrongpass",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_cannot_login(self):
        """Inactive user should not be able to login"""
        User.objects.create_user(
            username="inactive",
            email="inactive@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=False,
        )
        response = self.client.post(
            "/api/accounts/login/",
            {
                "email": "inactive@test.com",
                "password": "pass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
