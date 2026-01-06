"""
Security tests for parent-child access control in materials app.

Tests verify that:
- Parents can only access their own children
- Parents cannot access other parents' children
- Payment endpoints enforce child ownership
- Subject endpoints enforce child ownership
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
def parent1(db):
    """Create first parent with associated profile"""
    user = ParentFactory(username="parent1", email="parent1@example.com")
    from accounts.models import ParentProfile

    ParentProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def parent2(db):
    """Create second parent with associated profile"""
    user = ParentFactory(username="parent2", email="parent2@example.com")
    from accounts.models import ParentProfile

    ParentProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def student1(db, parent1):
    """Create first student belonging to parent1"""
    student = StudentFactory(username="student1", email="student1@example.com")
    from accounts.models import StudentProfile

    profile = StudentProfile.objects.get_or_create(user=student)[0]
    profile.parent = parent1
    profile.save()
    return student


@pytest.fixture
def student2(db, parent2):
    """Create second student belonging to parent2"""
    student = StudentFactory(username="student2", email="student2@example.com")
    from accounts.models import StudentProfile

    profile = StudentProfile.objects.get_or_create(user=student)[0]
    profile.parent = parent2
    profile.save()
    return student


@pytest.fixture
def subject(db):
    """Create a test subject"""
    return SubjectFactory(name="Mathematics")


@pytest.fixture
def teacher(db):
    """Create a test teacher"""
    return StudentFactory(username="teacher1", email="teacher1@example.com")


@pytest.fixture
def enrollment1(db, student1, subject, teacher):
    """Create enrollment for student1"""
    return SubjectEnrollmentFactory(
        student=student1, subject=subject, teacher=teacher, is_active=True
    )


@pytest.fixture
def enrollment2(db, student2, subject, teacher):
    """Create enrollment for student2"""
    return SubjectEnrollmentFactory(
        student=student2, subject=subject, teacher=teacher, is_active=True
    )


class TestChildAccessSecurity:
    """Test parent access control for children endpoints"""

    def test_parent1_can_see_own_child(self, api_client, parent1, student1):
        """Parent1 should see their own child"""
        token = Token.objects.create(user=parent1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = f"/api/materials/parent/children/{student1.id}/subjects/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_parent1_cannot_see_parent2_child(self, api_client, parent1, student2):
        """Parent1 should NOT see child of parent2 (403)"""
        token = Token.objects.create(user=parent1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = f"/api/materials/parent/children/{student2.id}/subjects/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_parent2_cannot_see_parent1_child(self, api_client, parent2, student1):
        """Parent2 should NOT see child of parent1 (403)"""
        token = Token.objects.create(user=parent2)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = f"/api/materials/parent/children/{student1.id}/subjects/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_parent1_cannot_initiate_payment_for_parent2_child(
        self, api_client, parent1, student2, enrollment2
    ):
        """Parent1 should NOT be able to initiate payment for parent2's child (403)"""
        token = Token.objects.create(user=parent1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = (
            f"/api/materials/parent/children/{student2.id}/"
            f"payment/{enrollment2.id}/"
        )
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_parent2_cannot_initiate_payment_for_parent1_child(
        self, api_client, parent2, student1, enrollment1
    ):
        """Parent2 should NOT be able to initiate payment for parent1's child (403)"""
        token = Token.objects.create(user=parent2)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = (
            f"/api/materials/parent/children/{student1.id}/"
            f"payment/{enrollment1.id}/"
        )
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_parent1_can_initiate_payment_for_own_child(
        self, api_client, parent1, student1, enrollment1
    ):
        """Parent1 should be able to initiate payment for own child"""
        token = Token.objects.create(user=parent1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = (
            f"/api/materials/parent/children/{student1.id}/"
            f"payment/{enrollment1.id}/"
        )
        data = {"amount": "100.00"}
        response = api_client.post(url, data, format="json")

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

    def test_unauthenticated_cannot_access_child(self, api_client, student1):
        """Unauthenticated user should not access child endpoints"""
        url = f"/api/materials/parent/children/{student1.id}/subjects/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_child_id_returns_404_or_403(self, api_client, parent1):
        """Accessing non-existent child returns 404, not exposing parent info"""
        token = Token.objects.create(user=parent1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        # Use a non-existent child ID
        url = f"/api/materials/parent/children/9999999/subjects/"
        response = api_client.get(url)

        # Should be either 404 (child not found) or 403 (forbidden)
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_parent_cannot_see_other_parent_subject_list(
        self, api_client, parent1, parent2, student1, student2
    ):
        """Parent1 should NOT see subject list of parent2's child"""
        token = Token.objects.create(user=parent1)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        url = f"/api/materials/parent/children/{student2.id}/subjects/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Ensure no data is leaked in response
        if response.data:
            assert "subjects" not in response.data or response.data["subjects"] == []
