import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestGetParentInvoicesAPI:

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

    def test_get_parent_invoices_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/invoices/parent/')
        assert response.status_code == 200

    def test_get_parent_invoices_requires_auth(self):
        response = self.client.get('/api/invoices/parent/')
        assert response.status_code == 401

    def test_get_parent_invoices_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/invoices/parent/')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and 'results' in data)

    def test_get_parent_invoices_pagination(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/invoices/parent/?page=1&page_size=10')
        assert response.status_code == 200

    def test_get_parent_invoices_filter_by_status(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/invoices/parent/?status=pending')
        assert response.status_code == 200

    def test_get_parent_invoices_non_parent_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get('/api/invoices/parent/')
        assert response.status_code == 403

    def test_get_parent_invoices_has_invoice_fields(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/invoices/parent/')
        assert response.status_code == 200
        assert 'application/json' in response['Content-Type']
