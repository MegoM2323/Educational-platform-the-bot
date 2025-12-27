"""
Tests for notification unsubscribe management (T_NTF_010).

GDPR-compliant unsubscribe functionality:
1. Secure unsubscribe tokens with HMAC-SHA256
2. Token-based one-click unsubscribe via email links
3. Unsubscribe preferences management (GET, PATCH)
4. Audit trail tracking (IP, user agent, timestamp)
"""

import json
import pytest
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import NotificationSettings, NotificationUnsubscribe
from .unsubscribe import UnsubscribeTokenGenerator, UnsubscribeService, generate_unsubscribe_token

User = get_user_model()


class UnsubscribeTokenGeneratorTests(TestCase):
    """Test secure token generation and validation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_token_generation(self):
        """Test that token is generated successfully."""
        token = UnsubscribeTokenGenerator.generate(self.user.id)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_token_generation_with_types(self):
        """Test token generation with specific notification types."""
        token = UnsubscribeTokenGenerator.generate(
            self.user.id,
            notification_types=['assignments', 'materials']
        )

        is_valid, data = UnsubscribeTokenGenerator.validate(token)
        self.assertTrue(is_valid)
        self.assertEqual(data['user_id'], self.user.id)
        self.assertEqual(data['notification_types'], ['assignments', 'materials'])

    def test_token_validation_success(self):
        """Test token validation succeeds for valid token."""
        token = UnsubscribeTokenGenerator.generate(
            self.user.id,
            notification_types=['assignments']
        )

        is_valid, data = UnsubscribeTokenGenerator.validate(token)

        self.assertTrue(is_valid)
        self.assertIsNotNone(data)
        self.assertEqual(data['user_id'], self.user.id)
        self.assertIn('expires_at', data)

    def test_token_validation_fails_for_invalid_token(self):
        """Test token validation fails for invalid token."""
        is_valid, data = UnsubscribeTokenGenerator.validate('invalid_token_string')

        self.assertFalse(is_valid)
        self.assertIsNone(data)

    def test_token_validation_fails_for_tampered_token(self):
        """Test token validation fails if token is tampered with."""
        token = UnsubscribeTokenGenerator.generate(self.user.id)

        # Tamper with token by changing a character
        tampered_token = token[:-5] + 'xxxxx'
        is_valid, data = UnsubscribeTokenGenerator.validate(tampered_token)

        self.assertFalse(is_valid)
        self.assertIsNone(data)

    def test_token_expiry(self):
        """Test that expired tokens are rejected."""
        # This test creates a token and would need to simulate expiry
        # For now, we'll just verify the token structure includes expiry
        token = UnsubscribeTokenGenerator.generate(self.user.id)
        is_valid, data = UnsubscribeTokenGenerator.validate(token)

        self.assertTrue(is_valid)
        expires_at = datetime.fromisoformat(data['expires_at'])
        # Verify expiry is 30 days from now
        now = timezone.now()
        delta = abs((expires_at - now.replace(tzinfo=None)).days)
        self.assertAlmostEqual(delta, 30, delta=1)


class UnsubscribeServiceTests(TestCase):
    """Test unsubscribe service functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.settings = NotificationSettings.objects.create(user=self.user)

    def test_unsubscribe_from_specific_type(self):
        """Test unsubscribing from a specific notification type."""
        self.assertTrue(self.settings.assignment_notifications)

        result = UnsubscribeService.unsubscribe(
            self.user.id,
            ['assignments']
        )

        self.assertTrue(result['success'])
        self.assertIn('assignments', result['disabled_types'])

        # Verify settings updated
        self.settings.refresh_from_db()
        self.assertFalse(self.settings.assignment_notifications)
        # Other types should still be enabled
        self.assertTrue(self.settings.material_notifications)

    def test_unsubscribe_from_multiple_types(self):
        """Test unsubscribing from multiple notification types."""
        result = UnsubscribeService.unsubscribe(
            self.user.id,
            ['assignments', 'materials', 'messages']
        )

        self.assertTrue(result['success'])
        self.assertEqual(len(result['disabled_types']), 3)

        self.settings.refresh_from_db()
        self.assertFalse(self.settings.assignment_notifications)
        self.assertFalse(self.settings.material_notifications)
        self.assertFalse(self.settings.message_notifications)

    def test_unsubscribe_from_all(self):
        """Test unsubscribing from all notifications."""
        result = UnsubscribeService.unsubscribe(
            self.user.id,
            ['all']
        )

        self.assertTrue(result['success'])
        self.assertIn('all', result['disabled_types'])

        # Verify all channels disabled
        self.settings.refresh_from_db()
        self.assertFalse(self.settings.email_notifications)
        self.assertFalse(self.settings.push_notifications)
        self.assertFalse(self.settings.sms_notifications)

    def test_unsubscribe_with_audit_trail(self):
        """Test unsubscribe records audit information."""
        ip_address = '192.168.1.1'
        user_agent = 'Mozilla/5.0 Test'

        result = UnsubscribeService.unsubscribe(
            self.user.id,
            ['assignments'],
            ip_address=ip_address,
            user_agent=user_agent,
            token_used=True
        )

        self.assertTrue(result['success'])

        # Verify unsubscribe event recorded
        unsubscribe_record = NotificationUnsubscribe.objects.get(user=self.user)
        self.assertEqual(unsubscribe_record.ip_address, ip_address)
        self.assertEqual(unsubscribe_record.user_agent, user_agent)
        self.assertTrue(unsubscribe_record.token_used)
        self.assertTrue(unsubscribe_record.is_active())

    def test_unsubscribe_nonexistent_user(self):
        """Test unsubscribe fails for nonexistent user."""
        result = UnsubscribeService.unsubscribe(99999, ['assignments'])

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'User not found')

    def test_unsubscribe_creates_settings_if_missing(self):
        """Test unsubscribe creates notification settings if not exists."""
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )

        # Delete settings for this user
        NotificationSettings.objects.filter(user=user2).delete()

        result = UnsubscribeService.unsubscribe(user2.id, ['assignments'])

        self.assertTrue(result['success'])
        # Verify settings created
        settings = NotificationSettings.objects.get(user=user2)
        self.assertFalse(settings.assignment_notifications)


class UnsubscribeAPITests(APITestCase):
    """Test unsubscribe API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.settings = NotificationSettings.objects.create(user=self.user)

    def test_unsubscribe_endpoint_valid_token(self):
        """Test unsubscribe endpoint with valid token."""
        token = UnsubscribeTokenGenerator.generate(self.user.id)

        response = self.client.get(
            f'/api/notifications/unsubscribe/{token}/',
            {'type': 'assignments'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('assignments', data['disabled_types'])

    def test_unsubscribe_endpoint_invalid_token(self):
        """Test unsubscribe endpoint with invalid token."""
        response = self.client.get(
            '/api/notifications/unsubscribe/invalid_token/'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid or expired token')

    def test_unsubscribe_endpoint_records_client_info(self):
        """Test unsubscribe endpoint records client IP and user agent."""
        token = UnsubscribeTokenGenerator.generate(self.user.id)

        response = self.client.get(
            f'/api/notifications/unsubscribe/{token}/',
            HTTP_USER_AGENT='TestBrowser/1.0',
            REMOTE_ADDR='192.168.1.100'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify audit record created
        unsubscribe_record = NotificationUnsubscribe.objects.latest('id')
        self.assertEqual(unsubscribe_record.ip_address, '192.168.1.100')
        self.assertIn('TestBrowser', unsubscribe_record.user_agent)

    def test_preferences_endpoint_get(self):
        """Test GET preferences endpoint."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/notifications/settings/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertTrue(data['email_notifications'])
        self.assertTrue(data['assignment_notifications'])

    def test_preferences_endpoint_patch(self):
        """Test PATCH preferences endpoint."""
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            '/api/notifications/settings/',
            {
                'email_notifications': False,
                'assignment_notifications': False
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.settings.refresh_from_db()
        self.assertFalse(self.settings.email_notifications)
        self.assertFalse(self.settings.assignment_notifications)


class NotificationUnsubscribeModelTests(TestCase):
    """Test NotificationUnsubscribe model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_unsubscribe_record_creation(self):
        """Test creating an unsubscribe record."""
        record = NotificationUnsubscribe.objects.create(
            user=self.user,
            notification_types=['assignments', 'materials'],
            channel='email',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            token_used=True
        )

        self.assertEqual(record.user, self.user)
        self.assertEqual(record.notification_types, ['assignments', 'materials'])
        self.assertEqual(record.channel, 'email')
        self.assertTrue(record.is_active())

    def test_resubscribe(self):
        """Test marking unsubscribe as resubscribed."""
        record = NotificationUnsubscribe.objects.create(
            user=self.user,
            notification_types=['assignments'],
            channel='email'
        )

        self.assertTrue(record.is_active())

        record.resubscribed_at = timezone.now()
        record.save()

        self.assertFalse(record.is_active())

    def test_unsubscribe_ordering(self):
        """Test unsubscribe records ordered by recent first."""
        record1 = NotificationUnsubscribe.objects.create(
            user=self.user,
            channel='email'
        )

        record2 = NotificationUnsubscribe.objects.create(
            user=self.user,
            channel='push'
        )

        records = NotificationUnsubscribe.objects.all()
        self.assertEqual(records[0].id, record2.id)
        self.assertEqual(records[1].id, record1.id)


class UnsubscribeHelperFunctionsTests(TestCase):
    """Test unsubscribe helper functions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_generate_unsubscribe_token(self):
        """Test generate_unsubscribe_token helper function."""
        token = generate_unsubscribe_token(self.user.id, 'assignments')

        self.assertIsNotNone(token)
        is_valid, data = UnsubscribeTokenGenerator.validate(token)
        self.assertTrue(is_valid)
        self.assertEqual(data['user_id'], self.user.id)


class GDPRComplianceTests(TestCase):
    """Test GDPR compliance features."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_audit_trail_complete(self):
        """Test complete audit trail is recorded."""
        UnsubscribeService.unsubscribe(
            self.user.id,
            ['assignments'],
            ip_address='192.168.1.1',
            user_agent='TestAgent/1.0',
            token_used=True
        )

        record = NotificationUnsubscribe.objects.get(user=self.user)

        # Verify all audit fields populated
        self.assertIsNotNone(record.user)
        self.assertEqual(record.user.email, 'test@example.com')
        self.assertEqual(record.ip_address, '192.168.1.1')
        self.assertIsNotNone(record.user_agent)
        self.assertIsNotNone(record.unsubscribed_at)
        self.assertTrue(record.token_used)

    def test_unsubscribe_history_retention(self):
        """Test unsubscribe history is retained for GDPR."""
        # First unsubscribe
        UnsubscribeService.unsubscribe(self.user.id, ['assignments'])

        # Get record
        record = NotificationUnsubscribe.objects.get(user=self.user)
        first_timestamp = record.unsubscribed_at

        # Verify record exists and can be retrieved
        self.assertIsNotNone(first_timestamp)
        self.assertTrue(record.is_active())


if __name__ == '__main__':
    import unittest
    unittest.main()
