import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestGetChildSubjectsAPI:

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
        self.other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )

    def test_get_child_subjects_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/subjects/')
        assert response.status_code == 200

    def test_get_child_subjects_requires_auth(self):
        response = self.client.get(f'/api/children/{self.child.id}/subjects/')
        assert response.status_code == 401

    def test_get_child_subjects_non_parent_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.get(f'/api/children/{self.child.id}/subjects/')
        assert response.status_code == 403

    def test_get_child_subjects_other_parent_403(self):
        self.client.force_authenticate(user=self.other_parent)
        response = self.client.get(f'/api/children/{self.child.id}/subjects/')
        assert response.status_code == 403

    def test_get_child_subjects_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/subjects/')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and 'results' in data)

    def test_get_child_subjects_invalid_id_returns_404(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/children/99999/subjects/')
        assert response.status_code == 404

    def test_get_child_subjects_response_structure(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/children/{self.child.id}/subjects/')
        assert response.status_code == 200
        assert 'application/json' in response['Content-Type']
