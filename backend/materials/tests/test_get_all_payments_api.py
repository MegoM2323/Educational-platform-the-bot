import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestGetAllPaymentsAPI:

    def setup_method(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )

    def test_get_all_payments_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/payments/all/')
        assert response.status_code == 200

    def test_get_all_payments_requires_auth(self):
        response = self.client.get('/api/payments/all/')
        assert response.status_code == 401

    def test_get_all_payments_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/payments/all/')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and 'results' in data)

    def test_get_all_payments_pagination(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/payments/all/?page=1&page_size=20')
        assert response.status_code == 200

    def test_get_all_payments_filter_by_status(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/payments/all/?status=completed')
        assert response.status_code == 200

    def test_get_all_payments_filter_by_date(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/payments/all/?start_date=2025-01-01&end_date=2025-12-31')
        assert response.status_code == 200

    def test_get_all_payments_sort_by_amount(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/payments/all/?sort=-amount')
        assert response.status_code == 200

    def test_get_all_payments_non_parent_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get('/api/payments/all/')
        assert response.status_code == 403
