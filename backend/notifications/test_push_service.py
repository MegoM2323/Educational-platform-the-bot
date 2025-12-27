"""
Tests for push notification service.

Tests Firebase push notification delivery, device token management,
batch delivery, and rate limiting.
"""

import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase, override_settings
from django.core.cache import cache

from notifications.models import Notification, PushDeliveryLog
from notifications.channels.models import DeviceToken
from notifications.push_service import (
    PushNotificationService,
    get_push_service
)
from notifications.batch_push_service import (
    BatchPushNotificationService,
    get_batch_push_service
)

User = get_user_model()


class PushNotificationServiceTests(TestCase):
    """Tests for PushNotificationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.notification = Notification.objects.create(
            title='Test Notification',
            message='Test message',
            recipient=self.user,
            type=Notification.Type.SYSTEM,
            priority=Notification.Priority.NORMAL
        )
        self.service = PushNotificationService()
        cache.clear()

    def test_service_initialization(self):
        """Test service initialization."""
        self.assertIsNotNone(self.service.firebase_channel)
        self.assertGreater(self.service.rate_limit, 0)
        self.assertGreater(self.service.batch_size, 0)

    def test_get_push_service_singleton(self):
        """Test singleton pattern for push service."""
        service1 = get_push_service()
        service2 = get_push_service()
        self.assertIs(service1, service2)

    def test_register_device_token(self):
        """Test device token registration."""
        token = 'test_fcm_token_123'
        device, created = self.service.register_device_token(
            self.user,
            token,
            'ios',
            'iPhone 12'
        )

        self.assertTrue(created)
        self.assertEqual(device.user, self.user)
        self.assertEqual(device.token, token)
        self.assertEqual(device.device_type, 'ios')
        self.assertEqual(device.device_name, 'iPhone 12')
        self.assertTrue(device.is_active)

    def test_register_device_token_update(self):
        """Test updating existing device token."""
        token = 'test_token_456'
        device1, created1 = self.service.register_device_token(
            self.user,
            token,
            'android'
        )
        self.assertTrue(created1)

        device2, created2 = self.service.register_device_token(
            self.user,
            token,
            'web',
            'Chrome Browser'
        )

        self.assertFalse(created2)
        self.assertEqual(device1.id, device2.id)
        self.assertEqual(device2.device_type, 'web')
        self.assertEqual(device2.device_name, 'Chrome Browser')

    def test_revoke_device_token(self):
        """Test revoking device token."""
        token = 'token_to_revoke'
        self.service.register_device_token(
            self.user,
            token,
            'ios'
        )

        revoked = self.service.revoke_device_token(self.user, token)
        self.assertTrue(revoked)

        device = DeviceToken.objects.get(token=token)
        self.assertFalse(device.is_active)

    def test_get_user_devices(self):
        """Test getting user's registered devices."""
        self.service.register_device_token(
            self.user,
            'token1',
            'ios',
            'iPhone'
        )
        self.service.register_device_token(
            self.user,
            'token2',
            'android',
            'Pixel'
        )
        self.service.register_device_token(
            self.user,
            'token3',
            'web',
            'Chrome'
        )

        devices = self.service.get_user_devices(self.user)

        self.assertEqual(len(devices), 3)
        self.assertTrue(all(d['is_active'] for d in devices))
        device_types = {d['device_type'] for d in devices}
        self.assertEqual(device_types, {'ios', 'android', 'web'})

    def test_cleanup_expired_tokens(self):
        """Test cleanup of expired device tokens."""
        # Register active token
        self.service.register_device_token(self.user, 'active_token', 'ios')

        # Create old token never used
        old_unused = DeviceToken.objects.create(
            user=self.user,
            token='old_unused_token',
            device_type='android',
            is_active=True,
            created_at=timezone.now() - timedelta(days=35)
        )

        # Create stale token (not used in 90+ days)
        stale = DeviceToken.objects.create(
            user=self.user,
            token='stale_token',
            device_type='web',
            is_active=True,
            last_used_at=timezone.now() - timedelta(days=91)
        )

        result = self.service.cleanup_expired_tokens()

        self.assertGreaterEqual(result['inactive_tokens'], 1)
        self.assertGreaterEqual(result['stale_tokens'], 1)

        # Check tokens are marked inactive
        old_unused.refresh_from_db()
        stale.refresh_from_db()
        self.assertFalse(old_unused.is_active)
        self.assertFalse(stale.is_active)

    def test_get_push_stats_all_users(self):
        """Test getting push statistics for all users."""
        # Register devices for multiple users
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass'
        )

        self.service.register_device_token(self.user, 'token1', 'ios')
        self.service.register_device_token(self.user, 'token2', 'android')
        self.service.register_device_token(user2, 'token3', 'web')

        stats = self.service.get_push_stats()

        self.assertEqual(stats['total_devices'], 3)
        self.assertEqual(stats['active_devices'], 3)
        self.assertEqual(stats['inactive_devices'], 0)
        self.assertIn('ios', stats['by_device_type'])
        self.assertIn('android', stats['by_device_type'])
        self.assertIn('web', stats['by_device_type'])

    def test_get_push_stats_per_user(self):
        """Test getting push statistics for specific user."""
        self.service.register_device_token(self.user, 'token1', 'ios')
        self.service.register_device_token(self.user, 'token2', 'android')

        user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass'
        )
        self.service.register_device_token(user2, 'token3', 'web')

        stats = self.service.get_push_stats(self.user)

        self.assertEqual(stats['total_devices'], 2)
        self.assertEqual(stats['active_devices'], 2)
        self.assertIn('ios', stats['by_device_type'])
        self.assertIn('android', stats['by_device_type'])
        self.assertNotIn('web', stats['by_device_type'])

    @patch('notifications.push_service.FirebasePushChannel.send')
    def test_send_to_user_single_device(self, mock_send):
        """Test sending to user with single device."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0
        }

        self.service.register_device_token(self.user, 'token1', 'ios')

        result = self.service.send_to_user(self.notification, self.user)

        self.assertEqual(result['status'], 'sent')
        self.assertEqual(result['total_devices'], 1)

    @patch('notifications.push_service.FirebasePushChannel.send')
    def test_send_to_user_multiple_devices(self, mock_send):
        """Test sending to user with multiple devices."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0
        }

        self.service.register_device_token(self.user, 'token1', 'ios')
        self.service.register_device_token(self.user, 'token2', 'android')

        result = self.service.send_to_user(self.notification, self.user)

        self.assertEqual(result['status'], 'sent')
        self.assertEqual(result['total_devices'], 2)

    def test_send_to_user_no_devices(self):
        """Test sending to user with no devices."""
        result = self.service.send_to_user(self.notification, self.user)

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['total_devices'], 0)

    def test_send_to_user_filter_device_types(self):
        """Test sending to specific device types only."""
        self.service.register_device_token(self.user, 'token1', 'ios')
        self.service.register_device_token(self.user, 'token2', 'android')
        self.service.register_device_token(self.user, 'token3', 'web')

        # Get devices for iOS only
        devices = self.service._get_user_device_tokens(
            self.user,
            ['ios']
        )

        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0][2], 'ios')

    def test_rate_limit_check(self):
        """Test rate limiting for push notifications."""
        # First call should pass
        result1 = self.service._check_rate_limit(self.user)
        self.assertTrue(result1)

        # Simulate exceeding rate limit
        cache_key = f'push_notifications_sent_{self.user.id}'
        cache.set(cache_key, self.service.rate_limit, 60)

        # Next call should fail
        result2 = self.service._check_rate_limit(self.user)
        self.assertFalse(result2)

    @patch('notifications.push_service.FirebasePushChannel.send')
    def test_send_to_multiple_users(self, mock_send):
        """Test sending to multiple users."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0
        }

        user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass'
        )

        self.service.register_device_token(self.user, 'token1', 'ios')
        self.service.register_device_token(user2, 'token2', 'android')

        users = [self.user, user2]
        result = self.service.send_to_users(self.notification, users)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_users'], 2)
        self.assertEqual(result['users_sent'], 2)


class BatchPushNotificationServiceTests(TestCase):
    """Tests for BatchPushNotificationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                email=f'user{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)

        self.notification = Notification.objects.create(
            title='Batch Test',
            message='Batch message',
            recipient=self.users[0],
            type=Notification.Type.SYSTEM
        )

        self.service = BatchPushNotificationService()
        cache.clear()

    def test_batch_service_initialization(self):
        """Test batch service initialization."""
        self.assertIsNotNone(self.service.push_service)
        self.assertGreater(self.service.batch_size, 0)

    def test_get_batch_service_singleton(self):
        """Test singleton pattern for batch service."""
        service1 = get_batch_push_service()
        service2 = get_batch_push_service()
        self.assertIs(service1, service2)

    @patch('notifications.batch_push_service.PushNotificationService.send_to_user')
    def test_send_to_users_empty_list(self, mock_send):
        """Test sending to empty user list."""
        result = self.service.send_to_users(self.notification, [])

        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['total_users'], 0)
        mock_send.assert_not_called()

    @patch('notifications.batch_push_service.PushNotificationService.send_to_user')
    def test_send_to_users_single_batch(self, mock_send):
        """Test sending to users in single batch."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0,
            'total_devices': 1
        }

        result = self.service.send_to_users(
            self.notification,
            self.users[:5]
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_users'], 5)
        self.assertEqual(result['total_batches'], 1)
        self.assertEqual(mock_send.call_count, 5)

    @patch('notifications.batch_push_service.PushNotificationService.send_to_user')
    def test_send_to_users_multiple_batches(self, mock_send):
        """Test sending to users in multiple batches."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0,
            'total_devices': 1
        }

        # Override batch size for testing
        self.service.batch_size = 3

        result = self.service.send_to_users(
            self.notification,
            self.users
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_users'], 10)
        self.assertEqual(result['total_batches'], 4)
        self.assertEqual(mock_send.call_count, 10)

    @patch('notifications.batch_push_service.PushNotificationService.send_to_user')
    def test_send_to_users_partial_failure(self, mock_send):
        """Test handling partial failures in batch."""
        # First 7 succeed, last 3 fail
        def send_side_effect(*args, **kwargs):
            call_count = mock_send.call_count
            if call_count <= 7:
                return {
                    'status': 'sent',
                    'sent_count': 1,
                    'failed_count': 0,
                    'total_devices': 1
                }
            else:
                return {
                    'status': 'failed',
                    'sent_count': 0,
                    'failed_count': 1,
                    'total_devices': 1
                }

        mock_send.side_effect = send_side_effect

        result = self.service.send_to_users(
            self.notification,
            self.users
        )

        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['devices_sent'], 7)
        self.assertEqual(result['devices_failed'], 3)

    @patch('notifications.batch_push_service.PushNotificationService.send_to_user')
    def test_send_to_user_list_by_ids(self, mock_send):
        """Test sending to users by ID list."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0,
            'total_devices': 1
        }

        user_ids = [u.id for u in self.users[:5]]
        result = self.service.send_to_user_list(self.notification, user_ids)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_users'], 5)

    @patch('notifications.batch_push_service.PushNotificationService.send_to_user')
    def test_send_to_query(self, mock_send):
        """Test sending to users via queryset."""
        mock_send.return_value = {
            'status': 'sent',
            'sent_count': 1,
            'failed_count': 0,
            'total_devices': 1
        }

        query = User.objects.filter(id__in=[u.id for u in self.users[:5]])
        result = self.service.send_to_query(self.notification, query)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_users'], 5)

    def test_batch_rate_limit(self):
        """Test rate limiting for batch operations."""
        # First batch should pass
        result = self.service._check_batch_rate_limit(50)
        self.assertTrue(result)

        # Set cache to near limit
        cache_key = 'batch_push_notifications_sent'
        cache.set(cache_key, self.service.rate_limit - 10, 60)

        # Large batch should fail
        result = self.service._check_batch_rate_limit(50)
        self.assertFalse(result)

    def test_get_batch_stats(self):
        """Test getting batch operation statistics."""
        # Create some delivery logs
        for i in range(5):
            PushDeliveryLog.objects.create(
                notification=self.notification,
                user=self.users[i],
                status=PushDeliveryLog.DeliveryStatus.SENT,
                success=True
            )

        stats = self.service.get_batch_stats()

        self.assertEqual(stats['total_logs'], 5)
        self.assertEqual(stats['total_success'], 5)
        self.assertEqual(stats['total_failed'], 0)
        self.assertEqual(stats['success_rate'], 100.0)

    def test_batch_stats_with_failures(self):
        """Test batch stats with mixed success/failure."""
        for i in range(5):
            PushDeliveryLog.objects.create(
                notification=self.notification,
                user=self.users[i],
                status=PushDeliveryLog.DeliveryStatus.SENT,
                success=True
            )

        for i in range(5, 8):
            PushDeliveryLog.objects.create(
                notification=self.notification,
                user=self.users[i],
                status=PushDeliveryLog.DeliveryStatus.FAILED,
                success=False,
                error_message='Test error'
            )

        stats = self.service.get_batch_stats()

        self.assertEqual(stats['total_logs'], 8)
        self.assertEqual(stats['total_success'], 5)
        self.assertEqual(stats['total_failed'], 3)
        self.assertAlmostEqual(stats['success_rate'], 62.5, places=1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
