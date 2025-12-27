"""
Celery задачи для уведомлений
"""
from celery import shared_task
from django.utils import timezone
from .archive import NotificationArchiveService
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='notifications.archive_old_notifications')
def archive_old_notifications(self, days=30):
    """
    Celery задача для архивирования уведомлений старше 30 дней
    Запускается ежедневно в 2:00 по расписанию

    Args:
        days: количество дней для архивирования (по умолчанию 30)

    Returns:
        dict: результаты архивирования
    """
    try:
        logger.info(f"Начало архивирования уведомлений старше {days} дней")

        result = NotificationArchiveService.archive_old_notifications(days=days)

        logger.info(
            f"Архивирование завершено: {result['archived_count']} уведомлений архивировано"
        )

        if result['errors']:
            logger.error(f"Ошибки при архивировании: {result['errors']}")

        return result

    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи архивирования: {str(e)}", exc_info=True)
        # Повторяем задачу при ошибке (max_retries по умолчанию 3)
        raise self.retry(exc=e, countdown=60)


@shared_task(name='notifications.cleanup_old_archived')
def cleanup_old_archived(days=90):
    """
    Celery задача для удаления архивированных уведомлений старше 90 дней
    Помогает освободить место в базе данных
    Запускается еженедельно в воскресенье в 3:00 по расписанию

    Args:
        days: количество дней для удаления (по умолчанию 90)

    Returns:
        dict: результаты удаления
    """
    try:
        logger.info(f"Начало очистки архивированных уведомлений старше {days} дней")

        result = NotificationArchiveService.bulk_delete_archived(days=days)

        logger.info(
            f"Очистка завершена: {result['deleted_count']} уведомлений удалено"
        )

        if result['errors']:
            logger.error(f"Ошибки при удалении: {result['errors']}")

        return result

    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи очистки: {str(e)}", exc_info=True)
        return {
            'deleted_count': 0,
            'errors': [str(e)]
        }


# ============= SCHEDULING TASKS =============

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='notifications.tasks.send_notification_task'
)
def send_notification_task(self, notification_id: int):
    """
    Send a single notification asynchronously.

    This task is used by the scheduled notification processor.
    It handles retry logic with exponential backoff.

    Args:
        notification_id: ID of the Notification to send

    Returns:
        Dict with success status and message
    """
    from .scheduler import NotificationScheduler
    try:
        scheduler = NotificationScheduler()
        success = scheduler.send_scheduled_notification(notification_id)

        if success:
            return {
                'success': True,
                'notification_id': notification_id,
                'message': 'Notification sent successfully',
            }
        else:
            logger.error(f"Failed to send notification {notification_id}")
            return {
                'success': False,
                'notification_id': notification_id,
                'message': 'Failed to send notification',
            }

    except Exception as exc:
        logger.error(
            f"Error in send_notification_task for {notification_id}: {exc}"
        )
        # Retry with exponential backoff: 5min, 10min, 20min
        retry_delay = 300 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=retry_delay)


@shared_task(
    name='notifications.tasks.process_scheduled_notifications'
)
def process_scheduled_notifications():
    """
    Process all pending scheduled notifications that are due to be sent.

    This task should be run every minute via Celery Beat.
    It queries for notifications with scheduled_at <= now and scheduled_status=pending,
    then enqueues send_notification_task for each one.

    Returns:
        Dict with processing statistics
    """
    from django.utils import timezone
    from .scheduler import NotificationScheduler
    try:
        scheduler = NotificationScheduler()
        pending_notifications = scheduler.get_pending_notifications()

        processed_count = 0
        failed_count = 0

        for notification in pending_notifications:
            try:
                # Enqueue the send task
                send_notification_task.delay(notification.id)
                processed_count += 1
                logger.info(
                    f"Enqueued notification {notification.id} for delivery"
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Error enqueueing notification {notification.id}: {e}"
                )

        logger.info(
            f"Processed scheduled notifications: {processed_count} sent, "
            f"{failed_count} failed"
        )

        return {
            'processed': processed_count,
            'failed': failed_count,
            'timestamp': timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Error in process_scheduled_notifications: {exc}")
        return {
            'processed': 0,
            'failed': -1,
            'error': str(exc),
            'timestamp': timezone.now().isoformat(),
        }


@shared_task(
    name='notifications.tasks.cleanup_cancelled_notifications'
)
def cleanup_cancelled_notifications(days_old: int = 30):
    """
    Clean up old cancelled and sent scheduled notifications.

    This task removes notifications that:
    - Have scheduled_status='cancelled' or 'sent'
    - Are older than days_old days
    - Are not required for audit purposes

    Args:
        days_old: Delete notifications older than this many days

    Returns:
        Dict with cleanup statistics
    """
    from datetime import timedelta
    from django.utils import timezone
    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Count before deletion
        from .models import Notification
        count_before = Notification.objects.filter(
            scheduled_at__lt=cutoff_date,
            scheduled_status__in=['cancelled', 'sent']
        ).count()

        # Delete cancelled notifications older than cutoff
        deleted_count, _ = Notification.objects.filter(
            scheduled_at__lt=cutoff_date,
            scheduled_status='cancelled'
        ).delete()

        logger.info(
            f"Cleaned up {deleted_count} old cancelled notifications "
            f"(before cutoff: {count_before})"
        )

        return {
            'deleted': deleted_count,
            'before_cutoff': count_before,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Error in cleanup_cancelled_notifications: {exc}")
        return {
            'deleted': 0,
            'error': str(exc),
            'timestamp': timezone.now().isoformat(),
        }


@shared_task(
    name='notifications.tasks.retry_failed_notifications'
)
def retry_failed_notifications():
    """
    Find and retry notifications that failed to send.

    This task checks for notifications with scheduling issues
    and reschedules them with exponential backoff.

    Returns:
        Dict with retry statistics
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import Notification
    from .scheduler import NotificationScheduler
    try:
        scheduler = NotificationScheduler()

        # Look for notifications that were supposed to be sent
        # but are still in pending status from more than 5 minutes ago
        five_minutes_ago = timezone.now() - timedelta(minutes=5)

        stuck_notifications = Notification.objects.filter(
            scheduled_at__lt=five_minutes_ago,
            scheduled_status='pending'
        ).select_related('recipient')

        retried_count = 0

        for notification in stuck_notifications[:100]:  # Limit to 100 per run
            try:
                scheduler.retry_failed_notification(
                    notification.id,
                    retry_delay_minutes=10
                )
                retried_count += 1
            except Exception as e:
                logger.error(
                    f"Error retrying notification {notification.id}: {e}"
                )

        logger.info(f"Retried {retried_count} failed notifications")

        return {
            'retried': retried_count,
            'timestamp': timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Error in retry_failed_notifications: {exc}")
        return {
            'retried': 0,
            'error': str(exc),
            'timestamp': timezone.now().isoformat(),
        }


# ============= SMS NOTIFICATION TASKS =============

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name='notifications.tasks.send_sms_task'
)
def send_sms_task(self, queue_entry_id: int):
    """
    Send queued SMS notification asynchronously.

    This task is executed by Celery workers to deliver SMS notifications.
    It handles retry logic with exponential backoff.

    Args:
        queue_entry_id: ID of NotificationQueue entry to process

    Returns:
        Dict with delivery status and message
    """
    from notifications.models import NotificationQueue
    from notifications.channels.sms import SMSChannel, SMSProviderError

    try:
        # Get queue entry
        queue_entry = NotificationQueue.objects.get(id=queue_entry_id)

        # Mark as processing
        queue_entry.status = NotificationQueue.Status.PROCESSING
        queue_entry.save(update_fields=['status'])

        notification = queue_entry.notification
        recipient = notification.recipient

        # Send SMS
        sms_channel = SMSChannel()

        try:
            result = sms_channel.send(notification, recipient)

            # Mark as sent
            queue_entry.status = NotificationQueue.Status.SENT
            queue_entry.attempts += 1
            queue_entry.processed_at = timezone.now()
            queue_entry.error_message = ""
            queue_entry.save()

            logger.info(
                f"SMS sent successfully for queue {queue_entry_id} "
                f"to user {recipient.email}"
            )

            return {
                'success': True,
                'queue_id': queue_entry_id,
                'message': 'SMS sent successfully',
            }

        except SMSProviderError as e:
            # Provider error - retry
            queue_entry.attempts += 1
            queue_entry.error_message = str(e)

            if queue_entry.attempts >= queue_entry.max_attempts:
                queue_entry.status = NotificationQueue.Status.FAILED
                queue_entry.processed_at = timezone.now()
                queue_entry.save()

                logger.error(
                    f"SMS delivery failed after {queue_entry.attempts} attempts "
                    f"for queue {queue_entry_id}: {str(e)}"
                )

                return {
                    'success': False,
                    'queue_id': queue_entry_id,
                    'message': 'SMS delivery failed - max retries exceeded',
                    'attempts': queue_entry.attempts,
                }
            else:
                queue_entry.status = NotificationQueue.Status.PENDING
                queue_entry.save()

                # Calculate retry delay with exponential backoff
                retry_delay = 300 * (2 ** queue_entry.attempts)

                logger.warning(
                    f"SMS delivery failed for queue {queue_entry_id}, "
                    f"retrying in {retry_delay} seconds (attempt {queue_entry.attempts})"
                )

                # Retry with backoff
                raise self.retry(exc=e, countdown=int(retry_delay))

    except NotificationQueue.DoesNotExist:
        logger.error(f"Queue entry {queue_entry_id} not found")
        return {
            'success': False,
            'queue_id': queue_entry_id,
            'message': 'Queue entry not found',
        }
    except Exception as exc:
        logger.error(
            f"Unexpected error in send_sms_task for queue {queue_entry_id}: {exc}"
        )
        raise self.retry(exc=exc, countdown=600)


@shared_task(
    name='notifications.tasks.process_pending_sms'
)
def process_pending_sms():
    """
    Process all pending SMS notifications that are ready to send.

    This task should be run every minute via Celery Beat.
    It queries for SMS with status=pending and scheduled_at <= now,
    then enqueues send_sms_task for each one.

    Returns:
        Dict with processing statistics
    """
    from notifications.models import NotificationQueue

    try:
        now = timezone.now()

        # Find pending SMS notifications that are ready to send
        pending_sms = NotificationQueue.objects.filter(
            channel='sms',
            status=NotificationQueue.Status.PENDING,
            scheduled_at__lte=now
        ).select_related('notification__recipient')[:100]

        processed_count = 0
        failed_count = 0

        for queue_entry in pending_sms:
            try:
                send_sms_task.delay(queue_entry.id)
                processed_count += 1

                logger.info(
                    f"Enqueued SMS for queue entry {queue_entry.id}"
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"Error enqueueing SMS for queue {queue_entry.id}: {e}"
                )

        logger.info(
            f"Processed pending SMS: {processed_count} enqueued, "
            f"{failed_count} failed"
        )

        return {
            'processed': processed_count,
            'failed': failed_count,
            'timestamp': now.isoformat(),
        }

    except Exception as exc:
        logger.error(f"Error in process_pending_sms: {exc}")
        return {
            'processed': 0,
            'failed': -1,
            'error': str(exc),
            'timestamp': timezone.now().isoformat(),
        }


@shared_task(
    name='notifications.tasks.retry_failed_sms'
)
def retry_failed_sms():
    """
    Find and retry SMS notifications that failed.

    This task looks for SMS in FAILED status that are within retry window
    and reschedules them with exponential backoff.

    Returns:
        Dict with retry statistics
    """
    from notifications.models import NotificationQueue
    from datetime import timedelta

    try:
        now = timezone.now()
        five_minutes_ago = now - timedelta(minutes=5)

        # Find SMS that failed or stuck in processing for > 5 minutes
        stuck_sms = NotificationQueue.objects.filter(
            channel='sms',
            status__in=[
                NotificationQueue.Status.PROCESSING,
                NotificationQueue.Status.FAILED,
            ],
            created_at__lt=five_minutes_ago
        ).select_related('notification__recipient')[:50]

        retried_count = 0

        for queue_entry in stuck_sms:
            if queue_entry.attempts >= queue_entry.max_attempts:
                continue

            try:
                # Reset to pending and schedule retry
                retry_delay = 300 * (2 ** queue_entry.attempts)
                queue_entry.status = NotificationQueue.Status.PENDING
                queue_entry.scheduled_at = now + timedelta(seconds=retry_delay)
                queue_entry.save()

                send_sms_task.apply_async(
                    args=[queue_entry.id],
                    countdown=int(retry_delay)
                )

                retried_count += 1
                logger.info(f"Rescheduled SMS retry for queue {queue_entry.id}")

            except Exception as e:
                logger.error(
                    f"Error retrying SMS for queue {queue_entry.id}: {e}"
                )

        logger.info(f"Retried {retried_count} failed SMS notifications")

        return {
            'retried': retried_count,
            'timestamp': now.isoformat(),
        }

    except Exception as exc:
        logger.error(f"Error in retry_failed_sms: {exc}")
        return {
            'retried': 0,
            'error': str(exc),
            'timestamp': timezone.now().isoformat(),
        }


@shared_task(
    name='notifications.tasks.cleanup_old_sms_queue'
)
def cleanup_old_sms_queue(days_old: int = 30):
    """
    Clean up old SMS queue entries (sent or failed).

    Removes queue entries that are:
    - Status: sent or failed
    - Age: older than days_old
    - Purpose: Free up database space

    Args:
        days_old: Delete entries older than this many days

    Returns:
        Dict with cleanup statistics
    """
    from notifications.models import NotificationQueue
    from datetime import timedelta

    try:
        cutoff_date = timezone.now() - timedelta(days=days_old)

        # Count before deletion
        count_before = NotificationQueue.objects.filter(
            channel='sms',
            status__in=[
                NotificationQueue.Status.SENT,
                NotificationQueue.Status.FAILED,
            ],
            created_at__lt=cutoff_date
        ).count()

        # Delete old entries
        deleted_count, _ = NotificationQueue.objects.filter(
            channel='sms',
            status__in=[
                NotificationQueue.Status.SENT,
                NotificationQueue.Status.FAILED,
            ],
            created_at__lt=cutoff_date
        ).delete()

        logger.info(
            f"Cleaned up {deleted_count} old SMS queue entries "
            f"(before cutoff: {count_before})"
        )

        return {
            'deleted': deleted_count,
            'before_cutoff': count_before,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Error in cleanup_old_sms_queue: {exc}")
        return {
            'deleted': 0,
            'error': str(exc),
            'timestamp': timezone.now().isoformat(),
        }
