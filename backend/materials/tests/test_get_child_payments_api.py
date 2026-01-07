import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
class TestGetChildPaymentsAPI:

    def setup_method(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        self.child = User.objects.create_user(
            username='child1',
            email='child1@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

    def test_get_child_payments_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/payments/')
        assert response.status_code == 200

    def test_get_child_payments_requires_auth(self):
        response = self.client.get(f'/api/children/{self.child.id}/payments/')
        assert response.status_code == 401

    def test_get_child_payments_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/payments/')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and 'results' in data)

    def test_get_child_payments_sorting_by_date(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/payments/?sort=-date')
        assert response.status_code == 200

    def test_get_child_payments_filter_by_status(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/payments/?status=completed')
        assert response.status_code == 200

    def test_get_child_payments_other_parent_403(self):
        other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        self.client.force_authenticate(user=other_parent)
        response = self.client.get(f'/api/children/{self.child.id}/payments/')
        assert response.status_code == 403

    def test_get_child_payments_invalid_child_returns_404(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/children/99999/payments/')
        assert response.status_code == 404
