import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestInitiatePaymentAPI:

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

    def test_initiate_payment_returns_201(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'child_id': self.child.id,
            'amount': 5000,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 201

    def test_initiate_payment_requires_auth(self):
        payload = {
            'child_id': self.child.id,
            'amount': 5000,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 401

    def test_initiate_payment_requires_amount(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'child_id': self.child.id,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 400

    def test_initiate_payment_requires_child_id(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'amount': 5000,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 400

    def test_initiate_payment_invalid_amount_returns_400(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'child_id': self.child.id,
            'amount': -1000,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 400

    def test_initiate_payment_returns_payment_id(self):
        self.client.force_authenticate(user=self.parent)
        payload = {
            'child_id': self.child.id,
            'amount': 5000,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 201
        data = response.json()
        assert 'id' in data or 'payment_id' in data

    def test_initiate_payment_non_parent_403(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        payload = {
            'child_id': self.child.id,
            'amount': 5000,
            'description': 'Monthly subscription'
        }
        response = self.client.post('/api/payments/initiate/', data=payload, format='json')
        assert response.status_code == 403
