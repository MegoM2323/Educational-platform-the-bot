"""
Abstract base class for notification delivery channels.

Defines the interface that all notification channels must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class ChannelValidationError(Exception):
    """Raised when recipient validation fails."""
    pass


class ChannelDeliveryError(Exception):
    """Raised when channel delivery fails."""
    pass


class AbstractChannel(ABC):
    """
    Abstract base class for notification delivery channels.

    All notification channels must inherit from this class and implement
    the abstract methods.
    """

    def __init__(self):
        """Initialize the channel."""
        self.logger = logger

    @abstractmethod
    def send(self, notification: Any, recipient: User) -> Dict[str, Any]:
        """
        Send notification through this channel.

        Args:
            notification: Notification object to send
            recipient: User receiving the notification

        Returns:
            Dictionary with delivery status and metadata

        Raises:
            ChannelValidationError: If recipient validation fails
            ChannelDeliveryError: If delivery fails
        """
        pass

    @abstractmethod
    def validate_recipient(self, recipient: User) -> bool:
        """
        Validate that recipient has necessary information for this channel.

        For example, push channel needs a device token, SMS channel needs
        a phone number.

        Args:
            recipient: User to validate

        Returns:
            True if recipient is valid for this channel, False otherwise
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """
        Get the name of this channel for logging and identification.

        Returns:
            Channel name (e.g., 'push', 'sms', 'email')
        """
        pass

    def log_delivery(self, notification: Any, recipient: User,
                     status: str, error: Optional[str] = None) -> None:
        """
        Log delivery attempt.

        Args:
            notification: Notification that was sent
            recipient: Recipient user
            status: Delivery status ('sent', 'failed', 'skipped')
            error: Error message if delivery failed
        """
        channel_name = self.get_channel_name()
        msg = f"Channel={channel_name}, Recipient={recipient.email}, " \
              f"Status={status}"
        if error:
            msg += f", Error={error}"
            self.logger.error(msg)
        else:
            self.logger.info(msg)
