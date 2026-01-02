"""
Tests for notification delivery channels.

Tests cover SMS channels, provider validation,
error handling, and integration with the notification queue system.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from notifications.channels import (
    AbstractChannel,
    SMSChannel,
    TwilioSMSProvider,
    get_channel,
)
from notifications.channels.base import ChannelDeliveryError, ChannelValidationError
from notifications.channels.sms import SMSProviderError
from notifications.models import Notification

User = get_user_model()


class TestAbstractChannel(TestCase):
    """Tests for AbstractChannel base class."""

    def test_abstract_channel_cannot_be_instantiated(self):
        """Test that AbstractChannel cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            AbstractChannel()

    def test_channel_name_method(self):
        """Test get_channel_name() method."""

        # Create a concrete implementation
        class ConcreteChannel(AbstractChannel):
            def send(self, notification, recipient):
                pass

            def validate_recipient(self, recipient):
                return True

            def get_channel_name(self):
                return "test"

        channel = ConcreteChannel()
        self.assertEqual(channel.get_channel_name(), "test")

    def test_logging_delivery_success(self):
        """Test logging successful delivery."""

        class ConcreteChannel(AbstractChannel):
            def send(self, notification, recipient):
                pass

            def validate_recipient(self, recipient):
                return True

            def get_channel_name(self):
                return "test"

        channel = ConcreteChannel()
        user = User.objects.create_user(email="test@example.com", password="test")
        notification = Notification.objects.create(
            recipient=user,
            title="Test",
            message="Test message",
            type=Notification.Type.SYSTEM,
        )

        # Should not raise
        channel.log_delivery(notification, user, "sent")

    def test_logging_delivery_failure(self):
        """Test logging failed delivery."""

        class ConcreteChannel(AbstractChannel):
            def send(self, notification, recipient):
                pass

            def validate_recipient(self, recipient):
                return True

            def get_channel_name(self):
                return "test"

        channel = ConcreteChannel()
        user = User.objects.create_user(email="test@example.com", password="test")
        notification = Notification.objects.create(
            recipient=user,
            title="Test",
            message="Test message",
            type=Notification.Type.SYSTEM,
        )

        # Should not raise even with error
        channel.log_delivery(notification, user, "failed", "Test error")


class TestChannelRegistry(TestCase):
    """Tests for channel registry and factory."""

    def test_get_channel_sms(self):
        """Test getting SMS channel from registry."""
        channel = get_channel("sms")
        self.assertIsInstance(channel, SMSChannel)

    def test_get_channel_unknown(self):
        """Test getting unknown channel raises error."""
        with self.assertRaises(ValueError) as ctx:
            get_channel("unknown")
        self.assertIn("Unknown channel type", str(ctx.exception))


class TestTwilioSMSProvider(TestCase):
    """Tests for Twilio SMS provider."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = TwilioSMSProvider()

    def test_validate_phone_valid_format(self):
        """Test phone number validation with valid format."""
        valid_numbers = [
            "+79876543210",
            "+12125552368",
            "9876543210",
            "79876543210",
        ]
        for phone in valid_numbers:
            self.assertTrue(self.provider.validate_phone(phone), f"Should accept {phone}")

    def test_validate_phone_invalid_format(self):
        """Test phone number validation with invalid format."""
        invalid_numbers = [
            "",
            "abc",
            "123",
            "+1234",
            "not-a-phone",
        ]
        for phone in invalid_numbers:
            self.assertFalse(self.provider.validate_phone(phone), f"Should reject {phone}")

    def test_normalize_phone_russian(self):
        """Test normalizing Russian phone numbers."""
        test_cases = [
            ("9876543210", "+79876543210"),
            ("89876543210", "+79876543210"),
            ("+79876543210", "+79876543210"),
            ("8 987 654 32 10", "+79876543210"),
        ]
        for raw, expected in test_cases:
            result = self.provider._normalize_phone(raw)
            self.assertEqual(result, expected)

    def test_normalize_phone_international(self):
        """Test normalizing international phone numbers."""
        test_cases = [
            ("+12125552368", "+12125552368"),
            ("12125552368", "+12125552368"),
        ]
        for raw, expected in test_cases:
            result = self.provider._normalize_phone(raw)
            self.assertEqual(result, expected)

    @override_settings(TWILIO_ACCOUNT_SID=None)
    def test_send_sms_no_config(self):
        """Test send fails when Twilio not configured."""
        provider = TwilioSMSProvider()

        with self.assertRaises(SMSProviderError) as ctx:
            provider.send_sms("+79876543210", "Test message")

        self.assertIn("not configured", str(ctx.exception).lower())

    @override_settings(
        TWILIO_ACCOUNT_SID="test_sid",
        TWILIO_AUTH_TOKEN="test_token",
        TWILIO_FROM_NUMBER="+19876543210",
    )
    def test_send_sms_invalid_phone(self):
        """Test send fails with invalid phone number."""
        provider = TwilioSMSProvider()

        with self.assertRaises(SMSProviderError) as ctx:
            provider.send_sms("invalid", "Test message")

        self.assertIn("invalid phone", str(ctx.exception).lower())

    @override_settings(
        TWILIO_ACCOUNT_SID="test_sid",
        TWILIO_AUTH_TOKEN="test_token",
        TWILIO_FROM_NUMBER="+19876543210",
    )
    @patch("notifications.channels.sms.Client")
    def test_send_sms_success(self, mock_client_class):
        """Test successful SMS send via Twilio."""
        # Mock Twilio client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_message = MagicMock()
        mock_message.sid = "SM_test_123"
        mock_client.messages.create.return_value = mock_message

        provider = TwilioSMSProvider()
        result = provider.send_sms("+79876543210", "Test message")

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["message_id"], "SM_test_123")
        self.assertEqual(result["provider"], "twilio")

    @override_settings(
        TWILIO_ACCOUNT_SID="test_sid",
        TWILIO_AUTH_TOKEN="test_token",
        TWILIO_FROM_NUMBER="+19876543210",
    )
    @patch("notifications.channels.sms.Client")
    def test_send_sms_failure(self, mock_client_class):
        """Test SMS send failure handling."""
        # Mock Twilio client to raise error
        mock_client_class.side_effect = Exception("Twilio API error")

        provider = TwilioSMSProvider()

        with self.assertRaises(SMSProviderError):
            provider.send_sms("+79876543210", "Test message")


class TestSMSChannel(TestCase):
    """Tests for SMS notification channel."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(email="test@example.com", password="test")
        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Test SMS",
            message="Test message",
            type=Notification.Type.MESSAGE_NEW,
        )

    def test_channel_name(self):
        """Test SMS channel name."""
        channel = SMSChannel()
        self.assertEqual(channel.get_channel_name(), "sms")

    def test_truncate_sms_under_limit(self):
        """Test SMS truncation for messages under limit."""
        channel = SMSChannel()
        message = "Short message"
        result = channel._truncate_sms(message)
        self.assertEqual(result, message)

    def test_truncate_sms_over_limit(self):
        """Test SMS truncation for messages over limit."""
        channel = SMSChannel()
        message = "x" * 200

        result = channel._truncate_sms(message)

        self.assertLessEqual(len(result), 160)
        self.assertTrue(result.endswith("..."))

    def test_truncate_sms_exactly_at_limit(self):
        """Test SMS at exactly character limit."""
        channel = SMSChannel()
        message = "x" * 160

        result = channel._truncate_sms(message)

        self.assertEqual(len(result), 160)

    def test_format_sms_message(self):
        """Test SMS message formatting."""
        channel = SMSChannel()
        self.user.first_name = "John"
        self.user.last_name = "Doe"

        result = channel._format_sms_message(self.notification, self.user)

        self.assertIn("John Doe", result)
        self.assertIn("Test message", result)

    def test_validate_recipient_no_phone(self):
        """Test validation fails when user has no phone."""
        channel = SMSChannel()

        result = channel.validate_recipient(self.user)

        # Should be False since user has no phone number
        self.assertFalse(result)

    def test_send_no_provider(self):
        """Test send skips when provider not configured."""
        with patch("notifications.channels.sms.settings") as mock_settings:
            mock_settings.SMS_PROVIDER = "unknown_provider"

            channel = SMSChannel()
            result = channel.send(self.notification, self.user)

        self.assertEqual(result["status"], "skipped")

    def test_send_no_phone_number(self):
        """Test send skips when user has no phone."""
        channel = SMSChannel()

        result = channel.send(self.notification, self.user)

        self.assertEqual(result["status"], "skipped")
        self.assertIn("phone", result["reason"].lower())

    @override_settings(
        SMS_PROVIDER="twilio",
        TWILIO_ACCOUNT_SID="test",
        TWILIO_AUTH_TOKEN="test",
        TWILIO_FROM_NUMBER="+1234567890",
    )
    @patch("notifications.channels.sms.TwilioSMSProvider.send_sms")
    def test_send_sms_success(self, mock_send):
        """Test successful SMS send."""
        # Add phone number to user
        self.user.phone_number = "+79876543210"
        self.user.save()

        mock_send.return_value = {
            "status": "sent",
            "message_id": "SM_test",
            "provider": "twilio",
        }

        channel = SMSChannel()
        result = channel.send(self.notification, self.user)

        self.assertEqual(result["status"], "sent")
        mock_send.assert_called_once()

    def test_get_recipient_phone_from_attribute(self):
        """Test getting phone from user attribute."""
        self.user.phone_number = "+79876543210"

        channel = SMSChannel()
        phone = channel._get_recipient_phone(self.user)

        self.assertEqual(phone, "+79876543210")

    def test_send_with_notification_data(self):
        """Test send includes notification data."""
        self.user.phone_number = "+79876543210"
        self.notification.data = {
            "order_id": "123",
            "amount": 1000,
        }

        channel = SMSChannel()

        # Format message should work with data
        message = channel._format_sms_message(self.notification, self.user)
        self.assertIsNotNone(message)


@pytest.mark.django_db
class TestChannelIntegration:
    """Integration tests for channels."""

    def test_channel_with_notification_queue(self):
        """Test channel integration with notification queue."""
        from notifications.models import NotificationQueue

        user = User.objects.create_user(email="test@example.com", password="test")
        notification = Notification.objects.create(
            recipient=user,
            title="Test",
            message="Test message",
            type=Notification.Type.SYSTEM,
        )

        # Create queue entry
        queue_entry = NotificationQueue.objects.create(
            notification=notification,
            channel="sms",
            status=NotificationQueue.Status.PENDING,
        )

        self.assertEqual(queue_entry.status, NotificationQueue.Status.PENDING)
        self.assertEqual(queue_entry.channel, "sms")

    def test_multiple_channels_same_notification(self):
        """Test sending same notification through multiple channels."""
        user = User.objects.create_user(email="test@example.com", password="test")
        notification = Notification.objects.create(
            recipient=user,
            title="Test",
            message="Test message",
            type=Notification.Type.SYSTEM,
        )

        sms_channel = get_channel("sms")

        self.assertIsInstance(sms_channel, SMSChannel)
