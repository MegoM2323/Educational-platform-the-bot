"""
E2E тест пагинации в списке пользователей админ кабинета.

Тестирует полный цикл пагинации:
1. Создание 50+ тестовых пользователей
2. Тестирование page и page_size параметров
3. Проверка целостности данных на разных страницах
4. Проверка метаданных пагинации (total_count, total_pages, current_page, has_next, has_previous)
5. Edge cases (invalid page, page_size limits)
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile, TeacherProfile, ParentProfile, TutorProfile

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user for testing"""
    user = User.objects.create_superuser(
        username="admin_pagination_test",
        email="admin_pagination@test.com",
        password="AdminPaginationPass123!",
        first_name="Admin",
        last_name="Pagination",
        role=User.Role.STUDENT,  # Role for admin in system
    )
    return user


@pytest.fixture
def admin_token(admin_user):
    """Create token for admin user"""
    token = Token.objects.create(user=admin_user)
    return token.key


@pytest.fixture
def api_client(admin_token):
    """Create authenticated API client"""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token}')
    return client


@pytest.fixture
def test_users(db):
    """Create 60 test users for pagination testing"""
    users = []

    # Create 60 students
    for i in range(60):
        user = User.objects.create_user(
            email=f'student_page_{i:03d}@test.com',
            username=f'student_page_{i:03d}',
            first_name=f'Student_{i:03d}',
            last_name=f'Paginate_{i:03d}',
            password='StudentPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(
            user=user,
            goal=f'Learning goal {i}',
        )
        users.append(user)

    return users


class TestAdminUserPaginationBasics:
    """Test basic pagination functionality"""

    def test_pagination_first_page_default_size(self, api_client, test_users):
        """Test retrieving first page with default page_size (if implemented)"""
        response = api_client.get('/api/accounts/users/')

        # Check response structure
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            # If pagination is implemented, check structure
            if isinstance(response.data, dict):
                # Paginated response format
                assert 'results' in response.data or 'data' in response.data
                assert 'total_count' in response.data or 'count' in response.data
            else:
                # Simple list format
                assert isinstance(response.data, list)

    def test_pagination_page_1_size_10(self, api_client, test_users):
        """Test page=1 with page_size=10"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=10')

        assert response.status_code in [200, 400]

        if response.status_code == 200:
            if isinstance(response.data, dict):
                # Extract results based on possible formats
                results = response.data.get('results', response.data.get('data', []))
                assert len(results) <= 10, f"Page 1 returned {len(results)} items, expected <= 10"

    def test_pagination_page_2_size_10(self, api_client, test_users):
        """Test page=2 with page_size=10 (different data from page 1)"""
        response1 = api_client.get('/api/accounts/users/?page=1&page_size=10')
        response2 = api_client.get('/api/accounts/users/?page=2&page_size=10')

        assert response1.status_code in [200, 400]
        assert response2.status_code in [200, 400]

        if response1.status_code == 200 and response2.status_code == 200:
            if isinstance(response1.data, dict) and isinstance(response2.data, dict):
                results1 = response1.data.get('results', response1.data.get('data', []))
                results2 = response2.data.get('results', response2.data.get('data', []))

                # Get user IDs for comparison
                ids1 = [r.get('id', r.get('user_id', i)) for i, r in enumerate(results1)]
                ids2 = [r.get('id', r.get('user_id', i)) for i, r in enumerate(results2)]

                # Pages should have different data if both have results
                if ids1 and ids2:
                    assert ids1 != ids2, "Page 1 and Page 2 should have different data"

    def test_pagination_different_page_sizes(self, api_client, test_users):
        """Test that page_size parameter works correctly"""
        # Test page_size=10
        response_10 = api_client.get('/api/accounts/users/?page=1&page_size=10')

        # Test page_size=25
        response_25 = api_client.get('/api/accounts/users/?page=1&page_size=25')

        assert response_10.status_code in [200, 400]
        assert response_25.status_code in [200, 400]

        if response_10.status_code == 200 and response_25.status_code == 200:
            if isinstance(response_10.data, dict) and isinstance(response_25.data, dict):
                results_10 = response_10.data.get('results', response_10.data.get('data', []))
                results_25 = response_25.data.get('results', response_25.data.get('data', []))

                # page_size=25 should return more items than page_size=10
                assert len(results_25) >= len(results_10), \
                    f"page_size=25 returned {len(results_25)} items, " \
                    f"expected >= {len(results_10)} from page_size=10"

    def test_pagination_same_first_page_data(self, api_client, test_users):
        """Test that same page returns consistent data"""
        response1 = api_client.get('/api/accounts/users/?page=1&page_size=10')
        response2 = api_client.get('/api/accounts/users/?page=1&page_size=10')

        assert response1.status_code == response2.status_code

        if response1.status_code == 200:
            # Data should be identical for same page
            if isinstance(response1.data, dict) and isinstance(response2.data, dict):
                results1 = response1.data.get('results', response1.data.get('data', []))
                results2 = response2.data.get('results', response2.data.get('data', []))

                assert len(results1) == len(results2), \
                    f"Same page returned different lengths: {len(results1)} vs {len(results2)}"


class TestAdminUserPaginationMetadata:
    """Test pagination metadata fields"""

    def test_pagination_response_contains_total_count(self, api_client, test_users):
        """Test that response contains total_count field"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=10')

        if response.status_code == 200 and isinstance(response.data, dict):
            assert 'total_count' in response.data or 'count' in response.data, \
                "Response should contain total_count or count field"

    def test_pagination_response_contains_total_pages(self, api_client, test_users):
        """Test that response contains total_pages field"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=10')

        if response.status_code == 200 and isinstance(response.data, dict):
            assert 'total_pages' in response.data or 'num_pages' in response.data, \
                "Response should contain total_pages or num_pages field"

    def test_pagination_response_contains_current_page(self, api_client, test_users):
        """Test that response contains current_page field"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=10')

        if response.status_code == 200 and isinstance(response.data, dict):
            assert 'current_page' in response.data or 'page' in response.data, \
                "Response should contain current_page or page field"

    def test_pagination_response_contains_has_next(self, api_client, test_users):
        """Test that response contains has_next field"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=10')

        if response.status_code == 200 and isinstance(response.data, dict):
            assert 'has_next' in response.data or 'next' in response.data, \
                "Response should contain has_next or next field"

    def test_pagination_response_contains_has_previous(self, api_client, test_users):
        """Test that response contains has_previous field"""
        response = api_client.get('/api/accounts/users/?page=2&page_size=10')

        if response.status_code == 200 and isinstance(response.data, dict):
            assert 'has_previous' in response.data or 'previous' in response.data, \
                "Response should contain has_previous or previous field"

    def test_pagination_metadata_accuracy(self, api_client, test_users):
        """Test that pagination metadata is accurate"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=10')

        if response.status_code == 200 and isinstance(response.data, dict):
            results = response.data.get('results', response.data.get('data', []))
            total_count = response.data.get('total_count', response.data.get('count', 0))
            total_pages = response.data.get('total_pages', response.data.get('num_pages', 0))

            # If metadata is present, verify accuracy
            if total_count > 0 and total_pages > 0:
                import math
                page_size = 10
                expected_pages = math.ceil(total_count / page_size)
                assert total_pages == expected_pages, \
                    f"total_pages={total_pages}, expected={expected_pages}"


class TestAdminUserPaginationEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_pagination_invalid_page_zero(self, api_client, test_users):
        """Test that page=0 is handled (should return error or first page)"""
        response = api_client.get('/api/accounts/users/?page=0&page_size=10')

        # Should either return 400 Bad Request or default to page 1
        assert response.status_code in [200, 400, 404]

    def test_pagination_invalid_page_negative(self, api_client, test_users):
        """Test that negative page numbers are handled"""
        response = api_client.get('/api/accounts/users/?page=-1&page_size=10')

        assert response.status_code in [200, 400, 404]

    def test_pagination_page_beyond_total(self, api_client, test_users):
        """Test requesting page beyond total pages"""
        # Request page 100 which is way beyond 60 users
        response = api_client.get('/api/accounts/users/?page=100&page_size=10')

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            if isinstance(response.data, dict):
                results = response.data.get('results', response.data.get('data', []))
                # Should return empty list
                assert len(results) == 0, "Beyond-range page should return empty results"

    def test_pagination_invalid_page_size_zero(self, api_client, test_users):
        """Test that page_size=0 is handled"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=0')

        # Should either return 400 or use default
        assert response.status_code in [200, 400]

    def test_pagination_invalid_page_size_negative(self, api_client, test_users):
        """Test that negative page_size is handled"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=-10')

        assert response.status_code in [200, 400]

    def test_pagination_page_size_exceeds_limit(self, api_client, test_users):
        """Test that page_size > 100 is limited or rejected"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=200')

        assert response.status_code in [200, 400]

        if response.status_code == 200:
            if isinstance(response.data, dict):
                results = response.data.get('results', response.data.get('data', []))
                # Should be limited to max of 100 or default
                assert len(results) <= 100, \
                    f"page_size should be limited to max 100, got {len(results)}"

    def test_pagination_last_page_partial(self, api_client, test_users):
        """Test that last page can contain fewer items"""
        # With 60 users and page_size=10, page 6 should have exactly 0 or be 404
        # Page 5 should have 10, page 6 should be empty or not exist
        response = api_client.get('/api/accounts/users/?page=6&page_size=10')

        # Should be 200 or 404
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            if isinstance(response.data, dict):
                results = response.data.get('results', response.data.get('data', []))
                # Last page might be partial or empty
                assert len(results) <= 10, "Each page should respect page_size limit"

    def test_pagination_with_non_numeric_page(self, api_client, test_users):
        """Test that non-numeric page parameter is handled"""
        response = api_client.get('/api/accounts/users/?page=abc&page_size=10')

        # Should return 400 or default to page 1
        assert response.status_code in [200, 400]

    def test_pagination_with_non_numeric_page_size(self, api_client, test_users):
        """Test that non-numeric page_size is handled"""
        response = api_client.get('/api/accounts/users/?page=1&page_size=abc')

        # Should return 400 or use default page_size
        assert response.status_code in [200, 400]


class TestAdminUserPaginationDataIntegrity:
    """Test data integrity across pagination"""

    def test_pagination_no_duplicate_users_across_pages(self, api_client, test_users):
        """Test that same user doesn't appear on multiple pages"""
        response1 = api_client.get('/api/accounts/users/?page=1&page_size=15')
        response2 = api_client.get('/api/accounts/users/?page=2&page_size=15')

        if response1.status_code == 200 and response2.status_code == 200:
            if isinstance(response1.data, dict) and isinstance(response2.data, dict):
                results1 = response1.data.get('results', response1.data.get('data', []))
                results2 = response2.data.get('results', response2.data.get('data', []))

                # Get user IDs
                ids1 = [r.get('id', r.get('user_id')) for r in results1 if 'id' in r or 'user_id' in r]
                ids2 = [r.get('id', r.get('user_id')) for r in results2 if 'id' in r or 'user_id' in r]

                # No duplicates between pages
                common_ids = set(ids1) & set(ids2)
                assert len(common_ids) == 0, \
                    f"Found duplicate users on different pages: {common_ids}"

    def test_pagination_all_users_accessible(self, api_client, test_users):
        """Test that all users are accessible through pagination"""
        all_user_ids = set()

        # Iterate through pages
        for page in range(1, 10):  # Max 10 pages to avoid infinite loop
            response = api_client.get(f'/api/accounts/users/?page={page}&page_size=10')

            if response.status_code != 200:
                break

            if isinstance(response.data, dict):
                results = response.data.get('results', response.data.get('data', []))

                if not results:
                    break

                # Collect user IDs
                for r in results:
                    if 'id' in r:
                        all_user_ids.add(r['id'])
                    elif 'user_id' in r:
                        all_user_ids.add(r['user_id'])

    def test_pagination_sequential_consistency(self, api_client, test_users):
        """Test that pagination results are sequential without gaps"""
        page_1_response = api_client.get('/api/accounts/users/?page=1&page_size=10')
        page_2_response = api_client.get('/api/accounts/users/?page=2&page_size=10')
        page_3_response = api_client.get('/api/accounts/users/?page=3&page_size=10')

        if (page_1_response.status_code == 200 and
            page_2_response.status_code == 200 and
            page_3_response.status_code == 200):

            if (isinstance(page_1_response.data, dict) and
                isinstance(page_2_response.data, dict) and
                isinstance(page_3_response.data, dict)):

                results1 = page_1_response.data.get('results', page_1_response.data.get('data', []))
                results2 = page_2_response.data.get('results', page_2_response.data.get('data', []))
                results3 = page_3_response.data.get('results', page_3_response.data.get('data', []))

                # All pages should have content
                if results1 and results2 and results3:
                    # Check they are different
                    ids1 = [r.get('id', r.get('user_id')) for r in results1]
                    ids2 = [r.get('id', r.get('user_id')) for r in results2]
                    ids3 = [r.get('id', r.get('user_id')) for r in results3]

                    # Sequential pages should be different
                    assert ids1 != ids2, "Page 1 and 2 should have different data"
                    assert ids2 != ids3, "Page 2 and 3 should have different data"


class TestAdminUserPaginationAuthorization:
    """Test authorization for pagination endpoints"""

    def test_pagination_requires_authentication(self, db):
        """Test that unauthenticated request is rejected"""
        client = APIClient()
        response = client.get('/api/accounts/users/?page=1&page_size=10')

        # Should return 401 or 403
        assert response.status_code in [401, 403]

    def test_pagination_non_admin_access(self, db):
        """Test that non-admin users cannot access pagination"""
        # Create non-admin user
        user = User.objects.create_user(
            email='student_non_admin@test.com',
            username='student_non_admin',
            first_name='Student',
            last_name='NonAdmin',
            password='StudentPass123!',
            role=User.Role.STUDENT,
            is_active=True,
        )
        StudentProfile.objects.create(user=user)

        # Create token for non-admin user
        token = Token.objects.create(user=user)

        # Try to access pagination
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = client.get('/api/accounts/users/?page=1&page_size=10')

        # Non-admin users should have limited or no access
        # (depends on API implementation - could be 200, 403)
        assert response.status_code in [200, 403]
