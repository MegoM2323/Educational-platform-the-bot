import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestGetParentDashboardAPI:

    def setup_method(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        self.other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )

    def test_dashboard_returns_200_with_auth(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/dashboard/parent/')
        assert response.status_code == 200

    def test_dashboard_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/dashboard/parent/')
        assert response.status_code == 401

    def test_dashboard_response_has_required_fields(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/dashboard/parent/')
        assert response.status_code == 200
        data = response.json()

        assert 'children' in data
        assert 'payments_summary' in data
        assert 'upcoming_classes' in data
        assert isinstance(data['children'], list)

    def test_dashboard_only_shows_own_data(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/dashboard/parent/')
        assert response.status_code == 200
        data = response.json()

        for child in data.get('children', []):
            if 'parent_id' in child:
                assert child['parent_id'] == self.parent.id

    def test_dashboard_returns_json_content_type(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/dashboard/parent/')
        assert response.status_code == 200
        assert 'application/json' in response['Content-Type']

    def test_dashboard_non_parent_user_returns_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get('/api/dashboard/parent/')
        assert response.status_code == 403
