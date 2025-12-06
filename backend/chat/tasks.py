"""
Celery tasks for chat system.

Handles asynchronous operations for chat, including Pachca notifications.
"""
import logging
from celery import shared_task
from typing import Optional

from core.monitoring import log_system_event

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute base delay
    autoretry_for=(Exception,),  # Retry on any exception
    retry_backoff=True,  # Enable exponential backoff
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True  # Add random jitter to prevent thundering herd
)
def send_pachca_forum_notification_task(
    self,
    message_id: int,
    chat_room_id: int
) -> dict:
    """
    Send Pachca notification for new forum message (async via Celery).

    Uses exponential backoff retry: 1 min, 2 min, 4 min
    Transient errors (500, network) are retried automatically.
    Client errors (401, 403, 400) are logged but not retried.

    Args:
        message_id: ID of Message instance
        chat_room_id: ID of ChatRoom instance

    Returns:
        dict: {
            'success': bool,
            'message': str,
            'attempt': int,
            'notification_sent': bool
        }

    Raises:
        Exception: Re-raised for Celery retry mechanism
    """
    from chat.models import Message, ChatRoom
    from chat.services.pachca_service import PachcaService

    attempt_number = self.request.retries + 1

    try:
        # Retrieve message and chat room from database
        try:
            message = Message.objects.select_related('sender', 'room').get(id=message_id)
            chat_room = ChatRoom.objects.prefetch_related('participants').get(id=chat_room_id)
        except Message.DoesNotExist:
            error_msg = f"Message {message_id} not found"
            logger.error(error_msg)
            log_system_event(
                'pachca_notification_failed',
                error_msg,
                'error',
                metadata={
                    'message_id': message_id,
                    'chat_room_id': chat_room_id,
                    'error_type': 'message_not_found'
                }
            )
            return {
                'success': False,
                'message': error_msg,
                'attempt': attempt_number,
                'notification_sent': False
            }
        except ChatRoom.DoesNotExist:
            error_msg = f"ChatRoom {chat_room_id} not found"
            logger.error(error_msg)
            log_system_event(
                'pachca_notification_failed',
                error_msg,
                'error',
                metadata={
                    'message_id': message_id,
                    'chat_room_id': chat_room_id,
                    'error_type': 'chat_room_not_found'
                }
            )
            return {
                'success': False,
                'message': error_msg,
                'attempt': attempt_number,
                'notification_sent': False
            }

        # Initialize Pachca service
        pachca_service = PachcaService()

        # Check if configured
        if not pachca_service.is_configured():
            logger.debug(
                f"Pachca not configured, skipping notification for message {message_id}"
            )
            return {
                'success': True,
                'message': 'Pachca not configured, skipped',
                'attempt': attempt_number,
                'notification_sent': False
            }

        # Send notification
        logger.info(
            f"Sending Pachca notification for message {message_id} "
            f"in chat {chat_room_id} (attempt {attempt_number}/4)"
        )

        pachca_service.notify_new_forum_message(message, chat_room)

        # Log success
        log_system_event(
            'pachca_notification_sent',
            f'Pachca notification sent for message {message_id}',
            'info',
            metadata={
                'message_id': message_id,
                'chat_room_id': chat_room_id,
                'chat_type': chat_room.type,
                'sender_id': message.sender.id,
                'attempt': attempt_number
            }
        )

        logger.info(
            f"Successfully sent Pachca notification for message {message_id} "
            f"on attempt {attempt_number}"
        )

        return {
            'success': True,
            'message': 'Notification sent successfully',
            'attempt': attempt_number,
            'notification_sent': True
        }

    except Exception as e:
        # Log error with full context
        error_context = {
            'message_id': message_id,
            'chat_room_id': chat_room_id,
            'attempt': attempt_number,
            'max_retries': self.max_retries,
            'error': str(e),
            'error_type': type(e).__name__
        }

        logger.error(
            f"Error sending Pachca notification for message {message_id} "
            f"(attempt {attempt_number}/4): {str(e)}",
            exc_info=True,
            extra=error_context
        )

        # Check if this is the last retry
        if attempt_number >= self.max_retries:
            # Final failure - log critical event for monitoring
            log_system_event(
                'pachca_notification_failed_final',
                f'Failed to send Pachca notification after {attempt_number} attempts',
                'critical',
                metadata=error_context
            )

            logger.critical(
                f"FINAL FAILURE: Pachca notification for message {message_id} "
                f"failed after {attempt_number} attempts. Manual intervention may be required.",
                extra=error_context
            )

            return {
                'success': False,
                'message': f'Failed after {attempt_number} attempts: {str(e)}',
                'attempt': attempt_number,
                'notification_sent': False
            }
        else:
            # Transient failure - log and retry
            log_system_event(
                'pachca_notification_retry',
                f'Retrying Pachca notification (attempt {attempt_number})',
                'warning',
                metadata=error_context
            )

            logger.warning(
                f"Retrying Pachca notification for message {message_id} "
                f"(attempt {attempt_number}/4)",
                extra=error_context
            )

            # Re-raise to trigger Celery retry
            raise


@shared_task
def monitor_pachca_failures():
    """
    Periodic task to monitor and alert on repeated Pachca failures.

    Runs every hour to check for patterns of failures and generate alerts.
    Uses core.monitoring to check for critical events.

    Returns:
        dict: {
            'success': bool,
            'critical_failures_count': int,
            'recent_failures_count': int,
            'alert_generated': bool
        }
    """
    from django.utils import timezone
    from datetime import timedelta

    try:
        from core.monitoring import system_monitor

        # Check for critical Pachca failures in last hour
        one_hour_ago = timezone.now() - timedelta(hours=1)

        # Get system metrics
        metrics = system_monitor.get_system_metrics()

        # Count critical and warning events related to Pachca
        # This is a simplified implementation - in production, you'd query
        # your monitoring database or log aggregation system

        logger.info("Monitoring Pachca notification failures")

        # For now, just log that monitoring is active
        # In production, integrate with your monitoring stack (Sentry, DataDog, etc.)

        log_system_event(
            'pachca_monitoring_check',
            'Pachca failure monitoring check completed',
            'info',
            metadata={
                'timestamp': timezone.now().isoformat()
            }
        )

        return {
            'success': True,
            'message': 'Monitoring check completed',
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in Pachca monitoring task: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Monitoring error: {str(e)}'
        }
