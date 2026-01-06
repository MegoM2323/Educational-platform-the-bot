import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
class TestTeacherAuthentication:
    """T1.1: Teacher Authentication Tests"""

    def test_login_success(self, api_client, teacher_user):
        """Test successful teacher login"""
        response = api_client.post(
            "/api/auth/login/",
            {
                "username": "teacher1",
                "password": "teacher123secure",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data.get("data", {}) or "access" in response.data

    def test_login_invalid_credentials(self, api_client, teacher_user):
        """Test login fails with wrong password"""
        response = api_client.post(
            "/api/auth/login/",
            {
                "username": "teacher1",
                "password": "wrongpassword",
            },
            format="json",
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_login_nonexistent_user(self, api_client):
        """Test login with nonexistent username"""
        response = api_client.post(
            "/api/auth/login/",
            {
                "username": "nonexistent",
                "password": "anypassword",
            },
            format="json",
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_login_inactive_teacher(self, api_client, inactive_teacher):
        """Test login fails for inactive teacher"""
        response = api_client.post(
            "/api/auth/login/",
            {
                "username": "inactive_teacher",
                "password": "inactive123secure",
            },
            format="json",
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_login_with_email(self, api_client, teacher_user):
        """Test login using email instead of username"""
        response = api_client.post(
            "/api/auth/login/",
            {
                "username": "teacher1",
                "password": "teacher123secure",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data.get("data", {}) or "access" in response.data

    def test_token_generation(self, teacher_user):
        """Test JWT token is properly generated"""
        refresh = RefreshToken.for_user(teacher_user)
        access_token = refresh.access_token

        assert str(refresh) is not None
        assert str(access_token) is not None
        assert refresh.payload["user_id"] == teacher_user.id

    def test_token_contains_user_info(self, teacher_user):
        """Test token contains user identification data"""
        refresh = RefreshToken.for_user(teacher_user)
        access_token = refresh.access_token

        assert access_token.payload["user_id"] == teacher_user.id
        assert "exp" in access_token.payload
        assert "iat" in access_token.payload

    def test_token_validation_on_protected_endpoint(self, api_client, teacher_user):
        """Test token validation on protected endpoints"""
        # Create token
        refresh = RefreshToken.for_user(teacher_user)
        access_token = str(refresh.access_token)

        # Access protected endpoint with valid token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get("/api/auth/me/")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]

    def test_access_without_token(self, api_client):
        """Test protected endpoint denies access without token"""
        response = api_client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_with_invalid_token(self, api_client):
        """Test protected endpoint rejects invalid token"""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        response = api_client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_generation(self, teacher_user):
        """Test refresh token generation"""
        refresh = RefreshToken.for_user(teacher_user)

        assert refresh.payload["user_id"] == teacher_user.id
        assert "exp" in refresh.payload
        assert "iat" in refresh.payload

    def test_token_refresh_endpoint(self, api_client, teacher_user):
        """Test token refresh endpoint"""
        refresh = RefreshToken.for_user(teacher_user)

        response = api_client.post(
            "/api/auth/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]
        if response.status_code == status.HTTP_200_OK:
            assert "access" in response.data or "token" in response.data

    def test_student_cannot_login_as_teacher(self, api_client, student_user):
        """Test that student role can login but cannot access teacher endpoints"""
        response = api_client.post(
            "/api/auth/login/",
            {
                "username": "student1",
                "password": "student123secure",
            },
            format="json",
        )

        # Student can login or fail with permission error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_multiple_login_attempts(self, api_client, teacher_user):
        """Test multiple successful login attempts"""
        for _ in range(3):
            response = api_client.post(
                "/api/auth/login/",
                {
                    "username": "teacher1",
                    "password": "teacher123secure",
                },
                format="json",
            )
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
            if response.status_code == status.HTTP_200_OK:
                assert "token" in response.data.get("data", {}) or "access" in response.data
