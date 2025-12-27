"""
Tests for SMS Notification Service with queuing and retry logic.

Tests cover:
- SMS message validation and character limit handling
- Recipient validation for SMS
- Rate limiting per user
- Async SMS queuing via Celery
- Retry logic with exponential backoff
- Delivery status tracking
- SMS statistics
"""

from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from notifications.channels.sms import SMSChannel, SMSProviderError
from notifications.models import Notification, NotificationQueue, NotificationSettings
from notifications.services.sms_service import (
    SMSNotificationService,
    SMSValidationError,
    SMSQueueError,
)

User = get_user_model()


class TestSMSNotificationService(TestCase):
    """Tests for SMSNotificationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = SMSNotificationService()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            phone_number='+79991234567'
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            type=Notification.Type.MESSAGE_NEW,
            title='Test SMS',
            message='This is a test SMS message',
        )

    def test_service_initialization(self):
        """Test SMS service initialization."""
        self.assertIsNotNone(self.service.sms_channel)
        self.assertEqual(self.service.SMS_CHAR_LIMIT, 160)
        self.assertEqual(self.service.RATE_LIMIT_PER_HOUR, 10)
        self.assertEqual(self.service.MAX_RETRIES, 3)

    # ========== MESSAGE VALIDATION TESTS ==========

    def test_validate_message_valid(self):
        """Test validation of valid SMS message."""
        message = "This is a valid message"
        self.assertTrue(self.service.validate_sms_message(message))

    def test_validate_message_empty(self):
        """Test validation fails for empty message."""
        with self.assertRaises(SMSValidationError):
            self.service.validate_sms_message("")

    def test_validate_message_none(self):
        """Test validation fails for None message."""
        with self.assertRaises(SMSValidationError):
            self.service.validate_sms_message(None)

    def test_validate_message_non_string(self):
        """Test validation fails for non-string message."""
        with self.assertRaises(SMSValidationError):
            self.service.validate_sms_message(123)

    def test_validate_message_exceeds_max_length(self):
        """Test validation fails for message exceeding max length."""
        # SMS_CHAR_LIMIT * 3 = 480 chars max, so 481+ should fail
        long_message = "x" * (self.service.SMS_CHAR_LIMIT * 3 + 1)
        with self.assertRaises(SMSValidationError):
            self.service.validate_sms_message(long_message)

    def test_validate_message_at_max_length(self):
        """Test validation succeeds at max length."""
        max_message = "x" * (self.service.SMS_CHAR_LIMIT * 3)
        self.assertTrue(self.service.validate_sms_message(max_message))

    # ========== RECIPIENT VALIDATION TESTS ==========

    def test_validate_recipient_valid(self):
        """Test validation of valid recipient."""
        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            self.assertTrue(self.service.validate_recipient(self.user))

    def test_validate_recipient_invalid_user(self):
        """Test validation fails for None user."""
        with self.assertRaises(SMSValidationError):
            self.service.validate_recipient(None)

    def test_validate_recipient_sms_disabled(self):
        """Test validation fails when SMS disabled for user."""
        # Create notification settings with SMS disabled
        NotificationSettings.objects.create(
            user=self.user,
            sms_notifications=False
        )

        with self.assertRaises(SMSValidationError):
            self.service.validate_recipient(self.user)

    def test_validate_recipient_no_phone(self):
        """Test validation fails when user has no phone number."""
        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=False):
            with self.assertRaises(SMSValidationError):
                self.service.validate_recipient(self.user)

    # ========== RATE LIMITING TESTS ==========

    def test_rate_limit_within_limit(self):
        """Test rate limit check when within limit."""
        self.assertTrue(self.service.check_rate_limit(self.user))

    def test_rate_limit_exceeded(self):
        """Test rate limit check when limit exceeded."""
        # Create 10 SMS in the last hour (at limit)
        one_hour_ago = timezone.now() - timedelta(minutes=30)
        for i in range(10):
            NotificationQueue.objects.create(
                notification=self.notification,
                channel='sms',
                status=NotificationQueue.Status.SENT,
                created_at=one_hour_ago + timedelta(minutes=i)
            )

        # 11th SMS should fail
        self.assertFalse(self.service.check_rate_limit(self.user))

    def test_rate_limit_outside_window(self):
        """Test rate limit check for SMS outside the hour window."""
        # Create 10 SMS older than 1 hour ago
        two_hours_ago = timezone.now() - timedelta(hours=2)
        for i in range(10):
            NotificationQueue.objects.create(
                notification=self.notification,
                channel='sms',
                status=NotificationQueue.Status.SENT,
                created_at=two_hours_ago
            )

        # Should be within limit since they're outside the hour window
        self.assertTrue(self.service.check_rate_limit(self.user))

    # ========== SMS QUEUING TESTS ==========

    def test_queue_sms_success(self):
        """Test successful SMS queuing."""
        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            queue_entry = self.service.queue_sms(self.notification, self.user)

        self.assertIsNotNone(queue_entry.id)
        self.assertEqual(queue_entry.channel, 'sms')
        self.assertEqual(queue_entry.status, NotificationQueue.Status.PENDING)
        self.assertEqual(queue_entry.max_attempts, self.service.MAX_RETRIES)

    def test_queue_sms_invalid_message(self):
        """Test SMS queuing fails with invalid message."""
        invalid_notification = Notification.objects.create(
            recipient=self.user,
            type=Notification.Type.MESSAGE_NEW,
            title='Test',
            message="",  # Empty message
        )

        with self.assertRaises(SMSValidationError):
            self.service.queue_sms(invalid_notification, self.user)

    def test_queue_sms_invalid_recipient(self):
        """Test SMS queuing fails with invalid recipient."""
        with self.assertRaises(SMSValidationError):
            self.service.queue_sms(self.notification, None)

    def test_queue_sms_rate_limit_exceeded(self):
        """Test SMS queuing fails when rate limit exceeded."""
        # Create SMS entries at limit
        one_hour_ago = timezone.now() - timedelta(minutes=30)
        for i in range(10):
            NotificationQueue.objects.create(
                notification=self.notification,
                channel='sms',
                status=NotificationQueue.Status.SENT,
                created_at=one_hour_ago + timedelta(minutes=i)
            )

        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            with self.assertRaises(SMSQueueError):
                self.service.queue_sms(self.notification, self.user)

    def test_queue_sms_with_scheduled_time(self):
        """Test SMS queuing with scheduled delivery time."""
        scheduled_time = timezone.now() + timedelta(hours=1)

        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            queue_entry = self.service.queue_sms(
                self.notification,
                self.user,
                scheduled_at=scheduled_time
            )

        self.assertEqual(queue_entry.scheduled_at, scheduled_time)

    # ========== ASYNC SEND TESTS ==========

    @patch('notifications.services.sms_service.send_sms_task')
    def test_send_sms_async(self, mock_send_task):
        """Test async SMS sending."""
        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            result = self.service.send_sms_async(self.notification, self.user)

        self.assertEqual(result['status'], 'queued')
        self.assertIn('queue_id', result)
        mock_send_task.delay.assert_called_once()

    @patch('notifications.services.sms_service.send_sms_task')
    def test_send_sms_async_invalid_message(self, mock_send_task):
        """Test async SMS fails with invalid message."""
        invalid_notification = Notification.objects.create(
            recipient=self.user,
            type=Notification.Type.MESSAGE_NEW,
            title='Test',
            message=""  # Empty message
        )

        result = self.service.send_sms_async(invalid_notification, self.user)

        self.assertEqual(result['status'], 'skipped')
        self.assertIn('reason', result)
        mock_send_task.delay.assert_not_called()

    @patch('notifications.services.sms_service.send_sms_task')
    def test_send_sms_async_rate_limit(self, mock_send_task):
        """Test async SMS fails with rate limit exceeded."""
        # Create SMS at limit
        one_hour_ago = timezone.now() - timedelta(minutes=30)
        for i in range(10):
            NotificationQueue.objects.create(
                notification=self.notification,
                channel='sms',
                status=NotificationQueue.Status.SENT,
                created_at=one_hour_ago + timedelta(minutes=i)
            )

        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            result = self.service.send_sms_async(self.notification, self.user)

        self.assertEqual(result['status'], 'skipped')
        mock_send_task.delay.assert_not_called()

    # ========== SYNC SEND TESTS ==========

    @patch.object(SMSChannel, 'send')
    def test_send_sms_now_success(self, mock_send):
        """Test successful sync SMS sending."""
        mock_send.return_value = {
            'status': 'sent',
            'message_length': 25,
            'provider_message_id': 'msg_123'
        }

        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            result = self.service.send_sms_now(self.notification, self.user)

        self.assertEqual(result['status'], 'sent')
        self.assertEqual(result['message_length'], 25)
        mock_send.assert_called_once_with(self.notification, self.user)

    @patch.object(SMSChannel, 'send')
    @patch('notifications.services.sms_service.send_sms_task')
    def test_send_sms_now_fallback_to_queue(self, mock_send_task, mock_send):
        """Test sync SMS falls back to queue on failure."""
        mock_send.side_effect = SMSProviderError("Network error")

        with patch.object(self.service.sms_channel, 'validate_recipient', return_value=True):
            result = self.service.send_sms_now(self.notification, self.user)

        self.assertEqual(result['status'], 'queued_fallback')
        self.assertIn('queue_id', result)
        mock_send_task.delay.assert_called_once()

    @patch.object(SMSChannel, 'send')
    def test_send_sms_now_invalid_message(self, mock_send):
        """Test sync SMS fails with invalid message."""
        invalid_notification = Notification.objects.create(
            recipient=self.user,
            type=Notification.Type.MESSAGE_NEW,
            title='Test',
            message=""
        )

        with self.assertRaises(SMSValidationError):
            self.service.send_sms_now(invalid_notification, self.user)

        mock_send.assert_not_called()

    # ========== RETRY TESTS ==========

    def test_retry_failed_sms_success(self):
        """Test successful retry of failed SMS."""
        queue_entry = NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.FAILED,
            attempts=1,
            max_attempts=3,
            error_message='Network error'
        )

        with patch('notifications.services.sms_service.send_sms_task'):
            success = self.service.retry_failed_sms(queue_entry.id)

        self.assertTrue(success)

        # Verify entry was updated
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, NotificationQueue.Status.PENDING)
        self.assertIsNotNone(queue_entry.scheduled_at)

    def test_retry_failed_sms_max_attempts_exceeded(self):
        """Test retry fails when max attempts exceeded."""
        queue_entry = NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.FAILED,
            attempts=3,
            max_attempts=3,
            error_message='Network error'
        )

        success = self.service.retry_failed_sms(queue_entry.id)

        self.assertFalse(success)

        # Verify entry status not changed
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, NotificationQueue.Status.FAILED)

    def test_retry_failed_sms_not_found(self):
        """Test retry fails when queue entry not found."""
        success = self.service.retry_failed_sms(999)
        self.assertFalse(success)

    def test_retry_exponential_backoff(self):
        """Test retry uses exponential backoff."""
        queue_entry = NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.FAILED,
            attempts=1,
            max_attempts=3,
        )

        before_scheduled = timezone.now()

        with patch('notifications.services.sms_service.send_sms_task'):
            self.service.retry_failed_sms(queue_entry.id)

        queue_entry.refresh_from_db()

        # Check that retry is scheduled with exponential backoff
        # Expected delay: 300 * (2 ^ 1) = 600 seconds
        time_diff = (queue_entry.scheduled_at - before_scheduled).total_seconds()
        self.assertGreater(time_diff, 500)
        self.assertLess(time_diff, 700)

    # ========== DELIVERY STATUS TESTS ==========

    def test_get_delivery_status_found(self):
        """Test getting delivery status of queued SMS."""
        queue_entry = NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.SENT,
            attempts=2,
            max_attempts=3,
        )

        status = self.service.get_sms_delivery_status(queue_entry.id)

        self.assertEqual(status['queue_id'], queue_entry.id)
        self.assertEqual(status['status'], NotificationQueue.Status.SENT)
        self.assertEqual(status['attempts'], 2)
        self.assertEqual(status['max_attempts'], 3)

    def test_get_delivery_status_not_found(self):
        """Test getting status of non-existent queue entry."""
        status = self.service.get_sms_delivery_status(999)

        self.assertEqual(status['queue_id'], 999)
        self.assertEqual(status['status'], 'not_found')

    # ========== USER STATISTICS TESTS ==========

    def test_get_user_sms_stats(self):
        """Test getting SMS statistics for user."""
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Create SMS entries
        NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.SENT,
            created_at=today + timedelta(hours=2)
        )
        NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.FAILED,
            created_at=today + timedelta(hours=3)
        )
        NotificationQueue.objects.create(
            notification=self.notification,
            channel='sms',
            status=NotificationQueue.Status.PENDING,
            created_at=today + timedelta(hours=4)
        )

        stats = self.service.get_user_sms_stats(self.user)

        self.assertEqual(stats['user_id'], self.user.id)
        self.assertEqual(stats['sent_today'], 1)
        self.assertEqual(stats['failed_today'], 1)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['rate_limit_remaining'], 9)  # 10 - 1 sent in last hour

    def test_get_user_sms_stats_rate_limit_remaining(self):
        """Test rate limit remaining calculation in stats."""
        one_hour_ago = timezone.now() - timedelta(minutes=30)

        # Create 5 SMS in last hour
        for i in range(5):
            NotificationQueue.objects.create(
                notification=self.notification,
                channel='sms',
                status=NotificationQueue.Status.SENT,
                created_at=one_hour_ago + timedelta(minutes=i)
            )

        stats = self.service.get_user_sms_stats(self.user)

        self.assertEqual(stats['sent_last_hour'], 5)
        self.assertEqual(stats['rate_limit_remaining'], 5)


@pytest.mark.django_db
class TestSMSQueueProcessing:
    """Tests for SMS queue processing and delivery."""

    def test_process_pending_sms_basic(self):
        """Test basic pending SMS processing."""
        from notifications.tasks import process_pending_sms

        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        notification = Notification.objects.create(
            recipient=user,
            type=Notification.Type.MESSAGE_NEW,
            title='Test',
            message='Test message'
        )

        # Create pending SMS scheduled for now
        queue_entry = NotificationQueue.objects.create(
            notification=notification,
            channel='sms',
            status=NotificationQueue.Status.PENDING,
            scheduled_at=timezone.now()
        )

        with patch('notifications.tasks.send_sms_task.delay'):
            result = process_pending_sms()

        assert result['processed'] >= 1
        assert 'timestamp' in result

    def test_process_pending_sms_respects_scheduled_time(self):
        """Test that process_pending_sms respects scheduled_at."""
        from notifications.tasks import process_pending_sms

        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        notification = Notification.objects.create(
            recipient=user,
            type=Notification.Type.MESSAGE_NEW,
            title='Test',
            message='Test message'
        )

        # Create pending SMS scheduled for future
        future_time = timezone.now() + timedelta(hours=1)
        NotificationQueue.objects.create(
            notification=notification,
            channel='sms',
            status=NotificationQueue.Status.PENDING,
            scheduled_at=future_time
        )

        with patch('notifications.tasks.send_sms_task.delay') as mock_delay:
            process_pending_sms()

        # Should not process SMS scheduled in future
        mock_delay.assert_not_called()
