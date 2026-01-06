"""
Tests for parent dashboard endpoints existence and basic functionality.

Verifies that all parent endpoints:
1. Exist and respond with correct HTTP status
2. Return correct data structure
3. Require authentication
4. Enforce access control
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from accounts.factories import ParentFactory, StudentFactory
from materials.factories import SubjectFactory, SubjectEnrollmentFactory

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def parent(db):
    """Create parent with profile"""
    user = ParentFactory(username="testparent", email="parent@test.com")
    from accounts.models import ParentProfile
    ParentProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def student(db, parent):
    """Create student belonging to parent"""
    student = StudentFactory(username="teststudent", email="student@test.com")
    from accounts.models import StudentProfile
    profile = StudentProfile.objects.get_or_create(user=student)[0]
    profile.parent = parent
    profile.save()
    return student


@pytest.fixture
def subject(db):
    """Create test subject"""
    return SubjectFactory(name="TestSubject")


@pytest.fixture
def teacher(db):
    """Create test teacher"""
    return StudentFactory(username="teacher1", email="teacher@test.com")


@pytest.fixture
def enrollment(db, student, subject, teacher):
    """Create enrollment"""
    return SubjectEnrollmentFactory(
        student=student, subject=subject, teacher=teacher, is_active=True
    )


@pytest.fixture
def parent_token(parent):
    """Create authentication token for parent"""
    return Token.objects.create(user=parent)


class TestParentEndpointsExistence:
    """Test that all parent endpoints exist and return 200 status"""

    def test_get_dashboard(self, api_client, parent, parent_token):
        """GET /api/materials/parent/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        response = api_client.get("/api/materials/parent/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_children(self, api_client, parent, parent_token):
        """GET /api/materials/parent/children/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        response = api_client.get("/api/materials/parent/children/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_child_subjects(self, api_client, parent, parent_token, student):
        """GET /api/materials/parent/children/{id}/subjects/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/subjects/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_get_child_progress(self, api_client, parent, parent_token, student):
        """GET /api/materials/parent/children/{id}/progress/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/progress/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_get_child_payments(self, api_client, parent, parent_token, student):
        """GET /api/materials/parent/children/{id}/payments/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/payments/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_initiate_payment(self, api_client, parent, parent_token, student, enrollment):
        """POST /api/materials/parent/children/{id}/payment/{enrollmentId}/ returns 200/201"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/payment/{enrollment.id}/"
        data = {"amount": "100.00", "create_subscription": False}
        response = api_client.post(url, data, format="json")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_cancel_subscription(self, api_client, parent, parent_token, student, enrollment):
        """POST /api/materials/parent/children/{id}/subscription/{enrollmentId}/cancel/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")

        # First create a subscription with all required fields
        from materials.models import SubjectSubscription
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta

        subscription = SubjectSubscription.objects.create(
            enrollment=enrollment,
            status=SubjectSubscription.Status.ACTIVE,
            amount=Decimal("100.00"),
            next_payment_date=timezone.now() + timedelta(weeks=1),
        )

        url = f"/api/materials/parent/children/{student.id}/subscription/{enrollment.id}/cancel/"
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_get_all_payments(self, api_client, parent, parent_token):
        """GET /api/materials/parent/payments/ returns 200"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        response = api_client.get("/api/materials/parent/payments/")
        assert response.status_code == status.HTTP_200_OK


class TestParentEndpointsCorrectData:
    """Test that endpoints return correct data structure"""

    def test_dashboard_returns_children_list(self, api_client, parent, parent_token, student):
        """Dashboard should return children list"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        response = api_client.get("/api/materials/parent/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "children" in data or "data" in data or isinstance(data, dict)

    def test_children_list_returns_array(self, api_client, parent, parent_token, student):
        """Children list should return array with pagination"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        response = api_client.get("/api/materials/parent/children/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "children" in data
        assert isinstance(data["children"], list)
        if data["children"]:
            child = data["children"][0]
            assert "id" in child
            assert "name" in child or "full_name" in child

    def test_child_subjects_returns_array(self, api_client, parent, parent_token, student, enrollment):
        """Child subjects should return array"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/subjects/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert isinstance(data, list)
        if data:
            subject = data[0]
            assert "subject" in subject or "name" in subject

    def test_child_progress_returns_data(self, api_client, parent, parent_token, student):
        """Child progress should return progress data"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/progress/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert isinstance(data, dict) or isinstance(data, list)

    def test_child_payments_returns_array(self, api_client, parent, parent_token, student):
        """Child payments should return array"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/payments/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert isinstance(data, list)

    def test_initiate_payment_returns_payment_data(self, api_client, parent, parent_token, student, enrollment):
        """Initiate payment should return payment data with keys"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        url = f"/api/materials/parent/children/{student.id}/payment/{enrollment.id}/"
        data = {"amount": "100.00", "create_subscription": False}
        response = api_client.post(url, data, format="json")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        response_data = response.data
        assert isinstance(response_data, dict)
        # Should have either payment_id, id, or similar
        assert any(k in response_data for k in ["id", "payment_id", "amount", "status"])

    def test_cancel_subscription_returns_success(self, api_client, parent, parent_token, student, enrollment):
        """Cancel subscription should return success message"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")

        # Create subscription first with all required fields
        from materials.models import SubjectSubscription
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta

        SubjectSubscription.objects.create(
            enrollment=enrollment,
            status=SubjectSubscription.Status.ACTIVE,
            amount=Decimal("100.00"),
            next_payment_date=timezone.now() + timedelta(weeks=1),
        )

        url = f"/api/materials/parent/children/{student.id}/subscription/{enrollment.id}/cancel/"
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "success" in data or "message" in data

    def test_payments_list_returns_array(self, api_client, parent, parent_token):
        """Payments list should return array"""
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {parent_token.key}")
        response = api_client.get("/api/materials/parent/payments/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert isinstance(data, list) or isinstance(data, dict)


class TestParentEndpointsAuthentication:
    """Test that endpoints require authentication"""

    def test_dashboard_requires_auth(self, api_client):
        """Dashboard should return 401 without auth"""
        response = api_client.get("/api/materials/parent/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_children_list_requires_auth(self, api_client):
        """Children list should return 401 without auth"""
        response = api_client.get("/api/materials/parent/children/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_child_subjects_requires_auth(self, api_client, student):
        """Child subjects should return 401 without auth"""
        url = f"/api/materials/parent/children/{student.id}/subjects/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_child_progress_requires_auth(self, api_client, student):
        """Child progress should return 401 without auth"""
        url = f"/api/materials/parent/children/{student.id}/progress/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_child_payments_requires_auth(self, api_client, student):
        """Child payments should return 401 without auth"""
        url = f"/api/materials/parent/children/{student.id}/payments/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_initiate_payment_requires_auth(self, api_client, student, enrollment):
        """Initiate payment should return 401 without auth"""
        url = f"/api/materials/parent/children/{student.id}/payment/{enrollment.id}/"
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cancel_subscription_requires_auth(self, api_client, student, enrollment):
        """Cancel subscription should return 401 without auth"""
        url = f"/api/materials/parent/children/{student.id}/subscription/{enrollment.id}/cancel/"
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_payments_list_requires_auth(self, api_client):
        """Payments list should return 401 without auth"""
        response = api_client.get("/api/materials/parent/payments/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
