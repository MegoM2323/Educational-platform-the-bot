"""
Test suite for notification click tracking and analytics

Tests cover:
- Click tracking model
- Click rate calculation
- Analytics with click metrics
- Track click API endpoint
"""

import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Notification, NotificationClick
from .analytics import NotificationAnalytics

User = get_user_model()


class NotificationClickModelTestCase(TestCase):
    """
    Test NotificationClick model
    """

    def setUp(self):
        """
        Create test users and notifications
        """
        self.user = User.objects.create_user(
            username='test_user',
            email='user@test.com',
            password='testpass123'
        )

        self.notification = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='Test message',
            type='assignment_new',
            is_sent=True
        )

    def test_create_notification_click(self):
        """
        Test creating a notification click
        """
        click = NotificationClick.objects.create(
            notification=self.notification,
            user=self.user,
            action_type='link_click',
            action_url='https://example.com/test',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )

        assert click.id is not None
        assert click.notification == self.notification
        assert click.user == self.user
        assert click.action_type == 'link_click'
        assert click.action_url == 'https://example.com/test'

    def test_click_relationships(self):
        """
        Test click relationships with notification and user
        """
        click = NotificationClick.objects.create(
            notification=self.notification,
            user=self.user,
            action_type='in_app_click'
        )

        # Check reverse relations
        assert click.notification.clicks.count() == 1
        assert click in self.notification.clicks.all()
        assert click in self.user.notification_clicks.all()

    def test_action_data_json(self):
        """
        Test click with JSON action data
        """
        action_data = {
            'button_id': 'submit_btn',
            'page': '/assignment/123',
            'timestamp': '2025-12-27T12:00:00Z'
        }

        click = NotificationClick.objects.create(
            notification=self.notification,
            user=self.user,
            action_type='button_click',
            action_data=action_data
        )

        assert click.action_data == action_data

    def test_click_str_representation(self):
        """
        Test string representation of click
        """
        click = NotificationClick.objects.create(
            notification=self.notification,
            user=self.user,
            action_type='link_click'
        )

        str_repr = str(click)
        assert self.user.email in str_repr
        assert str(self.notification.id) in str_repr


class NotificationClickAnalyticsTestCase(TestCase):
    """
    Test click tracking in analytics
    """

    def setUp(self):
        """
        Create test data
        """
        self.user = User.objects.create_user(
            username='test_user',
            email='user@test.com',
            password='testpass123'
        )

        self.now = timezone.now()
        self.yesterday = self.now - timedelta(days=1)

    def test_click_rate_calculation(self):
        """
        Test click rate percentage calculation
        """
        # Create 10 notifications
        notifications = []
        for i in range(10):
            notif = Notification.objects.create(
                recipient=self.user,
                title=f'Test {i}',
                message='Test',
                type='assignment_new',
                is_sent=True,
                is_read=True
            )
            notifications.append(notif)

        # 5 notifications have clicks
        for i in range(5):
            NotificationClick.objects.create(
                notification=notifications[i],
                user=self.user,
                action_type='link_click'
            )

        metrics = NotificationAnalytics.get_metrics()

        assert metrics['total_sent'] == 10
        assert metrics['total_clicked'] == 5
        assert metrics['click_rate'] == 50.0

    def test_click_rate_by_type(self):
        """
        Test click rate grouped by notification type
        """
        # Create assignment notifications
        for i in range(10):
            notif = Notification.objects.create(
                recipient=self.user,
                title=f'Assignment {i}',
                message='Test',
                type='assignment_new',
                is_sent=True
            )

            # 8 have clicks
            if i < 8:
                NotificationClick.objects.create(
                    notification=notif,
                    user=self.user,
                    action_type='link_click'
                )

        # Create material notifications
        for i in range(10):
            notif = Notification.objects.create(
                recipient=self.user,
                title=f'Material {i}',
                message='Test',
                type='material_new',
                is_sent=True
            )

            # 6 have clicks
            if i < 6:
                NotificationClick.objects.create(
                    notification=notif,
                    user=self.user,
                    action_type='link_click'
                )

        metrics = NotificationAnalytics.get_metrics()
        by_type = metrics['by_type']

        assert 'assignment_new' in by_type
        assert by_type['assignment_new']['clicked'] == 8
        assert by_type['assignment_new']['click_rate'] == 80.0

        assert 'material_new' in by_type
        assert by_type['material_new']['clicked'] == 6
        assert by_type['material_new']['click_rate'] == 60.0

    def test_get_notification_clicks(self):
        """
        Test getting clicks for a specific notification
        """
        notif = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test',
            type='assignment_new',
            is_sent=True
        )

        # Create 3 clicks of different types
        for action_type in ['link_click', 'in_app_click', 'button_click']:
            NotificationClick.objects.create(
                notification=notif,
                user=self.user,
                action_type=action_type
            )

        clicks = NotificationAnalytics.get_notification_clicks(notif.id)
        assert clicks.count() == 3

        # Filter by action type
        link_clicks = NotificationAnalytics.get_notification_clicks(
            notif.id,
            action_type='link_click'
        )
        assert link_clicks.count() == 1

    def test_get_user_clicks_by_type(self):
        """
        Test getting user clicks grouped by notification type
        """
        # Create assignment notifications with clicks
        for i in range(5):
            notif = Notification.objects.create(
                recipient=self.user,
                title=f'Assignment {i}',
                message='Test',
                type='assignment_new',
                is_sent=True
            )
            NotificationClick.objects.create(
                notification=notif,
                user=self.user,
                action_type='link_click'
            )

        # Create material notifications with clicks
        for i in range(3):
            notif = Notification.objects.create(
                recipient=self.user,
                title=f'Material {i}',
                message='Test',
                type='material_new',
                is_sent=True
            )
            NotificationClick.objects.create(
                notification=notif,
                user=self.user,
                action_type='link_click'
            )

        clicks_by_type = NotificationAnalytics.get_user_clicks_by_type(self.user.id)

        assert clicks_by_type['assignment_new'] == 5
        assert clicks_by_type['material_new'] == 3

    def test_track_click_method(self):
        """
        Test NotificationAnalytics.track_click() method
        """
        notif = Notification.objects.create(
            recipient=self.user,
            title='Test',
            message='Test',
            type='assignment_new',
            is_sent=True
        )

        click = NotificationAnalytics.track_click(
            notification_id=notif.id,
            user_id=self.user.id,
            action_type='link_click',
            action_url='https://example.com/test',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )

        assert click is not None
        assert click.notification == notif
        assert click.user == self.user
        assert click.action_type == 'link_click'

    def test_track_click_invalid_notification(self):
        """
        Test tracking click for non-existent notification
        """
        click = NotificationAnalytics.track_click(
            notification_id=9999,
            user_id=self.user.id,
            action_type='link_click'
        )

        assert click is None

    def test_click_rate_with_empty_data(self):
        """
        Test click rate with no notifications
        """
        metrics = NotificationAnalytics.get_metrics()

        assert metrics['total_sent'] == 0
        assert metrics['total_clicked'] == 0
        assert metrics['click_rate'] == 0


class TrackClickAPITestCase(APITestCase):
    """
    Test click tracking API endpoint
    """

    def setUp(self):
        """
        Create test data
        """
        self.user = User.objects.create_user(
            username='test_user',
            email='user@test.com',
            password='testpass123'
        )

        self.notification = Notification.objects.create(
            recipient=self.user,
            title='Test Notification',
            message='Test message',
            type='assignment_new',
            is_sent=True
        )

        self.client = Client()

    def test_track_click_requires_authentication(self):
        """
        Test that track click requires authentication
        """
        response = self.client.post('/api/notifications/analytics/track_click/')

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_track_click_valid_data(self):
        """
        Test tracking click with valid data
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'notification_id': self.notification.id,
            'action_type': 'link_click',
            'action_url': 'https://example.com/test'
        }

        response = self.client.post(
            '/api/notifications/analytics/track_click/',
            data=data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data['notification_id'] == self.notification.id
        assert response_data['action_type'] == 'link_click'

    def test_track_click_missing_notification_id(self):
        """
        Test tracking click without notification_id
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'action_type': 'link_click'
        }

        response = self.client.post(
            '/api/notifications/analytics/track_click/',
            data=data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_track_click_invalid_notification_id(self):
        """
        Test tracking click for non-existent notification
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'notification_id': 9999,
            'action_type': 'link_click'
        }

        response = self.client.post(
            '/api/notifications/analytics/track_click/',
            data=data,
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_track_click_with_all_fields(self):
        """
        Test tracking click with all optional fields
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'notification_id': self.notification.id,
            'action_type': 'button_click',
            'action_url': 'https://example.com/test',
            'action_data': {'button_id': 'submit'},
            'user_agent': 'Mozilla/5.0...',
            'ip_address': '192.168.1.1'
        }

        response = self.client.post(
            '/api/notifications/analytics/track_click/',
            data=data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data['action_data'] == {'button_id': 'submit'}
        assert response_data['ip_address'] == '192.168.1.1'

    def test_track_click_increments_click_count(self):
        """
        Test that click tracking increments the click count in metrics
        """
        self.client.force_authenticate(user=self.user)

        # Track a click
        data = {
            'notification_id': self.notification.id,
            'action_type': 'link_click'
        }

        self.client.post(
            '/api/notifications/analytics/track_click/',
            data=data,
            format='json'
        )

        # Check metrics
        metrics = NotificationAnalytics.get_metrics()
        assert metrics['total_clicked'] == 1
        assert metrics['click_rate'] == 100.0  # 1 out of 1 notification

    def test_track_click_multiple_times(self):
        """
        Test tracking multiple clicks on the same notification
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'notification_id': self.notification.id,
            'action_type': 'link_click'
        }

        # Track 3 clicks
        for _ in range(3):
            response = self.client.post(
                '/api/notifications/analytics/track_click/',
                data=data,
                format='json'
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Check that clicks are recorded
        clicks = NotificationClick.objects.filter(
            notification=self.notification,
            user=self.user
        )
        assert clicks.count() == 3
