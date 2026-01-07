import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestGetParentChildrenAPI:

    def setup_method(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        self.child1 = User.objects.create_user(
            username='child1',
            email='child1@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.child2 = User.objects.create_user(
            username='child2',
            email='child2@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

    def test_get_children_returns_200_with_auth(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/parent/children/')
        assert response.status_code == 200

    def test_get_children_requires_auth(self):
        response = self.client.get('/api/parent/children/')
        assert response.status_code == 401

    def test_get_children_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/parent/children/')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and 'results' in data)

    def test_get_children_pagination_support(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/parent/children/?page=1&page_size=10')
        assert response.status_code == 200

    def test_get_children_filter_by_status(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/parent/children/?status=active')
        assert response.status_code == 200

    def test_get_children_non_parent_returns_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get('/api/parent/children/')
        assert response.status_code == 403

    def test_get_children_returns_json(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/parent/children/')
        assert response.status_code == 200
        assert 'application/json' in response['Content-Type']
