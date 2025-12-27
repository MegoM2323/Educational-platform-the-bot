"""
SMS Notification Service with queuing and retry logic.

Provides high-level interface for sending SMS notifications through
Celery task queue with automatic retry, rate limiting, and delivery tracking.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.channels.sms import SMSChannel, SMSProviderError
from notifications.models import Notification, NotificationQueue

User = get_user_model()
logger = logging.getLogger(__name__)


class SMSValidationError(Exception):
    """Raised when SMS validation fails."""
    pass


class SMSQueueError(Exception):
    """Raised when SMS queue operation fails."""
    pass


class SMSNotificationService:
    """
    Service for sending SMS notifications with queuing and retry logic.

    Features:
    - Message validation and character limit handling
    - Celery-based queuing for async delivery
    - Automatic retry with exponential backoff
    - Rate limiting per user
    - Delivery tracking and logging
    - Provider abstraction (Twilio, etc.)

    Usage:
        service = SMSNotificationService()
        service.send_sms_async(
            recipient=user,
            notification=notification,
            priority='high'
        )
    """

    # SMS character limit (160 for single SMS)
    SMS_CHAR_LIMIT = 160

    # Rate limiting: max SMS per user per hour
    RATE_LIMIT_PER_HOUR = 10

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 300  # 5 minutes
    RETRY_BACKOFF_MULTIPLIER = 2

    def __init__(self):
        """Initialize SMS notification service."""
        self.sms_channel = SMSChannel()
        self.logger = logger

    def validate_sms_message(self, message: str) -> bool:
        """
        Validate SMS message format.

        Args:
            message: Message text to validate

        Returns:
            True if message is valid

        Raises:
            SMSValidationError: If validation fails
        """
        if not message or not isinstance(message, str):
            raise SMSValidationError("Message must be non-empty string")

        if len(message) > self.SMS_CHAR_LIMIT * 3:
            raise SMSValidationError(
                f"Message exceeds maximum length of {self.SMS_CHAR_LIMIT * 3} chars"
            )

        return True

    def validate_recipient(self, recipient: User) -> bool:
        """
        Validate that recipient can receive SMS.

        Args:
            recipient: User to validate

        Returns:
            True if recipient is valid for SMS delivery

        Raises:
            SMSValidationError: If recipient is invalid
        """
        if not recipient or not hasattr(recipient, 'email'):
            raise SMSValidationError("Invalid recipient user")

        # Check if SMS notifications are enabled for user
        try:
            settings_obj = getattr(recipient, 'notification_settings', None)
            if settings_obj and not settings_obj.sms_notifications:
                raise SMSValidationError(
                    f"SMS notifications disabled for user {recipient.email}"
                )
        except Exception:
            pass

        # Validate that provider can reach recipient
        if not self.sms_channel.validate_recipient(recipient):
            raise SMSValidationError(
                f"Recipient {recipient.email} not configured for SMS"
            )

        return True

    def check_rate_limit(self, recipient: User) -> bool:
        """
        Check if recipient has exceeded SMS rate limit.

        Rate limit: RATE_LIMIT_PER_HOUR SMS per hour

        Args:
            recipient: User to check

        Returns:
            True if within rate limit, False otherwise
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)

        sms_count = NotificationQueue.objects.filter(
            notification__recipient=recipient,
            channel='sms',
            status__in=['sent', 'processing', 'pending'],
            created_at__gte=one_hour_ago
        ).count()

        return sms_count < self.RATE_LIMIT_PER_HOUR

    def queue_sms(
        self,
        notification: Notification,
        recipient: User,
        scheduled_at: Optional[timezone.datetime] = None,
        priority: str = NotificationQueue.Status.PENDING,
    ) -> NotificationQueue:
        """
        Queue SMS notification for delivery via Celery.

        Args:
            notification: Notification object to queue
            recipient: Recipient user
            scheduled_at: Optional datetime to send SMS
            priority: Queue priority level

        Returns:
            NotificationQueue entry

        Raises:
            SMSValidationError: If validation fails
            SMSQueueError: If queuing fails
        """
        # Validate message
        self.validate_sms_message(notification.message)

        # Validate recipient
        self.validate_recipient(recipient)

        # Check rate limit
        if not self.check_rate_limit(recipient):
            raise SMSQueueError(
                f"Rate limit exceeded for user {recipient.email}"
            )

        try:
            # Create queue entry
            queue_entry = NotificationQueue.objects.create(
                notification=notification,
                channel='sms',
                status=NotificationQueue.Status.PENDING,
                scheduled_at=scheduled_at or timezone.now(),
                max_attempts=self.MAX_RETRIES,
            )

            self.logger.info(
                f"Queued SMS for notification {notification.id} "
                f"to user {recipient.email} (queue_id={queue_entry.id})"
            )

            return queue_entry

        except Exception as e:
            error_msg = f"Failed to queue SMS: {str(e)}"
            self.logger.error(error_msg)
            raise SMSQueueError(error_msg)

    def send_sms_async(
        self,
        notification: Notification,
        recipient: User,
        scheduled_at: Optional[timezone.datetime] = None,
    ) -> Dict[str, Any]:
        """
        Queue SMS notification for async delivery.

        This is the main entry point for sending SMS notifications.
        The actual delivery happens asynchronously via Celery task.

        Args:
            notification: Notification object
            recipient: Recipient user
            scheduled_at: Optional datetime to send SMS

        Returns:
            Dictionary with queue status and queue_id

        Raises:
            SMSValidationError: If validation fails
            SMSQueueError: If queuing fails
        """
        try:
            # Queue the SMS
            queue_entry = self.queue_sms(
                notification=notification,
                recipient=recipient,
                scheduled_at=scheduled_at,
            )

            # Import here to avoid circular imports
            from notifications.tasks import send_sms_task

            # Enqueue Celery task
            send_sms_task.delay(queue_entry.id)

            return {
                'status': 'queued',
                'queue_id': queue_entry.id,
                'message': 'SMS queued for delivery',
            }

        except (SMSValidationError, SMSQueueError) as e:
            self.logger.warning(f"SMS delivery skipped: {str(e)}")
            return {
                'status': 'skipped',
                'reason': str(e),
            }

    def send_sms_now(
        self,
        notification: Notification,
        recipient: User,
    ) -> Dict[str, Any]:
        """
        Send SMS immediately (synchronously).

        Used for urgent notifications that must be sent right away.
        Falls back to queue if sync send fails.

        Args:
            notification: Notification object
            recipient: Recipient user

        Returns:
            Dictionary with send status

        Raises:
            SMSValidationError: If validation fails
        """
        # Validate
        self.validate_sms_message(notification.message)
        self.validate_recipient(recipient)

        try:
            # Send immediately via channel
            result = self.sms_channel.send(notification, recipient)

            self.logger.info(
                f"Sent SMS for notification {notification.id} "
                f"to user {recipient.email}"
            )

            return {
                'status': 'sent',
                'message_length': result.get('message_length'),
                'provider_message_id': result.get('provider_message_id'),
            }

        except Exception as e:
            # Fall back to async queuing
            error_msg = str(e)
            self.logger.warning(
                f"Sync SMS send failed, falling back to queue: {error_msg}"
            )

            try:
                queue_entry = self.queue_sms(notification, recipient)
                from notifications.tasks import send_sms_task
                send_sms_task.delay(queue_entry.id)

                return {
                    'status': 'queued_fallback',
                    'queue_id': queue_entry.id,
                    'reason': error_msg,
                }
            except Exception as queue_error:
                return {
                    'status': 'failed',
                    'reason': str(queue_error),
                }

    def retry_failed_sms(self, queue_entry_id: int) -> bool:
        """
        Retry failed SMS delivery.

        Implements exponential backoff retry strategy.

        Args:
            queue_entry_id: ID of NotificationQueue entry to retry

        Returns:
            True if retry was scheduled, False otherwise
        """
        try:
            queue_entry = NotificationQueue.objects.get(id=queue_entry_id)

            # Check if we can retry
            if queue_entry.attempts >= queue_entry.max_attempts:
                queue_entry.status = NotificationQueue.Status.FAILED
                queue_entry.error_message = "Max retries exceeded"
                queue_entry.save()
                self.logger.error(
                    f"Max retries exceeded for queue entry {queue_entry_id}"
                )
                return False

            # Calculate retry delay with exponential backoff
            retry_delay = (
                self.INITIAL_RETRY_DELAY *
                (self.RETRY_BACKOFF_MULTIPLIER ** queue_entry.attempts)
            )

            # Schedule retry
            queue_entry.scheduled_at = timezone.now() + timedelta(
                seconds=retry_delay
            )
            queue_entry.status = NotificationQueue.Status.PENDING
            queue_entry.save()

            self.logger.info(
                f"Scheduled retry for queue entry {queue_entry_id} "
                f"in {retry_delay} seconds"
            )

            # Re-enqueue task
            from notifications.tasks import send_sms_task
            send_sms_task.apply_async(
                args=[queue_entry_id],
                countdown=int(retry_delay)
            )

            return True

        except NotificationQueue.DoesNotExist:
            self.logger.error(f"Queue entry {queue_entry_id} not found")
            return False
        except Exception as e:
            self.logger.error(
                f"Error retrying SMS for queue {queue_entry_id}: {str(e)}"
            )
            return False

    def get_sms_delivery_status(self, queue_entry_id: int) -> Dict[str, Any]:
        """
        Get delivery status of queued SMS.

        Args:
            queue_entry_id: ID of NotificationQueue entry

        Returns:
            Dictionary with delivery status and metadata
        """
        try:
            queue_entry = NotificationQueue.objects.get(id=queue_entry_id)

            return {
                'queue_id': queue_entry.id,
                'status': queue_entry.status,
                'attempts': queue_entry.attempts,
                'max_attempts': queue_entry.max_attempts,
                'scheduled_at': queue_entry.scheduled_at.isoformat() if queue_entry.scheduled_at else None,
                'processed_at': queue_entry.processed_at.isoformat() if queue_entry.processed_at else None,
                'error': queue_entry.error_message or None,
            }
        except NotificationQueue.DoesNotExist:
            return {
                'queue_id': queue_entry_id,
                'status': 'not_found',
            }

    def get_user_sms_stats(self, user: User) -> Dict[str, Any]:
        """
        Get SMS statistics for a user.

        Args:
            user: User to get stats for

        Returns:
            Dictionary with SMS statistics
        """
        one_hour_ago = timezone.now() - timedelta(hours=1)
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        sms_sent_today = NotificationQueue.objects.filter(
            notification__recipient=user,
            channel='sms',
            status=NotificationQueue.Status.SENT,
            created_at__gte=today
        ).count()

        sms_sent_hour = NotificationQueue.objects.filter(
            notification__recipient=user,
            channel='sms',
            status=NotificationQueue.Status.SENT,
            created_at__gte=one_hour_ago
        ).count()

        sms_failed = NotificationQueue.objects.filter(
            notification__recipient=user,
            channel='sms',
            status=NotificationQueue.Status.FAILED,
            created_at__gte=today
        ).count()

        sms_pending = NotificationQueue.objects.filter(
            notification__recipient=user,
            channel='sms',
            status=NotificationQueue.Status.PENDING
        ).count()

        return {
            'user_id': user.id,
            'sent_today': sms_sent_today,
            'sent_last_hour': sms_sent_hour,
            'failed_today': sms_failed,
            'pending': sms_pending,
            'rate_limit_remaining': max(0, self.RATE_LIMIT_PER_HOUR - sms_sent_hour),
        }
