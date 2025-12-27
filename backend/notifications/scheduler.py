"""
Notification scheduling service for Celery integration.
Handles creation, cancellation, and processing of scheduled notifications.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from .models import Notification
from .notification_service import NotificationService

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationScheduler:
    """
    Service for scheduling and managing delayed notifications.
    """

    def __init__(self):
        self.service = NotificationService()

    def schedule_notification(
        self,
        recipients: List[int],
        title: str,
        message: str,
        scheduled_at: datetime,
        notif_type: str = Notification.Type.SYSTEM,
        priority: str = Notification.Priority.NORMAL,
        related_object_type: str = '',
        related_object_id: Optional[int] = None,
        data: Optional[Dict] = None,
    ) -> List[int]:
        """
        Schedule notifications for multiple recipients.

        Args:
            recipients: List of user IDs to receive notifications
            title: Notification title
            message: Notification message
            scheduled_at: DateTime when to send (ISO format or timezone-aware)
            notif_type: Type of notification
            priority: Priority level
            related_object_type: Type of related object
            related_object_id: ID of related object
            data: Additional data dictionary

        Returns:
            List of created notification IDs

        Raises:
            ValueError: If scheduled_at is in the past or recipients is empty
        """
        if not recipients:
            raise ValueError("Recipients list cannot be empty")

        # Ensure scheduled_at is timezone-aware
        if isinstance(scheduled_at, str):
            scheduled_at = timezone.datetime.fromisoformat(scheduled_at)

        if not timezone.is_aware(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at)

        # Validate scheduled_at is in the future
        now = timezone.now()
        if scheduled_at <= now:
            raise ValueError(
                f"scheduled_at must be in the future. "
                f"Got {scheduled_at}, now is {now}"
            )

        created_ids = []

        with transaction.atomic():
            for user_id in recipients:
                try:
                    user = User.objects.get(id=user_id)
                    notification = Notification.objects.create(
                        recipient=user,
                        type=notif_type,
                        title=title,
                        message=message,
                        priority=priority,
                        related_object_type=related_object_type,
                        related_object_id=related_object_id,
                        data=data or {},
                        is_sent=False,
                        scheduled_at=scheduled_at,
                        scheduled_status='pending',
                    )
                    created_ids.append(notification.id)
                    logger.info(
                        f"Scheduled notification {notification.id} "
                        f"for user {user_id} at {scheduled_at}"
                    )
                except User.DoesNotExist:
                    logger.warning(f"User {user_id} does not exist")
                except Exception as e:
                    logger.error(
                        f"Error scheduling notification for user {user_id}: {e}"
                    )

        return created_ids

    def cancel_scheduled(self, notification_id: int) -> bool:
        """
        Cancel a scheduled notification before it's sent.

        Args:
            notification_id: ID of the notification to cancel

        Returns:
            True if cancelled, False if not found or already sent

        Raises:
            ValueError: If notification is not in pending state
        """
        try:
            notification = Notification.objects.get(id=notification_id)

            if notification.scheduled_status != 'pending':
                raise ValueError(
                    f"Cannot cancel notification with status "
                    f"{notification.scheduled_status}. Only pending can be cancelled."
                )

            notification.scheduled_status = 'cancelled'
            notification.save()

            logger.info(f"Cancelled scheduled notification {notification_id}")
            return True

        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found")
            return False
        except ValueError as e:
            logger.warning(f"Cannot cancel notification {notification_id}: {e}")
            return False

    def get_pending_notifications(self) -> list:
        """
        Get all pending notifications that are due to be sent.

        Returns:
            QuerySet of pending notifications with scheduled_at <= now
        """
        now = timezone.now()
        return Notification.objects.filter(
            scheduled_at__lte=now,
            scheduled_status='pending'
        ).select_related('recipient').order_by('scheduled_at')

    def send_scheduled_notification(self, notification_id: int) -> bool:
        """
        Send a scheduled notification and update its status.

        Args:
            notification_id: ID of notification to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            notification = Notification.objects.select_for_update().get(
                id=notification_id
            )

            # Double-check it's still pending (might have been cancelled)
            if notification.scheduled_status != 'pending':
                logger.info(
                    f"Notification {notification_id} is not pending "
                    f"(status: {notification.scheduled_status})"
                )
                return False

            # Send the notification via WebSocket
            payload = {
                'id': notification.id,
                'type': notification.type,
                'title': notification.title,
                'message': notification.message,
                'priority': notification.priority,
                'related_object_type': notification.related_object_type,
                'related_object_id': notification.related_object_id,
                'data': notification.data,
                'created_at': notification.created_at.isoformat(),
            }
            self.service._ws_send(notification.recipient.id, payload)

            # Update notification status
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.scheduled_status = 'sent'
            notification.save()

            logger.info(f"Sent scheduled notification {notification_id}")
            return True

        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error sending notification {notification_id}: {e}")
            return False

    def get_schedule_status(self, notification_id: int) -> Optional[Dict]:
        """
        Get the scheduling status of a notification.

        Args:
            notification_id: ID of notification

        Returns:
            Dict with scheduling details or None if not found
        """
        try:
            notification = Notification.objects.get(id=notification_id)
            return {
                'id': notification.id,
                'title': notification.title,
                'scheduled_at': notification.scheduled_at,
                'scheduled_status': notification.scheduled_status,
                'is_sent': notification.is_sent,
                'sent_at': notification.sent_at,
                'created_at': notification.created_at,
            }
        except Notification.DoesNotExist:
            return None

    def retry_failed_notification(
        self,
        notification_id: int,
        retry_delay_minutes: int = 5
    ) -> bool:
        """
        Reschedule a failed notification for retry.

        Args:
            notification_id: ID of notification to retry
            retry_delay_minutes: Minutes to wait before retry

        Returns:
            True if rescheduled, False otherwise
        """
        try:
            notification = Notification.objects.get(id=notification_id)

            if notification.scheduled_status == 'sent':
                logger.info(f"Notification {notification_id} already sent")
                return False

            new_scheduled_at = timezone.now() + timedelta(
                minutes=retry_delay_minutes
            )
            notification.scheduled_at = new_scheduled_at
            notification.scheduled_status = 'pending'
            notification.save()

            logger.info(
                f"Rescheduled notification {notification_id} for retry at "
                f"{new_scheduled_at}"
            )
            return True

        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found")
            return False
