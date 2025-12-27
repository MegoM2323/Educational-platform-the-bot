"""
Celery tasks for email notification delivery with retry logic and tracking.
Handles async email sending with delivery status updates.
"""
import logging
from typing import Dict, Optional, Any
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string

from .models import Notification, NotificationQueue
from .email_service import EmailNotificationService, EmailDeliveryStatus

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    name='notifications.send_notification_email'
)
def send_notification_email(
    self,
    notification_id: int,
    template_name: Optional[str] = None,
    subject: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send a notification email asynchronously with retry logic.

    Args:
        notification_id: ID of the Notification to send
        template_name: Override template name
        subject: Override subject line
        context: Additional template context

    Returns:
        Dict with delivery status
    """
    try:
        # Get notification
        notification = Notification.objects.get(id=notification_id)
        recipient = notification.recipient

        # Skip if user has disabled email notifications
        try:
            settings = getattr(recipient, 'notification_settings', None)
            if settings and not settings.email_notifications:
                logger.info(
                    f"Email notifications disabled for user {recipient.id}, "
                    f"skipping notification {notification_id}"
                )
                # Update queue entry status
                NotificationQueue.objects.filter(
                    notification=notification,
                    channel='email'
                ).update(status=EmailDeliveryStatus.CANCELLED)
                return {
                    'success': False,
                    'notification_id': notification_id,
                    'reason': 'Email notifications disabled'
                }
        except Exception:
            pass

        # Get email service
        email_service = EmailNotificationService()

        # Prepare context
        if not context:
            context = notification.data or {}

        # Add notification data to context
        context.update({
            'notification_id': notification_id,
            'notification_type': notification.type,
            'title': notification.title,
            'message': notification.message,
        })

        # Render email template
        final_template = template_name or f"notifications/{notification.type}.html"
        final_subject = subject or EmailNotificationService._get_default_subject(
            notification.type
        )

        try:
            html_content = render_to_string(final_template, {
                'recipient': recipient,
                'recipient_name': recipient.get_full_name() or recipient.username,
                'recipient_email': recipient.email,
                **context
            })
        except Exception as e:
            logger.error(
                f"Failed to render template {final_template} for "
                f"notification {notification_id}: {str(e)}"
            )
            raise

        # Update queue status to processing
        NotificationQueue.objects.filter(
            notification=notification,
            channel='email'
        ).update(status=EmailDeliveryStatus.PROCESSING)

        # Send email
        success = email_service.send_email(
            to_email=recipient.email,
            subject=final_subject,
            html_content=html_content,
            notification_id=notification_id,
            tags={'notification_type': notification.type}
        )

        if success:
            # Update notification status
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save()

            # Update queue entry
            queue_entry = NotificationQueue.objects.get(
                notification=notification,
                channel='email'
            )
            queue_entry.status = EmailDeliveryStatus.SENT
            queue_entry.processed_at = timezone.now()
            queue_entry.save()

            logger.info(
                f"Email sent successfully for notification {notification_id} "
                f"to {recipient.email}"
            )

            return {
                'success': True,
                'notification_id': notification_id,
                'recipient_email': recipient.email,
                'sent_at': timezone.now().isoformat()
            }
        else:
            raise Exception("Email sending failed")

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return {
            'success': False,
            'notification_id': notification_id,
            'error': 'Notification not found'
        }

    except Exception as exc:
        logger.error(
            f"Error sending email for notification {notification_id}: {str(exc)}"
        )

        try:
            # Update queue entry with error
            queue_entry = NotificationQueue.objects.get(
                notification_id=notification_id,
                channel='email'
            )
            queue_entry.attempts += 1
            queue_entry.error_message = str(exc)

            if queue_entry.attempts >= queue_entry.max_attempts:
                queue_entry.status = EmailDeliveryStatus.FAILED
            else:
                queue_entry.status = EmailDeliveryStatus.RETRY

            queue_entry.save()
        except Exception as update_exc:
            logger.error(
                f"Error updating queue entry: {str(update_exc)}"
            )

        # Retry with exponential backoff
        retry_delay = 300 * (2 ** self.request.retries)  # 5min, 10min, 20min
        raise self.retry(exc=exc, countdown=retry_delay)


@shared_task(
    name='notifications.send_batch_notification_emails'
)
def send_batch_notification_emails(
    notification_ids: list,
    template_name: Optional[str] = None,
    subject: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send emails for multiple notifications.

    Args:
        notification_ids: List of notification IDs
        template_name: Override template name
        subject: Override subject line

    Returns:
        Dict with batch results
    """
    results = {
        'total': len(notification_ids),
        'sent': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }

    for notif_id in notification_ids:
        try:
            result = send_notification_email.delay(
                notif_id,
                template_name=template_name,
                subject=subject
            )
            results['sent'] += 1
        except Exception as e:
            logger.error(f"Error queueing email for notification {notif_id}: {str(e)}")
            results['failed'] += 1
            results['errors'].append({
                'notification_id': notif_id,
                'error': str(e)
            })

    logger.info(f"Batch email send queued: {results}")
    return results


@shared_task(
    name='notifications.process_email_queue'
)
def process_email_queue(batch_size: int = 50) -> Dict[str, Any]:
    """
    Process pending emails in the queue.
    Queries for pending queue entries and sends them.

    Args:
        batch_size: Number of emails to process in one task

    Returns:
        Dict with processing statistics
    """
    from .models import NotificationQueue

    try:
        # Get pending queue entries
        pending_entries = NotificationQueue.objects.filter(
            channel='email',
            status=EmailDeliveryStatus.PENDING
        ).select_related('notification').order_by('created_at')[:batch_size]

        processed_count = 0
        failed_count = 0

        for queue_entry in pending_entries:
            try:
                # Queue email task
                send_notification_email.delay(
                    queue_entry.notification.id
                )
                processed_count += 1

                logger.info(
                    f"Queued email for queue entry {queue_entry.id} "
                    f"(notification {queue_entry.notification.id})"
                )
            except Exception as e:
                failed_count += 1
                queue_entry.error_message = str(e)
                queue_entry.save()
                logger.error(
                    f"Error processing queue entry {queue_entry.id}: {str(e)}"
                )

        logger.info(
            f"Email queue processing complete: "
            f"{processed_count} queued, {failed_count} errors"
        )

        return {
            'processed': processed_count,
            'failed': failed_count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"Error in process_email_queue: {str(exc)}")
        return {
            'processed': 0,
            'failed': -1,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(
    name='notifications.retry_failed_emails'
)
def retry_failed_emails(max_retries: int = 3) -> Dict[str, Any]:
    """
    Retry emails that failed to send.

    Args:
        max_retries: Maximum retry attempts per email

    Returns:
        Dict with retry statistics
    """
    from .models import NotificationQueue

    try:
        # Get failed entries that haven't exceeded max retries
        failed_entries = NotificationQueue.objects.filter(
            channel='email',
            status=EmailDeliveryStatus.RETRY,
            attempts__lt=max_retries
        ).select_related('notification').order_by('created_at')[:50]

        retried_count = 0

        for queue_entry in failed_entries:
            try:
                # Re-queue for sending
                send_notification_email.delay(
                    queue_entry.notification.id
                )
                queue_entry.status = EmailDeliveryStatus.PENDING
                queue_entry.save()
                retried_count += 1

                logger.info(
                    f"Retrying email for queue entry {queue_entry.id} "
                    f"(attempt {queue_entry.attempts})"
                )
            except Exception as e:
                logger.error(f"Error retrying queue entry {queue_entry.id}: {str(e)}")

        logger.info(f"Retried {retried_count} failed emails")

        return {
            'retried': retried_count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"Error in retry_failed_emails: {str(exc)}")
        return {
            'retried': 0,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }


@shared_task(
    name='notifications.cleanup_old_email_queue'
)
def cleanup_old_email_queue(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old completed email queue entries.

    Args:
        days_old: Delete entries older than this many days

    Returns:
        Dict with cleanup statistics
    """
    from datetime import timedelta
    from .models import NotificationQueue

    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Delete old completed entries
        deleted_count, _ = NotificationQueue.objects.filter(
            channel='email',
            status__in=[EmailDeliveryStatus.SENT, EmailDeliveryStatus.FAILED],
            processed_at__lt=cutoff_date
        ).delete()

        logger.info(
            f"Cleaned up {deleted_count} old email queue entries "
            f"older than {days_old} days"
        )

        return {
            'deleted': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"Error in cleanup_old_email_queue: {str(exc)}")
        return {
            'deleted': 0,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }
