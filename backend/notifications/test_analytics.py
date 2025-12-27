"""
Test suite for notification analytics module

Tests cover:
- Metrics calculation correctness
- Filtering by date range
- Filtering by type/channel
- Caching behavior
- Endpoint permissions
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Notification, NotificationQueue
from .analytics import NotificationAnalytics

User = get_user_model()


class NotificationAnalyticsTestCase(TestCase):
    """
    Test NotificationAnalytics service methods
    """

    def setUp(self):
        """
        Create test users and notifications
        """
        # Clear cache before each test
        cache.clear()

        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )

        self.student_user = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123'
        )

        self.now = timezone.now()
        self.yesterday = self.now - timedelta(days=1)
        self.week_ago = self.now - timedelta(days=7)

    def test_get_metrics_default_date_range(self):
        """
        Test metrics with default date range (7 days)
        """
        # Create notifications
        for i in range(10):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Test {i}',
                message='Test message',
                type='assignment_new',
                is_sent=True,
                is_read=i < 5  # 5 read, 5 unread
            )

        metrics = NotificationAnalytics.get_metrics()

        assert metrics['total_sent'] == 10
        assert metrics['total_opened'] == 5
        assert metrics['open_rate'] == 50.0

    def test_get_metrics_with_date_filter(self):
        """
        Test metrics with specific date range
        """
        # Create notifications at different times
        for i in range(5):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Old {i}',
                message='Old message',
                type='assignment_new',
                created_at=self.week_ago,
                is_sent=True,
                is_read=True
            )

        for i in range(10):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Recent {i}',
                message='Recent message',
                type='assignment_new',
                created_at=self.now,
                is_sent=True,
                is_read=True
            )

        # Get metrics for recent date range
        metrics = NotificationAnalytics.get_metrics(
            date_from=self.yesterday,
            date_to=self.now
        )

        # Should only include recent notifications
        assert metrics['total_sent'] == 10
        assert metrics['total_opened'] == 10

    def test_get_metrics_by_type(self):
        """
        Test metrics filtered by notification type
        """
        # Create notifications of different types
        for i in range(10):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Assignment {i}',
                message='Assignment message',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

        for i in range(5):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Material {i}',
                message='Material message',
                type='material_new',
                is_sent=True,
                is_read=True
            )

        # Get metrics for assignment_new type
        metrics = NotificationAnalytics.get_metrics(
            notification_type='assignment_new'
        )

        assert metrics['total_sent'] == 10
        by_type = metrics['by_type']
        assert 'assignment_new' in by_type
        assert by_type['assignment_new']['count'] == 10
        assert 'material_new' not in by_type  # Only requested type

    def test_get_metrics_by_channel(self):
        """
        Test metrics filtered by delivery channel
        """
        # Create notifications
        for i in range(10):
            notification = Notification.objects.create(
                recipient=self.student_user,
                title=f'Test {i}',
                message='Test message',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

            # Create queue entries for different channels
            if i < 5:
                NotificationQueue.objects.create(
                    notification=notification,
                    channel='email',
                    status='sent'
                )
            else:
                NotificationQueue.objects.create(
                    notification=notification,
                    channel='push',
                    status='sent'
                )

        # Get metrics for email channel
        metrics = NotificationAnalytics.get_metrics(
            channel='email'
        )

        by_channel = metrics['by_channel']
        assert 'email' in by_channel
        assert by_channel['email']['count'] == 5

    def test_get_metrics_by_time_day_granularity(self):
        """
        Test metrics grouped by day
        """
        # Create notifications on different days
        for i in range(5):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Today {i}',
                message='Today',
                type='assignment_new',
                created_at=self.now,
                is_sent=True,
                is_read=True
            )

        for i in range(3):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Yesterday {i}',
                message='Yesterday',
                type='assignment_new',
                created_at=self.yesterday,
                is_sent=True,
                is_read=True
            )

        metrics = NotificationAnalytics.get_metrics(
            granularity='day'
        )

        by_time = metrics['by_time']
        assert len(by_time) >= 2  # At least 2 days of data
        assert all('time' in item for item in by_time)
        assert all('count' in item for item in by_time)

    def test_delivery_rate_calculation(self):
        """
        Test delivery rate percentage calculation
        """
        # Create 10 notifications, 8 delivered
        for i in range(8):
            notification = Notification.objects.create(
                recipient=self.student_user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
            )
            NotificationQueue.objects.create(
                notification=notification,
                channel='email',
                status='sent'
            )

        for i in range(2):
            notification = Notification.objects.create(
                recipient=self.student_user,
                title=f'Failed {i}',
                message='Failed',
                type='assignment_new',
                is_sent=False,
            )
            NotificationQueue.objects.create(
                notification=notification,
                channel='email',
                status='failed'
            )

        metrics = NotificationAnalytics.get_metrics()

        assert metrics['total_sent'] == 10
        assert metrics['total_delivered'] == 8
        assert metrics['delivery_rate'] == 80.0

    def test_open_rate_calculation(self):
        """
        Test open rate percentage calculation
        """
        # Create 10 notifications, 6 opened
        for i in range(6):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Opened {i}',
                message='Opened',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

        for i in range(4):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Unopened {i}',
                message='Unopened',
                type='assignment_new',
                is_sent=True,
                is_read=False
            )

        metrics = NotificationAnalytics.get_metrics()

        assert metrics['total_sent'] == 10
        assert metrics['total_opened'] == 6
        assert metrics['open_rate'] == 60.0

    def test_caching_behavior(self):
        """
        Test that results are cached properly
        """
        # Create notifications
        for i in range(5):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

        # First call should hit database
        metrics1 = NotificationAnalytics.get_metrics()
        assert metrics1['total_sent'] == 5

        # Create more notifications
        Notification.objects.create(
            recipient=self.student_user,
            title='New',
            message='New',
            type='assignment_new',
            is_sent=True,
            is_read=True
        )

        # Second call should return cached result (still 5)
        metrics2 = NotificationAnalytics.get_metrics()
        assert metrics2['total_sent'] == 5

        # Invalidate cache
        NotificationAnalytics.invalidate_cache()

        # Third call should hit database (now 6)
        metrics3 = NotificationAnalytics.get_metrics()
        assert metrics3['total_sent'] == 6

    def test_get_delivery_rate_helper(self):
        """
        Test get_delivery_rate helper method
        """
        # Create 10 notifications, 9 delivered
        for i in range(9):
            notification = Notification.objects.create(
                recipient=self.student_user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
            )
            NotificationQueue.objects.create(
                notification=notification,
                channel='email',
                status='sent'
            )

        for i in range(1):
            notification = Notification.objects.create(
                recipient=self.student_user,
                title='Failed',
                message='Failed',
                type='assignment_new',
                is_sent=False,
            )
            NotificationQueue.objects.create(
                notification=notification,
                channel='email',
                status='failed'
            )

        rate = NotificationAnalytics.get_delivery_rate()
        assert rate == 90.0

    def test_get_open_rate_helper(self):
        """
        Test get_open_rate helper method
        """
        # Create 10 notifications, 7 opened
        for i in range(7):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Opened {i}',
                message='Opened',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

        for i in range(3):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Unopened {i}',
                message='Unopened',
                type='assignment_new',
                is_sent=True,
                is_read=False
            )

        rate = NotificationAnalytics.get_open_rate()
        assert rate == 70.0

    def test_get_top_performing_types(self):
        """
        Test getting top performing notification types
        """
        # Create notifications of different types with different open rates
        for i in range(10):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Assignment {i}',
                message='Assignment',
                type='assignment_new',
                is_sent=True,
                is_read=i < 9  # 90% open rate
            )

        for i in range(10):
            Notification.objects.create(
                recipient=self.student_user,
                title=f'Material {i}',
                message='Material',
                type='material_new',
                is_sent=True,
                is_read=i < 7  # 70% open rate
            )

        top_types = NotificationAnalytics.get_top_performing_types(limit=2)

        assert len(top_types) <= 2
        assert top_types[0]['type'] == 'assignment_new'
        assert top_types[0]['open_rate'] == 90.0
        assert top_types[1]['type'] == 'material_new'
        assert top_types[1]['open_rate'] == 70.0

    def test_get_channel_performance(self):
        """
        Test getting channel performance metrics
        """
        # Create notifications with different channels
        for i in range(10):
            notification = Notification.objects.create(
                recipient=self.student_user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
            )

            if i < 8:
                # Email: 80% delivery rate
                NotificationQueue.objects.create(
                    notification=notification,
                    channel='email',
                    status='sent' if i < 8 else 'failed'
                )
            else:
                # Push: 0% delivery rate for these 2
                NotificationQueue.objects.create(
                    notification=notification,
                    channel='push',
                    status='failed'
                )

        perf = NotificationAnalytics.get_channel_performance()

        assert 'email' in perf
        assert 'push' in perf

    def test_empty_date_range(self):
        """
        Test metrics with empty date range (no notifications)
        """
        future_date = self.now + timedelta(days=7)

        metrics = NotificationAnalytics.get_metrics(
            date_from=future_date,
            date_to=future_date + timedelta(days=1)
        )

        assert metrics['total_sent'] == 0
        assert metrics['delivery_rate'] == 0
        assert metrics['open_rate'] == 0

    def test_metrics_with_none_values(self):
        """
        Test metrics calculation with None/zero values
        """
        # Create notification but no queue entries
        Notification.objects.create(
            recipient=self.student_user,
            title='No Queue',
            message='No queue entry',
            type='assignment_new',
            is_sent=False,
            is_read=False
        )

        metrics = NotificationAnalytics.get_metrics()

        # Should handle gracefully
        assert metrics['total_sent'] == 1
        assert metrics['total_delivered'] == 0
        assert metrics['delivery_rate'] == 0.0


class AnalyticsEndpointTestCase(APITestCase):
    """
    Test analytics API endpoints
    """

    def setUp(self):
        """
        Create test users and data
        """
        cache.clear()

        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )

        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )

        self.client = Client()
        self.now = timezone.now()

    def test_metrics_endpoint_requires_authentication(self):
        """
        Test that metrics endpoint requires authentication
        """
        response = self.client.get('/api/notifications/analytics/metrics/')

        assert response.status_code == status.HTTP_403_FORBIDDEN or \
               response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_metrics_endpoint_requires_admin(self):
        """
        Test that metrics endpoint requires admin permission
        """
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get('/api/notifications/analytics/metrics/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_metrics_endpoint_with_admin(self):
        """
        Test metrics endpoint returns data for admin users
        """
        # Create test notifications
        for i in range(5):
            Notification.objects.create(
                recipient=self.admin_user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/notifications/analytics/metrics/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'total_sent' in data
        assert 'delivery_rate' in data
        assert 'open_rate' in data
        assert 'by_type' in data
        assert 'by_channel' in data

    def test_performance_endpoint_with_admin(self):
        """
        Test performance endpoint
        """
        # Create test notifications with queue entries
        for i in range(5):
            notification = Notification.objects.create(
                recipient=self.admin_user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
            )
            NotificationQueue.objects.create(
                notification=notification,
                channel='email',
                status='sent'
            )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/notifications/analytics/performance/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'channels' in data
        assert 'best_channel' in data
        assert 'worst_channel' in data

    def test_top_types_endpoint_with_admin(self):
        """
        Test top types endpoint
        """
        # Create notifications of different types
        for i in range(10):
            Notification.objects.create(
                recipient=self.admin_user,
                title=f'Assignment {i}',
                message='Assignment',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )

        for i in range(5):
            Notification.objects.create(
                recipient=self.admin_user,
                title=f'Material {i}',
                message='Material',
                type='material_new',
                is_sent=True,
                is_read=i < 3  # 60% open rate
            )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get('/api/notifications/analytics/top-types/')

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'top_types' in data
        assert len(data['top_types']) > 0

    def test_metrics_endpoint_with_date_filters(self):
        """
        Test metrics endpoint with date range filters
        """
        self.client.force_authenticate(user=self.admin_user)

        date_from = (self.now - timedelta(days=7)).date()
        date_to = self.now.date()

        response = self.client.get(
            '/api/notifications/analytics/metrics/',
            {
                'date_from': date_from.isoformat(),
                'date_to': date_to.isoformat(),
            }
        )

        assert response.status_code == status.HTTP_200_OK

    def test_metrics_endpoint_with_type_filter(self):
        """
        Test metrics endpoint with type filter
        """
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(
            '/api/notifications/analytics/metrics/',
            {
                'type': 'assignment_new',
            }
        )

        assert response.status_code == status.HTTP_200_OK

    def test_metrics_endpoint_with_channel_filter(self):
        """
        Test metrics endpoint with channel filter
        """
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(
            '/api/notifications/analytics/metrics/',
            {
                'channel': 'email',
            }
        )

        assert response.status_code == status.HTTP_200_OK

    def test_metrics_endpoint_with_granularity(self):
        """
        Test metrics endpoint with different granularity
        """
        self.client.force_authenticate(user=self.admin_user)

        for granularity in ['hour', 'day', 'week']:
            response = self.client.get(
                '/api/notifications/analytics/metrics/',
                {
                    'granularity': granularity,
                }
            )

            assert response.status_code == status.HTTP_200_OK
