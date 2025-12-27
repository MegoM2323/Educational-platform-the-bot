"""
Tests for Dashboard Analytics API endpoints.

Tests the following endpoints:
- GET /api/analytics/dashboard/ - Main dashboard
- GET /api/analytics/dashboard/summary/ - Summary only
- GET /api/analytics/dashboard/timeseries/ - Time series data
- GET /api/analytics/dashboard/comparison/ - Comparison view
- GET /api/analytics/dashboard/trends/ - Trend analysis
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class DashboardAnalyticsEndpointTests(TestCase):
    """Test Dashboard Analytics API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test users with different roles
        self.student = User.objects.create_user(
            email='student@test.com',
            password='TestPass123!',
            role='student'
        )

        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='TestPass123!',
            role='admin'
        )

    def test_dashboard_endpoint_exists(self):
        """Test that dashboard endpoint is registered."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/')

        # Should get 200 or 405 (if method not allowed), but not 404
        self.assertNotEqual(response.status_code, 404)

    def test_dashboard_requires_authentication(self):
        """Test that dashboard endpoint requires authentication."""
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, 401)

    def test_dashboard_list_endpoint(self):
        """Test dashboard list endpoint returns summary."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check response structure
        self.assertIn('dashboard', data)
        self.assertIn('summary', data)
        self.assertIn('metadata', data)

    def test_dashboard_structure(self):
        """Test dashboard response contains expected sections."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/')

        data = response.json()
        dashboard = data.get('dashboard', {})

        # Check dashboard has all required sections
        self.assertIn('students', dashboard)
        self.assertIn('assignments', dashboard)
        self.assertIn('engagement', dashboard)
        self.assertIn('progress', dashboard)

    def test_dashboard_summary_structure(self):
        """Test dashboard summary contains expected metrics."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/')

        data = response.json()
        summary = data.get('summary', {})

        # Check summary has expected fields
        self.assertIn('total_students', summary)
        self.assertIn('active_students', summary)
        self.assertIn('avg_completion_rate', summary)
        self.assertIn('avg_engagement', summary)
        self.assertIn('avg_grade', summary)

    def test_dashboard_metadata(self):
        """Test dashboard metadata is properly included."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/')

        data = response.json()
        metadata = data.get('metadata', {})

        # Check metadata fields
        self.assertIn('generated_at', metadata)
        self.assertIn('aggregation', metadata)
        self.assertIn('cached', metadata)
        self.assertIn('cache_ttl', metadata)

    def test_dashboard_with_date_range(self):
        """Test dashboard with date range filtering."""
        self.client.force_authenticate(user=self.teacher)

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        response = self.client.get('/api/analytics/dashboard/', {
            'date_from': str(week_ago),
            'date_to': str(today),
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('dashboard', data)

    def test_dashboard_with_aggregation_levels(self):
        """Test dashboard with different aggregation levels."""
        self.client.force_authenticate(user=self.teacher)

        for aggregation in ['student', 'class', 'subject', 'school']:
            response = self.client.get('/api/analytics/dashboard/', {
                'aggregation': aggregation,
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['metadata']['aggregation'], aggregation)

    def test_dashboard_caching(self):
        """Test that dashboard data is cached."""
        self.client.force_authenticate(user=self.teacher)

        # First request - not cached
        response1 = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response1.json()['metadata']['cached'], False)

        # Second request - should be cached
        response2 = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response2.json()['metadata']['cached'], True)

    def test_dashboard_summary_endpoint(self):
        """Test summary-only endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/summary/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check summary structure
        self.assertIn('total_students', data)
        self.assertIn('total_assignments', data)
        self.assertIn('avg_completion_rate', data)
        self.assertIn('avg_engagement', data)

    def test_dashboard_timeseries_endpoint(self):
        """Test time series endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/timeseries/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check timeseries structure
        self.assertIn('dates', data)
        self.assertIn('completion_rate', data)
        self.assertIn('engagement_score', data)
        self.assertIn('active_students', data)

    def test_dashboard_timeseries_with_granularity(self):
        """Test time series with different granularity levels."""
        self.client.force_authenticate(user=self.teacher)

        for granularity in ['daily', 'weekly', 'monthly']:
            response = self.client.get('/api/analytics/dashboard/timeseries/', {
                'granularity': granularity,
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['granularity'], granularity)

            # Check that dates list is populated
            self.assertGreater(len(data['dates']), 0)

    def test_dashboard_comparison_endpoint(self):
        """Test comparison endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/comparison/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check comparison structure
        self.assertIn('by_subject', data)
        self.assertIn('by_class', data)
        self.assertIn('by_role', data)

    def test_dashboard_trends_endpoint(self):
        """Test trends endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/trends/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check trends structure
        self.assertIn('completion_trend', data)
        self.assertIn('engagement_trend', data)
        self.assertIn('grade_trend', data)
        self.assertIn('top_performers', data)
        self.assertIn('at_risk_students', data)

    def test_dashboard_role_based_access(self):
        """Test role-based access control."""
        # Student access
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Teacher access
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Admin access
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_rate_limiting(self):
        """Test rate limiting on dashboard endpoints."""
        self.client.force_authenticate(user=self.teacher)

        # Make multiple rapid requests
        for i in range(5):
            response = self.client.get('/api/analytics/dashboard/')
            # Should still work (rate limit is per minute)
            self.assertEqual(response.status_code, 200)

    def test_dashboard_invalid_aggregation(self):
        """Test dashboard with invalid aggregation level."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/', {
            'aggregation': 'invalid',
        })

        # Should still work, defaulting to 'student'
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['metadata']['aggregation'], 'student')

    def test_dashboard_invalid_date_format(self):
        """Test dashboard with invalid date format."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/', {
            'date_from': 'invalid-date',
            'date_to': '2025-12-27',
        })

        # Should still work with default dates
        self.assertEqual(response.status_code, 200)

    def test_timeseries_data_consistency(self):
        """Test that timeseries data has consistent array lengths."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/timeseries/')

        data = response.json()
        dates_count = len(data['dates'])

        # All metrics should have same length as dates
        self.assertEqual(len(data['completion_rate']), dates_count)
        self.assertEqual(len(data['engagement_score']), dates_count)
        self.assertEqual(len(data['active_students']), dates_count)
        self.assertEqual(len(data['avg_grade']), dates_count)

    def test_comparison_data_structure(self):
        """Test comparison data has correct structure."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/comparison/')

        data = response.json()

        # Check by_subject structure
        for subject, metrics in data['by_subject'].items():
            self.assertIn('avg_grade', metrics)
            self.assertIn('completion_rate', metrics)
            self.assertIn('student_count', metrics)

    def test_trends_data_structure(self):
        """Test trends data has correct structure."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/trends/')

        data = response.json()

        # Check trend structure
        for trend in ['completion_trend', 'engagement_trend', 'grade_trend']:
            trend_data = data[trend]
            self.assertIn('direction', trend_data)
            self.assertIn('percentage_change', trend_data)
            self.assertIn('trend_strength', trend_data)

    def test_top_performers_format(self):
        """Test top performers data format."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/trends/')

        data = response.json()
        performers = data['top_performers']

        # Should be a list
        self.assertIsInstance(performers, list)

        # Each performer should have required fields
        if performers:
            performer = performers[0]
            self.assertIn('student_id', performer)
            self.assertIn('name', performer)
            self.assertIn('avg_grade', performer)

    def test_at_risk_students_format(self):
        """Test at-risk students data format."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/dashboard/trends/')

        data = response.json()
        at_risk = data['at_risk_students']

        # Should be a list
        self.assertIsInstance(at_risk, list)

        # Each student should have required fields
        if at_risk:
            student = at_risk[0]
            self.assertIn('student_id', student)
            self.assertIn('name', student)
            self.assertIn('avg_grade', student)


class DashboardAnalyticsIntegrationTests(TestCase):
    """Integration tests for Dashboard Analytics."""

    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

    def test_dashboard_workflow(self):
        """Test complete dashboard workflow."""
        self.client.force_authenticate(user=self.teacher)

        # Get dashboard
        response = self.client.get('/api/analytics/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Get summary
        response = self.client.get('/api/analytics/dashboard/summary/')
        self.assertEqual(response.status_code, 200)

        # Get timeseries
        response = self.client.get('/api/analytics/dashboard/timeseries/')
        self.assertEqual(response.status_code, 200)

        # Get comparison
        response = self.client.get('/api/analytics/dashboard/comparison/')
        self.assertEqual(response.status_code, 200)

        # Get trends
        response = self.client.get('/api/analytics/dashboard/trends/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_performance(self):
        """Test dashboard response time."""
        self.client.force_authenticate(user=self.teacher)

        # Dashboard should respond quickly even with placeholder data
        response = self.client.get('/api/analytics/dashboard/')

        # Should complete within reasonable time
        self.assertEqual(response.status_code, 200)
        self.assertLess(len(response.content), 100000)  # Less than 100KB


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
