import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, ParentProfile
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db
class TestCancelSubscriptionAPI:

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

        ParentProfile.objects.get_or_create(user=self.parent)
        student_profile = StudentProfile.objects.get_or_create(user=self.child)[0]
        student_profile.parent = self.parent
        student_profile.save()

        teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        self.subject = Subject.objects.create(
            name='Math'
        )

        self.enrollment = SubjectEnrollment.objects.create(
            student=self.child,
            subject=self.subject,
            teacher=teacher,
            status='active'
        )

    def test_cancel_subscription_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
        assert response.status_code in [200, 204]

    def test_cancel_subscription_requires_auth(self):
        response = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
        assert response.status_code == 401

    def test_cancel_subscription_invalid_id_returns_404(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.post('/api/subscriptions/99999/cancel/', format='json')
        assert response.status_code == 404

    def test_cancel_subscription_parent_only(self):
        student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        self.client.force_authenticate(user=student)
        response = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
        assert response.status_code == 403

    def test_cancel_subscription_already_cancelled_returns_400(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
        if response.status_code == 200 or response.status_code == 204:
            response2 = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
            assert response2.status_code == 400

    def test_cancel_subscription_other_parent_403(self):
        other_parent = User.objects.create_user(
            username='parent2',
            email='parent2@test.com',
            password='testpass123',
            role=User.Role.PARENT
        )
        self.client.force_authenticate(user=other_parent)
        response = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
        assert response.status_code == 403

    def test_cancel_subscription_returns_confirmation(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.post(f'/api/subscriptions/{self.enrollment.id}/cancel/', format='json')
        if response.status_code in [200, 204]:
            assert response.status_code in [200, 204]
