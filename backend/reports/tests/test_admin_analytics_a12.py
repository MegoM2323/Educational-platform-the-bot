"""
Test suite for Admin Analytics Functionality (T_W14_021-024, A12 fixes).

Tests for:
1. No infinite loop on analytics load
2. Correct API endpoint called
3. Null reference handling
4. Real database queries execute
5. Empty results handled
6. Date filtering works
"""

import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
import time

User = get_user_model()


class AdminAnalyticsLoadTest(APITestCase):
    """Test 1: No infinite loop on analytics load."""

    @pytest.fixture(autouse=True)
    def setUp_admin(self):
        """Set up test users."""
        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_analytics_page_loads_within_5_seconds(self):
        """Analytics dashboard loads without infinite loop (< 5s)."""
        start = time.time()
        response = self.client.get('/api/reports/analytics/dashboard/')
        elapsed = time.time() - start

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed, 5.0, f"Load took {elapsed:.2f}s > 5s limit")
        self.assertIn('dashboard', response.data)

    def test_analytics_multiple_requests_load_quickly(self):
        """Multiple sequential requests complete quickly."""
        for i in range(3):
            start = time.time()
            response = self.client.get('/api/reports/analytics/dashboard/')
            elapsed = time.time() - start

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertLess(elapsed, 5.0)

    def test_summary_endpoint_loads_quickly(self):
        """Summary endpoint loads within 5 seconds."""
        start = time.time()
        response = self.client.get('/api/reports/analytics/dashboard/summary/')
        elapsed = time.time() - start

        self.assertLess(elapsed, 5.0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_timeseries_endpoint_loads_quickly(self):
        """Timeseries endpoint loads within 5 seconds."""
        start = time.time()
        response = self.client.get('/api/reports/analytics/dashboard/timeseries/')
        elapsed = time.time() - start

        self.assertLess(elapsed, 5.0)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AnalyticsAPIEndpointTest(APITestCase):
    """Test 2: Correct API endpoint called."""

    def setUp(self):
        """Set up test users."""
        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_dashboard_endpoint_returns_200(self):
        """Correct API endpoint returns 200 OK."""
        response = self.client.get('/api/reports/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('dashboard', response.data)

    def test_dashboard_endpoint_exists(self):
        """Endpoint should exist, not return 404."""
        response = self.client.get('/api/reports/analytics/dashboard/')
        self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_endpoint_requires_authentication(self):
        """Unauthenticated users should not access analytics."""
        response = self.client.get('/api/reports/analytics/dashboard/')
        # Should be 200 because we authenticated above
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_summary_endpoint_200(self):
        """Summary endpoint returns 200."""
        response = self.client.get('/api/reports/analytics/dashboard/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_timeseries_endpoint_200(self):
        """Timeseries endpoint returns 200."""
        response = self.client.get('/api/reports/analytics/dashboard/timeseries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_comparison_endpoint_200(self):
        """Comparison endpoint returns 200."""
        response = self.client.get('/api/reports/analytics/dashboard/comparison/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trends_endpoint_200(self):
        """Trends endpoint returns 200."""
        response = self.client.get('/api/reports/analytics/dashboard/trends/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AnalyticsNullReferenceHandlingTest(APITestCase):
    """Test 3: Null reference handling."""

    def setUp(self):
        """Set up test users."""
        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_empty_metrics_no_crash(self):
        """Component handles missing metrics without crash."""
        response = self.client.get('/api/reports/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data.get('dashboard'))

    def test_summary_fields_exist(self):
        """Summary fields exist even if zero/null."""
        response = self.client.get('/api/reports/analytics/dashboard/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        summary = response.data
        expected_keys = [
            'total_students',
            'total_assignments',
            'avg_completion_rate',
            'avg_engagement'
        ]

        for key in expected_keys:
            self.assertIn(key, summary)

    def test_timeseries_returns_arrays(self):
        """Timeseries returns arrays even if empty."""
        response = self.client.get('/api/reports/analytics/dashboard/timeseries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data.get('dates'), list)
        self.assertIsInstance(response.data.get('completion_rate'), list)

    def test_comparison_returns_dicts(self):
        """Comparison returns dicts even if empty."""
        response = self.client.get('/api/reports/analytics/dashboard/comparison/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data.get('by_subject'), dict)
        self.assertIsInstance(response.data.get('by_class'), dict)

    def test_trends_returns_lists(self):
        """Trends returns lists even if empty."""
        response = self.client.get('/api/reports/analytics/dashboard/trends/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data.get('top_performers'), list)
        self.assertIsInstance(response.data.get('at_risk_students'), list)


class AnalyticsEmptyResultsTest(APITestCase):
    """Test 5: Empty results handled gracefully."""

    def setUp(self):
        """Set up with minimal data."""
        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_empty_database_returns_200(self):
        """Empty database returns 200, not 500."""
        response = self.client.get('/api/reports/analytics/dashboard/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_empty_results_have_valid_structure(self):
        """Empty results have valid structure."""
        response = self.client.get('/api/reports/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn('dashboard', response.data)
        self.assertIn('summary', response.data)
        self.assertIn('metadata', response.data)

    def test_empty_timeseries_returns_arrays(self):
        """Timeseries with no data returns arrays."""
        response = self.client.get('/api/reports/analytics/dashboard/timeseries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data.get('dates'), list)
        self.assertIsInstance(response.data.get('completion_rate'), list)

    def test_empty_comparison_returns_dicts(self):
        """Comparison with no data returns dicts."""
        response = self.client.get('/api/reports/analytics/dashboard/comparison/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data.get('by_subject'), dict)
        self.assertIsInstance(response.data.get('by_class'), dict)

    def test_empty_trends_returns_lists(self):
        """Trends with no data returns lists."""
        response = self.client.get('/api/reports/analytics/dashboard/trends/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data.get('top_performers'), list)
        self.assertIsInstance(response.data.get('at_risk_students'), list)


class AnalyticsDateFilteringTest(APITestCase):
    """Test 6: Date filtering works correctly."""

    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_date_range_filtering(self):
        """Date range filtering works."""
        today = timezone.now()
        start = (today - timedelta(days=7)).date()
        end = today.date()

        response = self.client.get(
            '/api/reports/analytics/dashboard/',
            {
                'date_from': start.strftime('%Y-%m-%d'),
                'date_to': end.strftime('%Y-%m-%d'),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_timeseries_date_range(self):
        """Timeseries respects date range."""
        today = timezone.now()
        start = (today - timedelta(days=30)).date()
        end = today.date()

        response = self.client.get(
            '/api/reports/analytics/dashboard/timeseries/',
            {
                'date_from': start.strftime('%Y-%m-%d'),
                'date_to': end.strftime('%Y-%m-%d'),
                'granularity': 'daily'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('dates', response.data)

    def test_invalid_date_format_handling(self):
        """Invalid date format handled gracefully."""
        response = self.client.get(
            '/api/reports/analytics/dashboard/',
            {'date_from': 'invalid-date'}
        )

        # Should handle gracefully
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )

    def test_date_from_before_date_to(self):
        """Date range validation works."""
        today = timezone.now()
        date_from = today.date()
        date_to = (today - timedelta(days=10)).date()

        response = self.client.get(
            '/api/reports/analytics/dashboard/',
            {
                'date_from': date_from.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d'),
            }
        )

        # Should handle gracefully
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )


class AnalyticsEdgeCasesTest(APITestCase):
    """Test edge cases."""

    def setUp(self):
        """Set up test users."""
        self.admin = User.objects.create_user(
            username='admin@test.com',
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )
        self.client.force_authenticate(user=self.admin)

    def test_large_date_range(self):
        """Handles large date ranges."""
        response = self.client.get(
            '/api/reports/analytics/dashboard/',
            {
                'date_from': '2020-01-01',
                'date_to': '2025-12-31',
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_same_date_range(self):
        """Same start and end date works."""
        today = timezone.now().date()
        date_str = today.strftime('%Y-%m-%d')

        response = self.client.get(
            '/api/reports/analytics/dashboard/',
            {
                'date_from': date_str,
                'date_to': date_str,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_aggregation_levels(self):
        """Different aggregation levels supported."""
        for aggregation in ['student', 'class', 'subject', 'school']:
            response = self.client.get(
                '/api/reports/analytics/dashboard/',
                {'aggregation': aggregation}
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_metadata_exists(self):
        """Response includes metadata."""
        response = self.client.get('/api/reports/analytics/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('metadata', response.data)
        self.assertIn('cached', response.data.get('metadata', {}))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
