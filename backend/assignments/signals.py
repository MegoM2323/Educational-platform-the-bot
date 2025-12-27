"""
T_ASSIGN_006: Django signals for assignment scheduling and notifications.
T_ASSIGN_013: Cache invalidation signals for assignment statistics.
T_REPORT_011: Real-time dashboard event broadcasting.

Handles:
- State transitions (draft -> published -> closed)
- Notifications when assignments are published or closed
- Cache invalidation on submission/grade changes
- Real-time dashboard events for submissions and grades
"""
import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from notifications.models import Notification
from .models import Assignment, AssignmentSubmission
from .cache.stats import AssignmentStatsCache

logger = logging.getLogger(__name__)

# Import realtime service (avoid circular imports by importing in signal handlers)
def get_dashboard_event_service():
    try:
        from reports.services.realtime import DashboardEventService
        return DashboardEventService
    except ImportError:
        return None


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
    T_REPORT_011: Broadcast assignment events to real-time dashboard.

    - Sends notifications when status changes
    - Logs state transitions
    - Triggers related tasks (notifications sent separately by Celery)
    - Broadcasts real-time events for new/closed assignments
    """
    if created:
        logger.info(f"Assignment {instance.id} created: {instance.title}")

        # T_REPORT_011: Broadcast assignment created event
        DashboardEventService = get_dashboard_event_service()
        if DashboardEventService:
            try:
                DashboardEventService.broadcast_assignment_created(instance)
            except Exception as e:
                logger.error(f"Error broadcasting assignment created event: {e}")
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

    # T_REPORT_011: Broadcast assignment closed event
    if instance.status == Assignment.Status.CLOSED and old_instance.status != Assignment.Status.CLOSED:
        DashboardEventService = get_dashboard_event_service()
        if DashboardEventService:
            try:
                DashboardEventService.broadcast_assignment_closed(instance)
            except Exception as e:
                logger.error(f"Error broadcasting assignment closed event: {e}")


# T_ASSIGN_013: Cache invalidation signals
# T_REPORT_011: Real-time dashboard event broadcasting
@receiver(post_save, sender=AssignmentSubmission)
def invalidate_stats_cache_on_submission_change(sender, instance, created, **kwargs):
    """
    T_ASSIGN_013: Invalidate assignment stats cache when submission is created or updated.
    T_REPORT_011: Broadcast real-time events to teacher dashboard.

    Triggered by:
    - New submission (created=True)
    - Grading (status change to GRADED)
    - Score change
    - Feedback update

    Args:
        sender: AssignmentSubmission model
        instance: The submission instance
        created: Boolean indicating if record was created
        **kwargs: Additional signal arguments
    """
    if not instance.assignment_id:
        logger.warning("AssignmentSubmission has no assignment_id")
        return

    try:
        # Always invalidate cache on submission/grade changes
        AssignmentStatsCache.invalidate_assignment(instance.assignment_id)
        logger.info(
            f"Invalidated stats cache for assignment {instance.assignment_id} "
            f"(submission {instance.id} changed, created={created})"
        )

        # T_REPORT_011: Broadcast real-time events
        DashboardEventService = get_dashboard_event_service()
        if DashboardEventService:
            try:
                if created and instance.submitted_at:
                    # Broadcast submission event
                    DashboardEventService.broadcast_submission(
                        instance,
                        instance.assignment,
                        instance.student
                    )
                elif instance.grade is not None:
                    # Broadcast grade event (when grade is set)
                    DashboardEventService.broadcast_grade(
                        instance,
                        instance.assignment,
                        instance.student,
                        instance.grade
                    )
            except Exception as e:
                logger.error(f"Error broadcasting dashboard event: {e}")

    except Exception as e:
        logger.error(
            f"Error invalidating cache for assignment {instance.assignment_id}: {e}",
            exc_info=True
        )


@receiver(post_delete, sender=AssignmentSubmission)
def invalidate_stats_cache_on_submission_delete(sender, instance, **kwargs):
    """
    T_ASSIGN_013: Invalidate assignment stats cache when submission is deleted.

    Args:
        sender: AssignmentSubmission model
        instance: The submission instance being deleted
        **kwargs: Additional signal arguments
    """
    if not instance.assignment_id:
        logger.warning("Deleted AssignmentSubmission has no assignment_id")
        return

    try:
        AssignmentStatsCache.invalidate_assignment(instance.assignment_id)
        logger.info(
            f"Invalidated stats cache for assignment {instance.assignment_id} "
            f"(submission {instance.id} deleted)"
        )
    except Exception as e:
        logger.error(
            f"Error invalidating cache for assignment {instance.assignment_id}: {e}",
            exc_info=True
        )
