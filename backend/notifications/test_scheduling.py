"""
Tests for notification scheduling functionality.
"""
import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Notification
from .scheduler import NotificationScheduler

User = get_user_model()


class NotificationSchedulerTestCase(TestCase):
    """Test cases for NotificationScheduler"""

    def setUp(self):
        """Set up test data"""
        self.scheduler = NotificationScheduler()

        # Create test users
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123'
        )

    def test_schedule_notification_single_recipient(self):
        """Test scheduling a notification for a single recipient"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='This is a test message',
            scheduled_at=scheduled_at,
            notif_type=Notification.Type.SYSTEM,
            priority=Notification.Priority.HIGH,
        )

        self.assertEqual(len(created_ids), 1)
        notification = Notification.objects.get(id=created_ids[0])

        self.assertEqual(notification.recipient, self.user1)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.message, 'This is a test message')
        self.assertEqual(notification.scheduled_status, 'pending')
        self.assertFalse(notification.is_sent)
        self.assertEqual(notification.scheduled_at, scheduled_at)

    def test_schedule_notification_multiple_recipients(self):
        """Test scheduling a notification for multiple recipients"""
        scheduled_at = timezone.now() + timedelta(hours=2)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id, self.user2.id],
            title='Bulk Notification',
            message='Message for multiple users',
            scheduled_at=scheduled_at,
        )

        self.assertEqual(len(created_ids), 2)

        notifications = Notification.objects.filter(id__in=created_ids)
        self.assertEqual(notifications.count(), 2)

        for notif in notifications:
            self.assertEqual(notif.scheduled_status, 'pending')
            self.assertFalse(notif.is_sent)

    def test_schedule_notification_past_date_raises_error(self):
        """Test that scheduling in the past raises ValueError"""
        past_time = timezone.now() - timedelta(hours=1)

        with self.assertRaises(ValueError) as context:
            self.scheduler.schedule_notification(
                recipients=[self.user1.id],
                title='Test',
                message='Test message',
                scheduled_at=past_time,
            )

        self.assertIn('must be in the future', str(context.exception))

    def test_schedule_notification_empty_recipients_raises_error(self):
        """Test that empty recipients list raises ValueError"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        with self.assertRaises(ValueError) as context:
            self.scheduler.schedule_notification(
                recipients=[],
                title='Test',
                message='Test message',
                scheduled_at=scheduled_at,
            )

        self.assertIn('cannot be empty', str(context.exception))

    def test_cancel_scheduled_notification(self):
        """Test cancelling a scheduled notification"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]

        # Cancel the notification
        success = self.scheduler.cancel_scheduled(notification_id)
        self.assertTrue(success)

        # Verify it's cancelled
        notification = Notification.objects.get(id=notification_id)
        self.assertEqual(notification.scheduled_status, 'cancelled')

    def test_cancel_already_sent_notification_fails(self):
        """Test that cancelling an already sent notification fails"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]
        notification = Notification.objects.get(id=notification_id)

        # Mark as sent manually
        notification.scheduled_status = 'sent'
        notification.save()

        # Try to cancel - should fail
        success = self.scheduler.cancel_scheduled(notification_id)
        self.assertFalse(success)

    def test_get_pending_notifications(self):
        """Test getting pending notifications that are due"""
        now = timezone.now()
        past_time = now - timedelta(minutes=5)
        future_time = now + timedelta(hours=1)

        # Create notifications with different scheduled times
        self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Past Notification',
            message='Should be pending',
            scheduled_at=past_time,
        )

        self.scheduler.schedule_notification(
            recipients=[self.user2.id],
            title='Future Notification',
            message='Should NOT be pending',
            scheduled_at=future_time,
        )

        # Get pending notifications
        pending = self.scheduler.get_pending_notifications()

        # Only the past scheduled notification should be pending
        self.assertEqual(pending.count(), 1)
        self.assertEqual(pending[0].recipient, self.user1)

    def test_send_scheduled_notification(self):
        """Test sending a scheduled notification"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]

        # Send the notification
        success = self.scheduler.send_scheduled_notification(notification_id)
        self.assertTrue(success)

        # Verify it's sent
        notification = Notification.objects.get(id=notification_id)
        self.assertEqual(notification.scheduled_status, 'sent')
        self.assertTrue(notification.is_sent)
        self.assertIsNotNone(notification.sent_at)

    def test_send_cancelled_notification_fails(self):
        """Test that sending a cancelled notification fails"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]

        # Cancel the notification
        self.scheduler.cancel_scheduled(notification_id)

        # Try to send - should fail
        success = self.scheduler.send_scheduled_notification(notification_id)
        self.assertFalse(success)

    def test_get_schedule_status(self):
        """Test getting schedule status of a notification"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        status_data = self.scheduler.get_schedule_status(created_ids[0])

        self.assertIsNotNone(status_data)
        self.assertEqual(status_data['id'], created_ids[0])
        self.assertEqual(status_data['title'], 'Test Notification')
        self.assertEqual(status_data['scheduled_status'], 'pending')
        self.assertFalse(status_data['is_sent'])
        self.assertIsNone(status_data['sent_at'])

    def test_retry_failed_notification(self):
        """Test retrying a failed notification"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]
        original_time = Notification.objects.get(id=notification_id).scheduled_at

        # Retry the notification
        success = self.scheduler.retry_failed_notification(
            notification_id,
            retry_delay_minutes=10
        )

        self.assertTrue(success)

        # Verify scheduled_at is updated
        notification = Notification.objects.get(id=notification_id)
        self.assertGreater(notification.scheduled_at, original_time)

    def test_retry_already_sent_notification_fails(self):
        """Test that retrying an already sent notification fails"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]
        notification = Notification.objects.get(id=notification_id)

        # Mark as sent
        notification.scheduled_status = 'sent'
        notification.save()

        # Try to retry - should fail
        success = self.scheduler.retry_failed_notification(notification_id)
        self.assertFalse(success)


class NotificationSchedulingAPITestCase(TestCase):
    """Test cases for scheduling API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123'
        )

    def test_schedule_notification_endpoint(self):
        """Test POST /api/notifications/schedule/"""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user1)

        scheduled_at = timezone.now() + timedelta(hours=1)

        data = {
            'recipients': [self.user1.id, self.user2.id],
            'title': 'API Test Notification',
            'message': 'Test message from API',
            'scheduled_at': scheduled_at.isoformat(),
            'type': 'system',
            'priority': 'high',
        }

        response = client.post('/api/notifications/schedule/', data, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['notification_ids']), 2)

    def test_cancel_scheduled_notification_endpoint(self):
        """Test DELETE /api/notifications/{id}/cancel_scheduled/"""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user1)

        # First schedule a notification
        scheduler = NotificationScheduler()
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]

        # Cancel it via API
        response = client.delete(f'/api/notifications/{notification_id}/cancel_scheduled/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['notification_id'], notification_id)

    def test_get_schedule_status_endpoint(self):
        """Test GET /api/notifications/{id}/schedule_status/"""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user1)

        # First schedule a notification
        scheduler = NotificationScheduler()
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = scheduler.schedule_notification(
            recipients=[self.user1.id],
            title='Test Notification',
            message='Test message',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]

        # Get status via API
        response = client.get(f'/api/notifications/{notification_id}/schedule_status/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], notification_id)
        self.assertEqual(response.data['scheduled_status'], 'pending')


class NotificationRetryLogicTestCase(TestCase):
    """Test retry logic and backoff"""

    def setUp(self):
        """Set up test data"""
        self.scheduler = NotificationScheduler()
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123'
        )

    def test_exponential_backoff_calculation(self):
        """Test that retry delays increase exponentially"""
        scheduled_at = timezone.now() + timedelta(hours=1)

        created_ids = self.scheduler.schedule_notification(
            recipients=[self.user.id],
            title='Test',
            message='Test',
            scheduled_at=scheduled_at,
        )

        notification_id = created_ids[0]

        # First retry - 5 minutes
        self.scheduler.retry_failed_notification(notification_id, retry_delay_minutes=5)
        notif1 = Notification.objects.get(id=notification_id)
        time1 = notif1.scheduled_at

        # Second retry - 10 minutes
        self.scheduler.retry_failed_notification(notification_id, retry_delay_minutes=10)
        notif2 = Notification.objects.get(id=notification_id)
        time2 = notif2.scheduled_at

        # Verify second retry is later
        self.assertGreater(time2, time1)
