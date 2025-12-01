"""
Tests for reactivate_user endpoint (POST /api/auth/users/{id}/reactivate/)

Acceptance Criteria:
- POST /api/auth/users/{id}/reactivate/ endpoint exists
- Only works on deactivated users (is_active=False)
- Only admin/staff can reactivate
- Audit logged
- Clear error messages
- HTTP 200 on success, 400/404 on error
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestReactivateUser:
    """Test suite for reactivate_user endpoint"""

    @pytest.fixture
    def admin_user(self):
        """Create admin user for testing"""
        return User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='admin123',
            role=User.Role.STUDENT,
            is_staff=True,
            is_active=True
        )

    @pytest.fixture
    def deactivated_student(self):
        """Create deactivated student for testing"""
        return User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='student123',
            role=User.Role.STUDENT,
            is_active=False
        )

    @pytest.fixture
    def active_student(self):
        """Create active student for testing"""
        return User.objects.create_user(
            username='active@test.com',
            email='active@test.com',
            password='student123',
            role=User.Role.STUDENT,
            is_active=True
        )

    @pytest.fixture
    def api_client(self, admin_user):
        """Create authenticated API client"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        return client

    def test_reactivate_deactivated_user_success(self, api_client, deactivated_student):
        """Test 1: Reactivate deactivated student - should succeed"""
        url = f'/api/auth/users/{deactivated_student.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'reactivated' in response.data['message'].lower()

        # Verify user is now active
        deactivated_student.refresh_from_db()
        assert deactivated_student.is_active is True

    def test_reactivate_already_active_user(self, api_client, active_student):
        """Test 2: Reactivate already active user - should fail with 400"""
        url = f'/api/auth/users/{active_student.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already active' in response.data['detail'].lower()

    def test_reactivate_nonexistent_user(self, api_client):
        """Test 3: Reactivate non-existent user - should fail with 404"""
        url = '/api/auth/users/999999/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.data['detail'].lower()

    def test_reactivate_without_auth(self, deactivated_student):
        """Test 4: Non-admin cannot reactivate - should fail with 403"""
        client = APIClient()
        # Create regular student (not admin)
        regular_student = User.objects.create_user(
            username='regular@test.com',
            email='regular@test.com',
            password='student123',
            role=User.Role.STUDENT,
            is_active=True,
            is_staff=False
        )
        client.force_authenticate(user=regular_student)

        url = f'/api/auth/users/{deactivated_student.id}/reactivate/'
        response = client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reactivate_parent_updates_status(self, api_client):
        """Test 5: Reactivate parent - should update user status"""
        # Create deactivated parent
        parent = User.objects.create_user(
            username='parent@test.com',
            email='parent@test.com',
            password='parent123',
            role=User.Role.PARENT,
            is_active=False
        )

        url = f'/api/auth/users/{parent.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        parent.refresh_from_db()
        assert parent.is_active is True

    def test_reactivate_verifies_user_reactivated(self, api_client, deactivated_student):
        """Test 6: Verify user is actually reactivated after API call"""
        # Verify user starts as inactive
        assert deactivated_student.is_active is False

        url = f'/api/auth/users/{deactivated_student.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify user is now active in database
        deactivated_student.refresh_from_db()
        assert deactivated_student.is_active is True

        # Verify can't reactivate again (already active)
        response2 = api_client.post(url)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_reactivate_response_format(self, api_client, deactivated_student):
        """Test 7: Response format is correct"""
        url = f'/api/auth/users/{deactivated_student.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'success' in response.data
        assert 'message' in response.data
        assert response.data['success'] is True
        assert isinstance(response.data['message'], str)

    def test_reactivate_teacher(self, api_client):
        """Test 8: Reactivate teacher - should work"""
        teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='teacher123',
            role=User.Role.TEACHER,
            is_active=False
        )

        url = f'/api/auth/users/{teacher.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        teacher.refresh_from_db()
        assert teacher.is_active is True

    def test_reactivate_tutor(self, api_client):
        """Test 9: Reactivate tutor - should work"""
        tutor = User.objects.create_user(
            username='tutor@test.com',
            email='tutor@test.com',
            password='tutor123',
            role=User.Role.TUTOR,
            is_active=False
        )

        url = f'/api/auth/users/{tutor.id}/reactivate/'
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        tutor.refresh_from_db()
        assert tutor.is_active is True
