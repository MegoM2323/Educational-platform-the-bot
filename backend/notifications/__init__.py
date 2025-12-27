"""
Notifications module for THE_BOT platform.
Provides notification service, email delivery, and real-time messaging.
"""
# Avoid circular imports by importing lazily
__all__ = [
    'NotificationService',
    'EmailNotificationService',
    'get_email_service',
    'EmailDeliveryStatus',
]


def __getattr__(name):
    """Lazy import to avoid circular dependencies"""
    if name == 'NotificationService':
        from .notification_service import NotificationService
        return NotificationService
    elif name == 'EmailNotificationService':
        from .email_service import EmailNotificationService
        return EmailNotificationService
    elif name == 'get_email_service':
        from .email_service import get_email_service
        return get_email_service
    elif name == 'EmailDeliveryStatus':
        from .email_service import EmailDeliveryStatus
        return EmailDeliveryStatus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
