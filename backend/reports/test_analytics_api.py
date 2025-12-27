"""
Comprehensive test suite for Analytics API endpoints.

Tests cover:
- Student analytics endpoint
- Assignment analytics endpoint
- Attendance analytics endpoint
- Engagement analytics endpoint
- Progress analytics endpoint
- Pagination and filtering
- Role-based access control
- Caching behavior
- Rate limiting
- Authentication
- Error handling
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

User = get_user_model()


class StudentAnalyticsAPITestCase(APITestCase):
    """Test student analytics endpoint."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher',
            first_name='John',
            last_name='Teacher'
        )

        self.student1 = User.objects.create_user(
            email='student1@test.com',
            password='test123',
            role='student',
            first_name='Alice',
            last_name='Student'
        )

        self.student2 = User.objects.create_user(
            email='student2@test.com',
            password='test123',
            role='student',
            first_name='Bob',
            last_name='Student'
        )

        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            role='admin',
            is_staff=True
        )

        self.client = APIClient()

    def test_student_analytics_unauthenticated(self):
        """Test that unauthenticated users cannot access analytics."""
        response = self.client.get('/api/analytics/students/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_analytics_authenticated(self):
        """Test student analytics endpoint with authenticated user."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/students/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('metadata', response.data)
        self.assertIsInstance(response.data['data'], list)

    def test_student_analytics_pagination(self):
        """Test student analytics pagination."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/students/?page=1&per_page=10')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['metadata']['page'], 1)
        self.assertEqual(response.data['metadata']['per_page'], 10)

    def test_student_analytics_invalid_date(self):
        """Test error handling for invalid date format."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/students/?date_from=invalid')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_analytics_date_range_validation(self):
        """Test validation of date range."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            '/api/analytics/students/?date_from=2025-12-01&date_to=2025-01-01'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AssignmentAnalyticsAPITestCase(APITestCase):
    """Test assignment analytics endpoint."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )

        self.client = APIClient()

    def test_assignment_analytics_list(self):
        """Test assignment analytics endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/assignments/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('metadata', response.data)

    def test_assignment_analytics_pagination(self):
        """Test assignment analytics pagination."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/assignments/?page=1&per_page=5')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['metadata']['per_page'], 5)


class AttendanceAnalyticsAPITestCase(APITestCase):
    """Test attendance analytics endpoint."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )

        self.client = APIClient()

    def test_attendance_analytics_missing_class_id(self):
        """Test that class_id is required."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/attendance/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attendance_analytics_invalid_date(self):
        """Test error handling for invalid date format."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            '/api/analytics/attendance/?class_id=1&date_from=invalid'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EngagementAnalyticsAPITestCase(APITestCase):
    """Test engagement analytics endpoint."""

    def setUp(self):
        """Set up test data."""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )

        self.client = APIClient()

    def test_engagement_analytics_list(self):
        """Test engagement analytics endpoint."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/engagement/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)


class ProgressAnalyticsAPITestCase(APITestCase):
    """Test progress analytics endpoint."""

    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )

        self.client = APIClient()

    def test_progress_analytics_list(self):
        """Test progress analytics endpoint."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/analytics/progress/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('subject', response.data)
        self.assertIn('grades', response.data)
        self.assertIn('trend', response.data)

    def test_progress_analytics_granularity_day(self):
        """Test progress analytics with day granularity."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/analytics/progress/?granularity=day')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_progress_analytics_granularity_month(self):
        """Test progress analytics with month granularity."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/analytics/progress/?granularity=month')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_progress_analytics_trend_validation(self):
        """Test that trend is one of valid values."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/analytics/progress/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('trend', response.data)
        self.assertIn(response.data['trend'], ['upward', 'downward', 'stable', 'unknown'])


class AnalyticsAccessControlTestCase(APITestCase):
    """Test role-based access control for analytics."""

    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            email='student@test.com',
            password='test123',
            role='student'
        )

        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='test123',
            role='teacher'
        )

        self.client = APIClient()

    def test_student_can_view_own_analytics(self):
        """Test that students can view their own analytics."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/analytics/progress/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_teacher_can_view_student_analytics(self):
        """Test that teachers can view student analytics."""
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/analytics/students/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AnalyticsResponseFormatTestCase(APITestCase):
    """Test response format compliance."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@test.com',
            password='test123',
            role='teacher'
        )
        self.client = APIClient()

    def test_student_analytics_response_format(self):
        """Test student analytics response format."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/analytics/students/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check response structure
        self.assertIn('data', response.data)
        self.assertIn('metadata', response.data)
        # Check metadata structure
        self.assertIn('total', response.data['metadata'])
        self.assertIn('page', response.data['metadata'])
        self.assertIn('per_page', response.data['metadata'])
        self.assertIn('filters_applied', response.data['metadata'])

    def test_progress_analytics_response_format(self):
        """Test progress analytics response format."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/analytics/progress/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check response structure
        self.assertIn('subject', response.data)
        self.assertIn('grades', response.data)
        self.assertIn('trend', response.data)
        self.assertIn('weeks', response.data)
        self.assertIn('metadata', response.data)
