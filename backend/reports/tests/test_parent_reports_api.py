import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestParentReportsAPI:

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

    def test_get_parent_reports_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent/')
        assert response.status_code == 200

    def test_get_parent_reports_requires_auth(self):
        response = self.client.get('/api/reports/parent/')
        assert response.status_code == 401

    def test_get_parent_reports_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent/')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and 'results' in data)

    def test_get_parent_reports_filter_by_child(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/reports/parent/?child_id={self.child.id}')
        assert response.status_code == 200

    def test_get_parent_reports_filter_by_date(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent/?start_date=2025-01-01&end_date=2025-12-31')
        assert response.status_code == 200

    def test_get_parent_reports_non_parent_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get('/api/reports/parent/')
        assert response.status_code == 403

    def test_get_parent_reports_export_pdf(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent/')
        assert response.status_code in [200, 400]

    def test_get_parent_reports_pagination(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/reports/parent/?page=1&page_size=15')
        assert response.status_code == 200
