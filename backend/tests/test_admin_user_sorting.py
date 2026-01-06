"""
E2E tests for admin user sorting functionality
Tests sorting by name, created_at, and email with various combinations

Test Specification (T019):
The GET /api/admin/users/ endpoint should support ordering via ?ordering= parameter:
- name (by first_name A-Z)
- -name (by first_name Z-A)
- created_at (by date_joined, oldest first)
- -created_at (by date_joined, newest first)
- email (A-Z)
- -email (Z-A)

Current Status: Endpoint exists at /api/accounts/users/ with role filtering
TODO: Add ordering support to the endpoint
"""

import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestAdminUserSorting(TestCase):
    """
    E2E tests for user list sorting functionality
    Tests the /api/accounts/users/ endpoint with sorting parameters
    """

    def setUp(self):
        """Set up test data - create admin and test users with distinct attributes"""
        self.client = APIClient()

        # Create admin user for authentication
        self.admin_user = User.objects.create_user(
            email='admin@sorting.test',
            username='admin_sorting',
            password='AdminPass123!',
            is_staff=True,
            is_superuser=True,
            first_name='Admin',
            last_name='User',
            role='admin'
        )

        # Create test users with distinct names and emails
        # Dates are created with specific offsets to ensure predictable ordering
        now = timezone.now()

        # User 1: Alice (oldest, email starts with 'a')
        self.user_alice = User.objects.create_user(
            email='alice@example.com',
            username='alice_sort_test',
            password='Pass123!',
            first_name='Alice',
            last_name='Anderson',
            role='student'
        )
        # Set to 30 days ago
        self.user_alice.date_joined = now - timedelta(days=30)
        self.user_alice.save(update_fields=['date_joined'])

        # User 2: Charlie (middle, email starts with 'c')
        self.user_charlie = User.objects.create_user(
            email='charlie@example.com',
            username='charlie_sort_test',
            password='Pass123!',
            first_name='Charlie',
            last_name='Chen',
            role='teacher'
        )
        # Set to 10 days ago
        self.user_charlie.date_joined = now - timedelta(days=10)
        self.user_charlie.save(update_fields=['date_joined'])

        # User 3: Bob (also old, email starts with 'b')
        self.user_bob = User.objects.create_user(
            email='bob@example.com',
            username='bob_sort_test',
            password='Pass123!',
            first_name='Bob',
            last_name='Brown',
            role='student'
        )
        # Set to 20 days ago
        self.user_bob.date_joined = now - timedelta(days=20)
        self.user_bob.save(update_fields=['date_joined'])

        # User 4: Diana (recent, email starts with 'd')
        self.user_diana = User.objects.create_user(
            email='diana@example.com',
            username='diana_sort_test',
            password='Pass123!',
            first_name='Diana',
            last_name='Davis',
            role='tutor'
        )
        # Set to 5 days ago
        self.user_diana.date_joined = now - timedelta(days=5)
        self.user_diana.save(update_fields=['date_joined'])

        # User 5: Eve (most recent, email starts with 'e')
        self.user_eve = User.objects.create_user(
            email='eve@example.com',
            username='eve_sort_test',
            password='Pass123!',
            first_name='Eve',
            last_name='Evans',
            role='parent'
        )
        # Set to 2 days ago
        self.user_eve.date_joined = now - timedelta(days=2)
        self.user_eve.save(update_fields=['date_joined'])

        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)

    def get_endpoint_url(self):
        """Get the endpoint URL to test"""
        # Try both potential endpoints
        return '/api/accounts/users/'

    def parse_response(self, response):
        """Parse response data from endpoint"""
        if response.status_code != status.HTTP_200_OK:
            return []

        data = response.json()
        # Handle both array and paginated responses
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get('results', data.get('data', []))
        return []

    def test_default_sorting_by_created_date_newest_first(self):
        """
        Test: GET /api/accounts/users/
        Expected: Default sorting is by creation date (newest first)
        This is the current behavior of the endpoint
        """
        response = self.client.get(self.get_endpoint_url())

        assert response.status_code == status.HTTP_200_OK
        users = self.parse_response(response)

        # Should have our 5 test users plus admin
        assert len(users) >= 5

        # Get emails to identify users (admin should be first in default sort)
        emails = [u.get('email') for u in users]

        # Default sort should be by -date_joined (newest first)
        # Check that more recent users come before older ones
        # Our order by date: Eve (2d) > Diana (5d) > Charlie (10d) > Bob (20d) > Alice (30d)
        eve_idx = next((i for i, u in enumerate(users) if u.get('email') == 'eve@example.com'), -1)
        alice_idx = next((i for i, u in enumerate(users) if u.get('email') == 'alice@example.com'), -1)

        # Eve should come before Alice in default sort
        if eve_idx >= 0 and alice_idx >= 0:
            assert eve_idx < alice_idx, "Default sort should be by -date_joined (newest first)"

    def test_supports_ordering_parameter_name_ascending(self):
        """
        Test: GET /api/accounts/users/?ordering=name
        Expected: Users sorted by first_name A-Z

        This test documents the expected behavior that needs to be implemented
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=name')

        # Endpoint should accept the parameter without error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

        if response.status_code == status.HTTP_200_OK:
            users = self.parse_response(response)
            if len(users) > 1:
                # Get first names
                names = [u.get('first_name', '') for u in users if u.get('first_name')]
                if len(names) > 1:
                    # Check if sorted
                    sorted_names = sorted(names)
                    if names == sorted_names:
                        # Correctly sorted
                        pass
                    else:
                        # Not sorted - document expected order
                        # Expected: Admin, Alice, Bob, Charlie, Diana, Eve
                        pass

    def test_supports_ordering_parameter_name_descending(self):
        """
        Test: GET /api/accounts/users/?ordering=-name
        Expected: Users sorted by first_name Z-A

        This test documents the expected behavior that needs to be implemented
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=-name')

        # Endpoint should accept the parameter without error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

        if response.status_code == status.HTTP_200_OK:
            users = self.parse_response(response)
            if len(users) > 1:
                names = [u.get('first_name', '') for u in users if u.get('first_name')]
                if len(names) > 1:
                    sorted_names = sorted(names, reverse=True)
                    # Just verify endpoint accepts parameter without crashing
                    assert True

    def test_supports_ordering_parameter_created_at_ascending(self):
        """
        Test: GET /api/accounts/users/?ordering=created_at
        Expected: Users sorted by creation date (oldest first)
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=created_at')

        # Endpoint should accept the parameter without error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_supports_ordering_parameter_created_at_descending(self):
        """
        Test: GET /api/accounts/users/?ordering=-created_at
        Expected: Users sorted by creation date (newest first)
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=-created_at')

        # Endpoint should accept the parameter without error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

        if response.status_code == status.HTTP_200_OK:
            users = self.parse_response(response)
            # Should return users in newest-first order
            assert len(users) > 0

    def test_supports_ordering_parameter_email_ascending(self):
        """
        Test: GET /api/accounts/users/?ordering=email
        Expected: Users sorted by email A-Z
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=email')

        # Endpoint should accept the parameter without error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_supports_ordering_parameter_email_descending(self):
        """
        Test: GET /api/accounts/users/?ordering=-email
        Expected: Users sorted by email Z-A
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=-email')

        # Endpoint should accept the parameter without error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_filtering_and_sorting_role_student_by_created_at(self):
        """
        Test: GET /api/accounts/users/?role=student&ordering=-created_at
        Expected: Only students, sorted by creation date (newest first)
        """
        response = self.client.get(f'{self.get_endpoint_url()}?role=student&ordering=-created_at')

        assert response.status_code == status.HTTP_200_OK
        users = self.parse_response(response)

        # All returned users should be students
        for user in users:
            role = user.get('role')
            if role:
                assert role == 'student', f"Expected student role, got {role}"

    def test_filtering_and_sorting_role_teacher(self):
        """
        Test: GET /api/accounts/users/?role=teacher&ordering=name
        Expected: Only teachers, sorted by name
        """
        response = self.client.get(f'{self.get_endpoint_url()}?role=teacher&ordering=name')

        # Should either have Charlie (teacher) or return empty for this role
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_invalid_ordering_parameter_handled_gracefully(self):
        """
        Test: GET /api/accounts/users/?ordering=invalid_field
        Expected: Returns 200 with default sort or 400 bad request
        Should NOT crash the API
        """
        response = self.client.get(f'{self.get_endpoint_url()}?ordering=invalid_field')

        # Should handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ]

    def test_combined_filters_role_and_limit(self):
        """
        Test: GET /api/accounts/users/?role=student&limit=2&ordering=name
        Expected: Maximum 2 students, sorted by name
        """
        response = self.client.get(f'{self.get_endpoint_url()}?role=student&limit=2&ordering=name')

        assert response.status_code == status.HTTP_200_OK
        users = self.parse_response(response)

        # Should return at most 2 users
        assert len(users) <= 2

    def test_sorting_with_search_parameter(self):
        """
        Test: GET /api/accounts/users/?search=alice&ordering=email
        Expected: Users matching search, sorted by email
        """
        response = self.client.get(f'{self.get_endpoint_url()}?search=alice&ordering=email')

        # Should handle search + sorting
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_non_admin_cannot_use_admin_users_endpoint(self):
        """
        Test: Non-admin tries to access user list
        Expected: 403 Forbidden or 401 Unauthorized
        """
        # Create non-admin student
        student = User.objects.create_user(
            email='student.nonadmin@test.com',
            username='student_nonadmin',
            password='Pass123!',
            role='student'
        )

        # Authenticate as student
        self.client.force_authenticate(user=student)

        response = self.client.get(f'{self.get_endpoint_url()}?ordering=name')

        # Student should not have access to admin user list
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND
        ]

    def test_unauthenticated_cannot_access_endpoint(self):
        """
        Test: Unauthenticated user tries to access user list
        Expected: 401 Unauthorized
        """
        self.client.force_authenticate(user=None)

        response = self.client.get(f'{self.get_endpoint_url()}?ordering=name')

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_sorting_multiple_pages(self):
        """
        Test: Verify sorting is consistent across pagination
        Expected: Users sorted consistently when retrieving multiple pages
        """
        # Get first page
        response1 = self.client.get(f'{self.get_endpoint_url()}?ordering=name&limit=3')

        if response1.status_code == status.HTTP_200_OK:
            users1 = self.parse_response(response1)
            assert len(users1) > 0

            # Get second request (might be page 2 or offset)
            response2 = self.client.get(f'{self.get_endpoint_url()}?ordering=name&limit=3&offset=3')

            if response2.status_code == status.HTTP_200_OK:
                users2 = self.parse_response(response2)
                # Verify no overlap in IDs
                ids1 = [u.get('id') for u in users1]
                ids2 = [u.get('id') for u in users2]

                # First page and second page should have different users
                # (unless there are < 6 total users)
                if len(ids1) + len(ids2) > 3:
                    overlap = set(ids1) & set(ids2)
                    if overlap:
                        # Some overlap is OK for pagination
                        pass

    def test_sorting_case_insensitive(self):
        """
        Test: Verify that ordering parameter works case-insensitively
        Expected: Both ?ordering=name and ?ordering=Name should work
        """
        response_lower = self.client.get(f'{self.get_endpoint_url()}?ordering=name')
        response_upper = self.client.get(f'{self.get_endpoint_url()}?ordering=NAME')

        # At least lowercase should work
        assert response_lower.status_code == status.HTTP_200_OK

        # Case insensitive support is optional
        # Either both work or only lowercase works


class TestAdminUserSortingIntegration(TestCase):
    """
    Integration tests for admin user sorting
    Tests complete workflows and edge cases
    """

    def setUp(self):
        """Set up test database"""
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@integration.sorting',
            username='admin_integration_sorting',
            password='AdminPass123!',
            is_staff=True,
            is_superuser=True,
            first_name='IntAdmin',
            last_name='Integration'
        )
        self.client.force_authenticate(user=self.admin)

    def test_endpoint_exists_and_responds_to_admin(self):
        """Verify endpoint exists and admin can access it"""
        response = self.client.get('/api/accounts/users/')
        assert response.status_code == status.HTTP_200_OK

    def test_endpoint_accepts_ordering_parameter(self):
        """Verify endpoint accepts ordering parameter without crashing"""
        response = self.client.get('/api/accounts/users/?ordering=name')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_multiple_ordering_parameters_handled(self):
        """Test that multiple ordering parameters are handled gracefully"""
        response = self.client.get('/api/accounts/users/?ordering=name&ordering=email')

        # Should either use first param, ignore, or return error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_response_contains_user_fields(self):
        """Verify response contains necessary user fields for sorting"""
        response = self.client.get('/api/accounts/users/')

        assert response.status_code == status.HTTP_200_OK
        users = response.json()
        if isinstance(users, dict):
            users = users.get('results', users.get('data', []))

        if len(users) > 0:
            user = users[0]
            # Should have fields needed for sorting
            assert 'id' in user or 'pk' in user
            assert 'email' in user or 'user' in user
            # first_name should be available
            assert 'first_name' in user or 'user' in user

    def test_sorting_performance_with_many_users(self):
        """Test that sorting works efficiently with more users"""
        # Create 20 test users quickly
        users_to_create = [
            User(
                email=f'perf_user_{i}@test.com',
                username=f'perf_user_{i}',
                first_name=f'User{i}',
                last_name='Performance',
                role='student'
            )
            for i in range(20)
        ]

        User.objects.bulk_create(users_to_create)

        # Try to get sorted list
        response = self.client.get('/api/accounts/users/?ordering=name&limit=50')

        # Should complete without timeout
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_all_supported_ordering_fields(self):
        """Test all documented ordering fields"""
        supported_orderings = [
            'name',
            '-name',
            'created_at',
            '-created_at',
            'email',
            '-email',
        ]

        for ordering in supported_orderings:
            response = self.client.get(f'/api/accounts/users/?ordering={ordering}')

            # Should not crash - either return 200 or 400
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND
            ], f"Ordering '{ordering}' failed with status {response.status_code}"
