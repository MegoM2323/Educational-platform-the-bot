import pytest
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User


@pytest.mark.django_db
class TestUserDetailRouting:
    """Test API routing for user detail endpoints"""

    @pytest.fixture
    def admin_user(self):
        """Create admin user"""
        return User.objects.create_superuser(
            username='admin_routing_test',
            email='admin_routing@test.com',
            first_name='Admin',
            last_name='Test',
            password='testpass123'
        )

    @pytest.fixture
    def regular_user(self):
        """Create regular user"""
        return User.objects.create_user(
            username='user_routing_test',
            email='user_routing@test.com',
            first_name='Test',
            last_name='User',
            role='student',
            password='testpass123'
        )

    def test_get_user_detail_valid_id(self, admin_user, regular_user):
        """Test GET /api/accounts/users/{id}/ with valid ID should return 200"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        response = client.get(f'/api/accounts/users/{regular_user.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == regular_user.id
        assert response.data['email'] == regular_user.email

    def test_get_user_detail_invalid_id(self, admin_user):
        """Test GET /api/accounts/users/999999/ with invalid ID should return 404"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        response = client.get('/api/accounts/users/999999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'detail' in response.data

    def test_patch_user_detail_valid_id(self, admin_user, regular_user):
        """Test PATCH /api/accounts/users/{id}/ with valid ID should return 200"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        response = client.patch(
            f'/api/accounts/users/{regular_user.id}/',
            {'first_name': 'Updated'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK

    def test_delete_user_detail_valid_id(self, admin_user, regular_user):
        """Test DELETE /api/accounts/users/{id}/ with valid ID should return 204"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        response = client.delete(f'/api/accounts/users/{regular_user.id}/?soft=true')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_user_detail_invalid_id(self, admin_user):
        """Test DELETE /api/accounts/users/999999/ with invalid ID should return 404"""
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        response = client.delete('/api/accounts/users/999999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'detail' in response.data
