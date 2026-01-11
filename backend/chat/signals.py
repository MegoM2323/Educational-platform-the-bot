import logging
import asyncio
from datetime import datetime
from weakref import WeakSet
from typing import Any

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger("chat.websocket")

active_consumers: WeakSet[Any] = WeakSet()


def register_consumer(consumer):
    """Register a consumer for graceful shutdown (weak reference)"""
    active_consumers.add(consumer)
    logger.debug(f"Consumer registered: total_active={len(active_consumers)}")


def unregister_consumer(consumer):
    """Unregister a consumer (weak reference - may already be garbage collected)"""
    active_consumers.discard(consumer)
    logger.debug(f"Consumer unregistered: total_active={len(active_consumers)}")


async def shutdown_all_connections():
    """Shutdown all active WebSocket connections gracefully"""
    logger.info(f"Shutting down {len(active_consumers)} active WebSocket connections")

    if not active_consumers:
        logger.info("No active consumers to shutdown")
        return

    # Create snapshot of consumers to avoid issues if WeakSet changes during iteration
    tasks = [consumer.graceful_shutdown() for consumer in list(active_consumers)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    failed = sum(1 for r in results if isinstance(r, Exception))
    logger.info(f"Graceful shutdown completed: total={len(active_consumers)}, failed={failed}")


@receiver(post_save, sender="materials.SubjectEnrollment")
def on_subject_enrollment_change(sender, instance, created, **kwargs):
    """
    Invalidate chat permission cache when enrollment status changes.
    TTL: 60 seconds (reduced from 300) - reduces stale permission window.

    CRITICAL: Fires when:
    - New enrollment created (created=True)
    - Enrollment status changed (ACTIVE/COMPLETED)
    - Enrollment updated (e.g., start_date, end_date changes)

    Effect: Student loses chat access immediately when teacher marks enrollment non-ACTIVE.
    """
    from chat.permissions import invalidate_permission_cache

    try:
        student_user_id = instance.student.id
        teacher_id = instance.teacher.id

        invalidate_permission_cache(student_user_id, teacher_id)
        logger.debug(
            f"[T007_cache_invalidation] SubjectEnrollment changed: "
            f"student={student_user_id}, teacher={teacher_id}, status={instance.status}"
        )
    except Exception as e:
        logger.error(f"[T007_cache_invalidation] Error in on_subject_enrollment_change: {e}")


@receiver(post_delete, sender="materials.SubjectEnrollment")
def on_subject_enrollment_delete(sender, instance, **kwargs):
    """
    Invalidate chat permission cache when enrollment is deleted.
    TTL: 60 seconds - immediate cache bust on deletion.

    Effect: Student loses chat access immediately when enrollment is removed.
    """
    from chat.permissions import invalidate_permission_cache

    try:
        student_user_id = instance.student.id
        teacher_id = instance.teacher.id

        invalidate_permission_cache(student_user_id, teacher_id)
        logger.debug(
            f"[T007_cache_invalidation] SubjectEnrollment deleted: "
            f"student={student_user_id}, teacher={teacher_id}"
        )
    except Exception as e:
        logger.error(f"[T007_cache_invalidation] Error in on_subject_enrollment_delete: {e}")


@receiver(post_save, sender="accounts.StudentProfile")
def on_student_profile_change(sender, instance, created, **kwargs):
    """
    Invalidate chat permission cache when tutor or parent assignment changes.
    TTL: 60 seconds - immediate cache bust on profile update.

    CRITICAL: Fires when:
    - StudentProfile.tutor changed (tutor assigned or removed)
    - StudentProfile.parent changed (parent assigned or removed)
    - StudentProfile created (new student)

    Effect: Chat permissions immediately reflect tutor/parent assignment changes.
    """
    from chat.permissions import invalidate_permission_cache

    try:
        student_user_id = instance.user.id

        if instance.tutor:
            tutor_id = instance.tutor.id
            invalidate_permission_cache(student_user_id, tutor_id)
            logger.debug(
                f"[T007_cache_invalidation] StudentProfile.tutor changed: "
                f"student={student_user_id}, tutor={tutor_id}"
            )

        if instance.parent:
            parent_id = instance.parent.id
            invalidate_permission_cache(student_user_id, parent_id)
            logger.debug(
                f"[T007_cache_invalidation] StudentProfile.parent changed: "
                f"student={student_user_id}, parent={parent_id}"
            )
    except Exception as e:
        logger.error(f"[T007_cache_invalidation] Error in on_student_profile_change: {e}")
