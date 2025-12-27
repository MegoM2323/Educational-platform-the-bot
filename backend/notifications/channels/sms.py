"""
SMS notification channel with provider abstraction.

Supports multiple SMS providers (Twilio, MessageBird, AWS SNS).
Uses factory pattern for provider selection.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model

from .base import AbstractChannel, ChannelValidationError, ChannelDeliveryError

User = get_user_model()
logger = logging.getLogger(__name__)


class SMSProviderError(Exception):
    """Raised when SMS provider operations fail."""
    pass


class AbstractSMSProvider(ABC):
    """Abstract base class for SMS providers."""

    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS message.

        Args:
            phone_number: Recipient phone number
            message: Message text

        Returns:
            Dictionary with send status and provider-specific data

        Raises:
            SMSProviderError: If send fails
        """
        pass

    @abstractmethod
    def validate_phone(self, phone_number: str) -> bool:
        """
        Validate phone number format for this provider.

        Args:
            phone_number: Phone number to validate

        Returns:
            True if valid, False otherwise
        """
        pass


class TwilioSMSProvider(AbstractSMSProvider):
    """
    Twilio SMS provider.

    Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
    """

    # Regex for international phone numbers
    PHONE_REGEX = re.compile(r'^\+?1?\d{9,15}$')

    def __init__(self):
        """Initialize Twilio provider."""
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_FROM_NUMBER', None)
        self.logger = logger

        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that Twilio is properly configured."""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            self.logger.warning(
                "Twilio SMS not configured. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER."
            )

    def validate_phone(self, phone_number: str) -> bool:
        """
        Validate phone number format.

        Args:
            phone_number: Phone number to validate

        Returns:
            True if phone number format is valid
        """
        if not phone_number:
            return False

        # Remove common formatting characters
        cleaned = re.sub(r'[\s\-().]', '', phone_number)

        return bool(self.PHONE_REGEX.match(cleaned))

    def _normalize_phone(self, phone_number: str) -> str:
        """
        Normalize phone number to E.164 format.

        Args:
            phone_number: Raw phone number

        Returns:
            Normalized phone number
        """
        # Remove formatting
        normalized = re.sub(r'[\s\-().]', '', phone_number)

        # Add + if missing
        if not normalized.startswith('+'):
            # Assume country code 7 if not provided (Russia/Kazakhstan)
            if len(normalized) == 10:
                normalized = '+7' + normalized[1:]
            elif len(normalized) == 11 and normalized.startswith('8'):
                normalized = '+7' + normalized[1:]
            elif not normalized.startswith('+'):
                normalized = '+' + normalized

        return normalized

    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Twilio.

        Args:
            phone_number: Recipient phone number
            message: Message text

        Returns:
            Dictionary with send status

        Raises:
            SMSProviderError: If send fails
        """
        if not self.account_sid or not self.auth_token:
            raise SMSProviderError("Twilio not configured")

        if not self.validate_phone(phone_number):
            raise SMSProviderError(f"Invalid phone number: {phone_number}")

        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)
            normalized_phone = self._normalize_phone(phone_number)

            message_obj = client.messages.create(
                body=message,
                from_=self.from_number,
                to=normalized_phone
            )

            return {
                'status': 'sent',
                'message_id': message_obj.sid,
                'provider': 'twilio',
            }

        except ImportError:
            raise SMSProviderError("Twilio library not installed")
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Twilio send failed: {error_msg}")
            raise SMSProviderError(f"Send failed: {error_msg}")


class MessageBirdSMSProvider(AbstractSMSProvider):
    """
    MessageBird SMS provider.

    Requires: MESSAGEBIRD_API_KEY
    """

    def __init__(self):
        """Initialize MessageBird provider."""
        self.api_key = getattr(settings, 'MESSAGEBIRD_API_KEY', None)
        self.logger = logger

    def validate_phone(self, phone_number: str) -> bool:
        """Validate phone number format."""
        return bool(re.match(r'^\+?1?\d{9,15}$', phone_number))

    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via MessageBird."""
        raise SMSProviderError("MessageBird provider not yet implemented")


class SMSChannel(AbstractChannel):
    """
    SMS notification channel with provider abstraction.

    Supports multiple SMS providers. Uses factory pattern to select provider.
    Messages are automatically truncated to 160 characters if needed.
    """

    # SMS character limit (standard SMS is 160 chars)
    SMS_CHAR_LIMIT = 160

    # Template for SMS messages
    SMS_TEMPLATE = "{user_name}: {message}"

    # Mapping of provider names to classes
    PROVIDERS = {
        'twilio': TwilioSMSProvider,
        'messagebird': MessageBirdSMSProvider,
    }

    def __init__(self):
        """Initialize SMS channel."""
        super().__init__()
        self.provider_name = getattr(settings, 'SMS_PROVIDER', 'twilio')
        self.provider = self._get_provider()

    def _get_provider(self) -> Optional[AbstractSMSProvider]:
        """
        Get SMS provider instance.

        Returns:
            Provider instance or None if not configured
        """
        if self.provider_name not in self.PROVIDERS:
            self.logger.warning(f"Unknown SMS provider: {self.provider_name}")
            return None

        provider_class = self.PROVIDERS[self.provider_name]
        try:
            return provider_class()
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.provider_name}: {e}")
            return None

    def validate_recipient(self, recipient: User) -> bool:
        """
        Validate that recipient has a phone number.

        Args:
            recipient: User to validate

        Returns:
            True if user has a phone number, False otherwise
        """
        if not self.provider:
            return False

        try:
            from notifications.channels.models import UserPhoneNumber

            # Try to get from UserPhoneNumber model first
            try:
                phone_record = UserPhoneNumber.objects.get(user=recipient)
                if phone_record.status == UserPhoneNumber.VerificationStatus.VERIFIED:
                    return self.provider.validate_phone(phone_record.phone_number)
            except Exception:
                pass

            # Fallback to direct attribute
            phone = getattr(recipient, 'phone_number', None)
            if not phone:
                return False

            return self.provider.validate_phone(phone)

        except Exception as e:
            self.logger.error(f"Error validating recipient {recipient.id}: {e}")
            return False

    def get_channel_name(self) -> str:
        """Get the name of this channel."""
        return 'sms'

    def _get_recipient_phone(self, recipient: User) -> Optional[str]:
        """
        Get phone number from recipient.

        Args:
            recipient: User to get phone from

        Returns:
            Phone number or None
        """
        try:
            from notifications.channels.models import UserPhoneNumber

            # Try to get from UserPhoneNumber model
            phone_record = UserPhoneNumber.objects.get(user=recipient)
            if phone_record.status == UserPhoneNumber.VerificationStatus.VERIFIED:
                return phone_record.phone_number
        except Exception:
            pass

        # Try direct attribute as fallback
        phone = getattr(recipient, 'phone_number', None)
        return phone

    def _truncate_sms(self, message: str) -> str:
        """
        Truncate SMS to 160 characters if needed.

        SMS messages are traditionally limited to 160 characters.
        This method ensures the message fits within that limit.

        Args:
            message: Message text

        Returns:
            Truncated message
        """
        if len(message) <= self.SMS_CHAR_LIMIT:
            return message

        # Truncate and add ellipsis
        return message[:self.SMS_CHAR_LIMIT - 3] + "..."

    def _format_sms_message(self, notification: Any, recipient: User) -> str:
        """
        Format SMS message from notification.

        Args:
            notification: Notification object
            recipient: Recipient user

        Returns:
            Formatted SMS message
        """
        user_name = recipient.get_full_name() or recipient.username
        message = self.SMS_TEMPLATE.format(
            user_name=user_name,
            message=notification.message
        )

        return self._truncate_sms(message)

    def send(self, notification: Any, recipient: User) -> Dict[str, Any]:
        """
        Send SMS notification.

        Args:
            notification: Notification object to send
            recipient: User to send to

        Returns:
            Dictionary with delivery status and metadata

        Raises:
            ChannelDeliveryError: If delivery fails
        """
        if not self.provider:
            self.log_delivery(notification, recipient, 'skipped',
                            'SMS provider not configured')
            return {
                'status': 'skipped',
                'reason': 'Provider not configured',
            }

        if not self.validate_recipient(recipient):
            self.log_delivery(notification, recipient, 'skipped',
                            'No valid phone number')
            return {
                'status': 'skipped',
                'reason': 'No phone number',
            }

        try:
            phone_number = self._get_recipient_phone(recipient)
            if not phone_number:
                raise ChannelDeliveryError("Could not get phone number")

            sms_message = self._format_sms_message(notification, recipient)

            result = self.provider.send_sms(phone_number, sms_message)

            self.log_delivery(notification, recipient, 'sent')

            return {
                'status': 'sent',
                'message_length': len(sms_message),
                'provider': result.get('provider', self.provider_name),
                'provider_message_id': result.get('message_id'),
            }

        except SMSProviderError as e:
            error_msg = str(e)
            self.log_delivery(notification, recipient, 'failed', error_msg)
            raise ChannelDeliveryError(f"SMS send failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            self.log_delivery(notification, recipient, 'failed', error_msg)
            raise ChannelDeliveryError(f"Unexpected error: {error_msg}")
