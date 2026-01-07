import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestParentProfileAPI:

    def setup_method(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent@test.com',
            password='testpass123',
            role=User.Role.PARENT,
            first_name='John',
            last_name='Doe'
        )

    def test_get_parent_profile_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/accounts/profile/')
        assert response.status_code == 200

    def test_get_parent_profile_requires_auth(self):
        response = self.client.get('/api/accounts/profile/')
        assert response.status_code == 401

    def test_get_parent_profile_has_required_fields(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/accounts/profile/')
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert 'email' in data
        assert 'first_name' in data
        assert 'last_name' in data

    def test_patch_parent_profile_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'first_name': 'Jane',
            'last_name': 'Smith'
        }
        response = self.client.patch('/api/accounts/profile/', data=payload, format='json')
        assert response.status_code == 200

    def test_patch_parent_profile_requires_auth(self):
        payload = {
            'first_name': 'Jane'
        }
        response = self.client.patch('/api/accounts/profile/', data=payload, format='json')
        assert response.status_code == 401

    def test_patch_parent_profile_cannot_change_email(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'email': 'newemail@test.com'
        }
        response = self.client.patch('/api/accounts/profile/', data=payload, format='json')
        assert response.status_code == 400

    def test_patch_parent_profile_updates_data(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'first_name': 'Jane'
        }
        response = self.client.patch('/api/accounts/profile/', data=payload, format='json')
        assert response.status_code == 200
        data = response.json()
        assert data['first_name'] == 'Jane'

    def test_other_parent_cannot_view_profile(self):
        other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        self.client.force_authenticate(user=other_parent)
        response = self.client.get(f'/api/accounts/profile/{self.parent.id}/')
        assert response.status_code == 403
