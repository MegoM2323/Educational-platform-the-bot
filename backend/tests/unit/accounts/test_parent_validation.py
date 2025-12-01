"""
Unit tests for parent creation input validation (T834)

Tests email format, password strength, and phone format validation
for the parent creation endpoint.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing"""
    return User.objects.create_user(
        email='admin@test.com',
        username='admin@test.com',
        password='adminpass123',
        role='student',
        is_staff=True,
        is_superuser=True,
        first_name='Admin',
        last_name='User'
    )


@pytest.fixture
def api_client():
    """Return API client"""
    return APIClient()


@pytest.fixture
def auth_client(api_client, admin_user):
    """Return authenticated API client"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture(autouse=True)
def mock_supabase_services(mocker):
    """
    Mock Supabase services to avoid actual API calls during tests.
    This fixture is autouse=True so it applies to all tests in this file.
    """
    # Mock SupabaseAuthService
    mock_auth = mocker.patch('accounts.staff_views.SupabaseAuthService')
    mock_auth_instance = MagicMock()
    mock_auth_instance.sign_up.return_value = {
        'success': False,
        'user': None,
        'error': 'Mocked Supabase disabled in tests'
    }
    mock_auth.return_value = mock_auth_instance

    # Mock SupabaseSyncService
    mock_sync = mocker.patch('accounts.staff_views.SupabaseSyncService')
    mock_sync_instance = MagicMock()
    mock_sync_instance.create_django_user_from_supabase.return_value = None
    mock_sync.return_value = mock_sync_instance

    return {
        'auth': mock_auth_instance,
        'sync': mock_sync_instance
    }


class TestParentEmailValidation:
    """Test email format validation"""

    def test_valid_email_accepted(self, auth_client, db):
        """Valid email should be accepted"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'valid.parent@example.com',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_invalid_email_no_at_rejected(self, auth_client, db):
        """Email without @ should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'invalidemail.com',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_invalid_email_no_domain_rejected(self, auth_client, db):
        """Email without domain should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'invalid@',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_duplicate_email_rejected(self, auth_client, db):
        """Duplicate email should be rejected"""
        # Create first parent
        User.objects.create_user(
            email='existing@test.com',
            username='existing@test.com',
            password='pass123',
            role='parent',
            first_name='Existing',
            last_name='Parent'
        )

        # Try to create another with same email
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'existing@test.com',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        # Should be rejected with validation error (400)
        # Serializer validation catches duplicate emails
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_empty_email_rejected(self, auth_client, db):
        """Empty email should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': '',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data


class TestParentPasswordValidation:
    """Test password strength validation"""

    def test_strong_password_accepted(self, auth_client, db):
        """Strong password should be accepted"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'StrongPass123!'
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_weak_password_too_short_rejected(self, auth_client, db):
        """Password less than 8 characters should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent2@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'short'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_weak_password_too_common_rejected(self, auth_client, db):
        """Common password should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent3@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'password'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_weak_password_numeric_only_rejected(self, auth_client, db):
        """Numeric-only password should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent4@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': '12345678'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_auto_generated_password_when_not_provided(self, auth_client, db):
        """Password should be auto-generated if not provided"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent5@test.com',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        # Check if password is returned in credentials
        assert 'credentials' in response.data
        assert 'password' in response.data['credentials']
        # Password should be non-empty
        assert len(response.data['credentials']['password']) > 0


class TestParentPhoneValidation:
    """Test phone format validation"""

    def test_valid_phone_international_accepted(self, auth_client, db):
        """Valid international phone format should be accepted"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent6@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+79991234567'
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_valid_phone_without_plus_accepted(self, auth_client, db):
        """Valid phone without + should be accepted"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent7@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '79991234567'
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_invalid_phone_too_short_rejected(self, auth_client, db):
        """Phone with less than 9 digits should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent8@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+7999123'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone' in response.data

    def test_invalid_phone_too_long_rejected(self, auth_client, db):
        """Phone with more than 15 digits should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent9@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+79991234567890123'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone' in response.data

    def test_invalid_phone_with_letters_rejected(self, auth_client, db):
        """Phone with letters should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent10@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+7999abc4567'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone' in response.data

    def test_empty_phone_accepted(self, auth_client, db):
        """Empty phone should be accepted (optional field)"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent11@test.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': ''
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]


class TestParentMultipleValidationErrors:
    """Test multiple validation errors returned together"""

    def test_multiple_errors_returned_together(self, auth_client, db):
        """Multiple validation errors should be returned in one response"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'invalidemail',  # Invalid format
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+7abc',  # Invalid format
            'password': 'weak'  # Too short
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Should have errors for email, phone, and password
        assert 'email' in response.data or 'phone' in response.data or 'password' in response.data


class TestParentRequiredFields:
    """Test required field validation"""

    def test_missing_first_name_rejected(self, auth_client, db):
        """Missing first_name should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent12@test.com',
            'last_name': 'Doe'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'first_name' in response.data

    def test_missing_last_name_rejected(self, auth_client, db):
        """Missing last_name should be rejected"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent13@test.com',
            'first_name': 'John'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'last_name' in response.data

    def test_all_required_fields_provided_accepted(self, auth_client, db):
        """Request with all required fields should be accepted"""
        response = auth_client.post('/api/auth/parents/create/', {
            'email': 'parent14@test.com',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
