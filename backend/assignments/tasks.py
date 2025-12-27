"""
T_ASSIGN_006: Celery tasks for assignment scheduling.
T_ASSIGN_013: Celery tasks for cache warming.

Auto-publishes and auto-closes assignments based on publish_at and close_at times.
Runs every 5 minutes via Celery Beat.

Cache warming for assignment statistics:
- Preloads stats for teacher assignments on login
- Batch warming for multiple assignments
- Async processing if warming takes >2 seconds
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q

from notifications.models import Notification
from .models import Assignment

logger = logging.getLogger(__name__)


@shared_task
def auto_publish_assignments():
    """
    T_ASSIGN_006: Automatically publish pending assignments.

    Finds all draft assignments with publish_at time in the past
    and publishes them. Sends notifications to assigned students.

    Returns:
        dict: {published_count: int, failed_count: int}
    """
    now = timezone.now()

    # Find draft assignments ready to publish
    assignments_to_publish = Assignment.objects.filter(
        status=Assignment.Status.DRAFT,
        publish_at__isnull=False,
        publish_at__lte=now,
    )

    published_count = 0
    failed_count = 0

    for assignment in assignments_to_publish:
        try:
            # Update assignment status
            assignment.status = Assignment.Status.PUBLISHED
            assignment.save(update_fields=['status', 'updated_at'])

            # Send notifications to assigned students
            assigned_students = assignment.assigned_to.all()
            for student in assigned_students:
                try:
                    notification = Notification.objects.create(
                        recipient=student,
                        title=f"Задание опубликовано: {assignment.title}",
                        message=f"Задание '{assignment.title}' теперь доступно для выполнения.",
                        type=Notification.Type.ASSIGNMENT_NEW,
                        related_object_type="Assignment",
                        related_object_id=assignment.id,
                    )
                    logger.info(
                        f"Notification sent to user {student.id} "
                        f"for assignment {assignment.id}"
                    )
                except Exception as exc:
                    logger.error(
                        f"Failed to create notification for user {student.id}: {exc}"
                    )

            published_count += 1
            logger.info(f"Assignment {assignment.id} published automatically")

        except Exception as exc:
            logger.error(f"Failed to publish assignment {assignment.id}: {exc}")
            failed_count += 1

    logger.info(
        f"Auto-publish task complete: {published_count} published, "
        f"{failed_count} failed"
    )
    return {"published_count": published_count, "failed_count": failed_count}


@shared_task
def auto_close_assignments():
    """
    T_ASSIGN_006: Automatically close published assignments.

    Finds all published assignments with close_at time in the past
    and closes them. Sends notifications to assigned students.

    Returns:
        dict: {closed_count: int, failed_count: int}
    """
    now = timezone.now()

    # Find published assignments ready to close
    assignments_to_close = Assignment.objects.filter(
        status=Assignment.Status.PUBLISHED,
        close_at__isnull=False,
        close_at__lte=now,
    )

    closed_count = 0
    failed_count = 0

    for assignment in assignments_to_close:
        try:
            # Update assignment status
            assignment.status = Assignment.Status.CLOSED
            assignment.save(update_fields=['status', 'updated_at'])

            # Send notifications to assigned students
            assigned_students = assignment.assigned_to.all()
            for student in assigned_students:
                try:
                    notification = Notification.objects.create(
                        recipient=student,
                        title=f"Задание закрыто: {assignment.title}",
                        message=f"Задание '{assignment.title}' больше не принимает новые ответы.",
                        type=Notification.Type.ASSIGNMENT_DUE,
                        related_object_type="Assignment",
                        related_object_id=assignment.id,
                    )
                    logger.info(
                        f"Notification sent to user {student.id} "
                        f"for closed assignment {assignment.id}"
                    )
                except Exception as exc:
                    logger.error(
                        f"Failed to create notification for user {student.id}: {exc}"
                    )

            closed_count += 1
            logger.info(f"Assignment {assignment.id} closed automatically")

        except Exception as exc:
            logger.error(f"Failed to close assignment {assignment.id}: {exc}")
            failed_count += 1

    logger.info(
        f"Auto-close task complete: {closed_count} closed, "
        f"{failed_count} failed"
    )
    return {"closed_count": closed_count, "failed_count": failed_count}


@shared_task
def check_assignment_scheduling():
    """
    T_ASSIGN_006: Check both publish and close operations.

    This task runs every 5 minutes and executes both
    auto_publish_assignments() and auto_close_assignments().

    Returns:
        dict: Combined results from both tasks
    """
    logger.info("Starting assignment scheduling check...")

    try:
        publish_result = auto_publish_assignments()
        close_result = auto_close_assignments()

        combined_result = {
            "publish": publish_result,
            "close": close_result,
            "total_published": publish_result.get("published_count", 0),
            "total_closed": close_result.get("closed_count", 0),
        }

        logger.info(
            f"Assignment scheduling check complete: "
            f"published={combined_result['total_published']}, "
            f"closed={combined_result['total_closed']}"
        )

        return combined_result

    except Exception as exc:
        logger.error(f"Assignment scheduling check failed: {exc}")
        return {"error": str(exc)}


# T_ASSIGN_013: Cache warming tasks
@shared_task
def warm_assignment_cache_async(assignment_ids: list):
    """
    T_ASSIGN_013: Asynchronously warm cache for multiple assignments.

    This task is called when cache warming would take >2 seconds.
    Processes assignments in batches.

    Args:
        assignment_ids: List of assignment IDs to warm cache for

    Returns:
        dict: {total, warmed, failed, duration_seconds}
    """
    from assignments.cache.stats import AssignmentStatsCache
    from assignments.services.analytics import GradeDistributionAnalytics
    import time

    start_time = time.time()

    results = {
        'total': len(assignment_ids),
        'warmed': 0,
        'failed': 0,
    }

    logger.info(f"Starting async cache warming for {len(assignment_ids)} assignments")

    for assignment_id in assignment_ids:
        try:
            assignment = Assignment.objects.get(id=assignment_id)
            analytics = GradeDistributionAnalytics(assignment)
            analytics_data = analytics.get_analytics()

            cache_manager = AssignmentStatsCache(assignment_id)
            cache_manager.get_or_calculate(analytics_data)

            results['warmed'] += 1
            logger.debug(f"Warmed cache for assignment {assignment_id}")
        except Exception as e:
            results['failed'] += 1
            logger.error(f"Failed to warm cache for assignment {assignment_id}: {e}")

    duration = time.time() - start_time
    results['duration_seconds'] = round(duration, 2)

    logger.info(
        f"Async cache warming complete: {results['warmed']} warmed, "
        f"{results['failed']} failed out of {results['total']} "
        f"(took {duration:.2f}s)"
    )

    return results


@shared_task
def warm_teacher_assignment_cache(teacher_id: int):
    """
    T_ASSIGN_013: Warm cache for all assignments created by a teacher.

    Called when teacher logs in to preload statistics.

    Args:
        teacher_id: ID of the teacher

    Returns:
        dict: Warming results
    """
    from assignments.cache.stats import AssignmentStatsCache

    logger.info(f"Warming assignment cache for teacher {teacher_id}")

    try:
        # Get all assignments created by this teacher
        teacher_assignments = Assignment.objects.filter(
            author_id=teacher_id
        ).values_list('id', flat=True)

        assignment_ids = list(teacher_assignments[:10])  # Limit to 10 most recent

        if not assignment_ids:
            logger.info(f"No assignments found for teacher {teacher_id}")
            return {'total': 0, 'warmed': 0, 'failed': 0}

        # Use the static warm_cache method
        results = AssignmentStatsCache.warm_cache(assignment_ids)

        logger.info(f"Teacher cache warming complete for teacher {teacher_id}: {results}")

        return results

    except Exception as e:
        logger.error(f"Failed to warm teacher cache for teacher {teacher_id}: {e}")
        return {'error': str(e)}
