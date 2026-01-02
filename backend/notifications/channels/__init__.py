"""
Notification delivery channels module.

Provides abstract base class and concrete implementations for different
notification delivery methods (SMS).
"""

from .base import AbstractChannel, ChannelDeliveryError, ChannelValidationError
from .models import DeviceToken, UserPhoneNumber
from .sms import SMSChannel, TwilioSMSProvider

__all__ = [
    "AbstractChannel",
    "ChannelDeliveryError",
    "ChannelValidationError",
    "SMSChannel",
    "TwilioSMSProvider",
    "DeviceToken",
    "UserPhoneNumber",
    "get_channel",
    "NOTIFICATION_CHANNELS",
]


# Channel registry - maps channel types to their implementation classes
NOTIFICATION_CHANNELS = {
    "sms": SMSChannel,
}


def get_channel(channel_type: str) -> AbstractChannel:
    """
    Factory method to get a channel instance by type.

    Args:
        channel_type: Type of channel ('push', 'sms', 'email', etc.)

    Returns:
        Instance of the appropriate channel class

    Raises:
        ValueError: If channel type is not registered
    """
    if channel_type not in NOTIFICATION_CHANNELS:
        raise ValueError(f"Unknown channel type: {channel_type}")

    channel_class = NOTIFICATION_CHANNELS[channel_type]
    return channel_class()
