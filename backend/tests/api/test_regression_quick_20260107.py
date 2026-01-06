"""
Quick regression test - проверка основных endpoints после fixes
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    user = User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='TestPass123!',
        role=User.Role.TEACHER
    )
    return user


class TestEndpointAccessibility:
    """Test if basic endpoints are accessible"""

    @pytest.mark.django_db
    def test_chat_endpoint_accessible(self, api_client, authenticated_user):
        """Check if /api/chat/rooms/ is accessible"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/chat/rooms/')
        # Should not be 404 or 405
        assert response.status_code != 404, f"404 Not Found for /api/chat/rooms/"
        assert response.status_code != 405, f"405 Method Not Allowed for /api/chat/rooms/"
        print(f"GET /api/chat/rooms/ → {response.status_code}")

    @pytest.mark.django_db
    def test_accounts_students_endpoint(self, api_client, authenticated_user):
        """Check if /api/accounts/students/ is accessible"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/accounts/students/')
        # Should not be 404 or 405
        assert response.status_code != 404, f"404 Not Found for /api/accounts/students/"
        assert response.status_code != 405, f"405 Method Not Allowed for /api/accounts/students/"
        print(f"GET /api/accounts/students/ → {response.status_code}")

    @pytest.mark.django_db
    def test_invoices_endpoint(self, api_client, authenticated_user):
        """Check if /api/invoices/ is accessible"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/invoices/')
        # Should not be 404 or 405
        assert response.status_code != 404, f"404 Not Found for /api/invoices/"
        assert response.status_code != 405, f"405 Method Not Allowed for /api/invoices/"
        print(f"GET /api/invoices/ → {response.status_code}")

    @pytest.mark.django_db
    def test_assignments_endpoint(self, api_client, authenticated_user):
        """Check if /api/assignments/ is accessible"""
        api_client.force_authenticate(user=authenticated_user)
        response = api_client.get('/api/assignments/')
        # Should not be 404 or 405
        assert response.status_code != 404, f"404 Not Found for /api/assignments/"
        assert response.status_code != 405, f"405 Method Not Allowed for /api/assignments/"
        print(f"GET /api/assignments/ → {response.status_code}")
