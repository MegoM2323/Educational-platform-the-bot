import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestGetChildProgressAPI:

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

    def test_get_child_progress_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/progress/')
        assert response.status_code == 200

    def test_get_child_progress_requires_auth(self):
        response = self.client.get(f'/api/children/{self.child.id}/progress/')
        assert response.status_code == 401

    def test_get_child_progress_parent_only(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get(f'/api/children/{self.child.id}/progress/')
        assert response.status_code == 403

    def test_get_child_progress_has_stats(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/progress/')
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            assert 'stats' in data or 'progress' in data or 'data' in data

    def test_get_child_progress_filter_by_subject(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/progress/?subject=math')
        assert response.status_code == 200

    def test_get_child_progress_filter_by_date_range(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(
            f'/api/children/{self.child.id}/progress/?start_date=2025-01-01&end_date=2025-12-31'
        )
        assert response.status_code == 200

    def test_get_child_progress_invalid_child_returns_404(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/children/99999/progress/')
        assert response.status_code == 404
