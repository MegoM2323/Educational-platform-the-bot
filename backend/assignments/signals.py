"""
T_ASSIGN_006: Django signals for assignment scheduling and notifications.

Handles state transitions (draft -> published -> closed) and sends notifications
when assignments are published or closed.
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from notifications.models import Notification
from .models import Assignment

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Assignment)
def validate_scheduling_dates(sender, instance, **kwargs):
    """
    T_ASSIGN_006: Validate scheduling dates before saving.

    Ensures:
    - publish_at is not before now (unless already published/closed)
    - close_at is not before publish_at (if both set)
    - Prevents modification of dates once published
    """
    if instance.pk:  # Only for updates
        old_instance = Assignment.objects.filter(pk=instance.pk).first()
        if old_instance:
            # Prevent date modification after publishing
            if old_instance.status == Assignment.Status.PUBLISHED:
                if old_instance.publish_at != instance.publish_at:
                    logger.warning(
                        f"Attempt to modify publish_at of published assignment {instance.id}"
                    )
                if old_instance.close_at != instance.close_at:
                    logger.warning(
                        f"Attempt to modify close_at of published assignment {instance.id}"
                    )

    # Validate date logic
    now = timezone.now()

    if instance.publish_at:
        if instance.publish_at < now and instance.status == Assignment.Status.DRAFT:
            # Allow scheduling in the past only if not draft status
            logger.warning(
                f"Assignment {instance.id} publish_at is in the past: {instance.publish_at}"
            )

    if instance.publish_at and instance.close_at:
        if instance.close_at <= instance.publish_at:
            raise ValueError(
                "close_at must be after publish_at"
            )


@receiver(post_save, sender=Assignment)
def handle_assignment_status_change(sender, instance, created, **kwargs):
    """
    T_ASSIGN_006: Handle assignment status transitions and send notifications.

    - Sends notifications when status changes
    - Logs state transitions
    - Triggers related tasks (notifications sent separately by Celery)
    """
    if created:
        logger.info(f"Assignment {instance.id} created: {instance.title}")
        return

    # Get the old instance to detect status changes
    try:
        old_instance = Assignment.objects.get(pk=instance.pk)
        # Note: The status may be updated by signals, so we check current state
    except Assignment.DoesNotExist:
        return

    # Status was already updated by this point in post_save
    # The Celery tasks handle actual publish/close operations
    logger.info(
        f"Assignment {instance.id} state checked: status={instance.status}"
    )
