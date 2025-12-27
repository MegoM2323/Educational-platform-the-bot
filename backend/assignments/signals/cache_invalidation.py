"""
T_ASSIGN_013: Cache invalidation signals.

Automatically invalidates assignment statistics cache when:
- Grades change (post_save AssignmentSubmission with graded status)
- New submissions (post_save AssignmentSubmission)
- Peer reviews change (post_save PeerReview if exists)

Signal handlers ensure cache freshness without manual invalidation.

Also invalidates T_ASN_005 statistics caches:
- Overall statistics
- Per-student breakdown
- Per-question analysis
- Time spent analysis
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from assignments.models import AssignmentSubmission
from assignments.cache.stats import AssignmentStatsCache
from assignments.services.statistics import AssignmentStatisticsService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AssignmentSubmission)
def invalidate_stats_cache_on_submission_change(sender, instance, created, **kwargs):
    """
    Invalidate assignment stats cache when submission is created or updated.

    Triggered by:
    - New submission (created=True)
    - Grading (status change to GRADED)
    - Score change
    - Feedback update

    Invalidates both T_ASSIGN_013 and T_ASN_005 caches.

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
        # Invalidate T_ASSIGN_013 analytics cache
        AssignmentStatsCache.invalidate_assignment(instance.assignment_id)

        # Invalidate T_ASN_005 statistics caches
        AssignmentStatisticsService.invalidate_assignment(instance.assignment_id)

        logger.info(
            f"Invalidated all statistics caches for assignment {instance.assignment_id} "
            f"(submission {instance.id} changed, created={created})"
        )
    except Exception as e:
        logger.error(
            f"Error invalidating cache for assignment {instance.assignment_id}: {e}",
            exc_info=True
        )


@receiver(post_delete, sender=AssignmentSubmission)
def invalidate_stats_cache_on_submission_delete(sender, instance, **kwargs):
    """
    Invalidate assignment stats cache when submission is deleted.

    Invalidates both T_ASSIGN_013 and T_ASN_005 caches.

    Args:
        sender: AssignmentSubmission model
        instance: The submission instance being deleted
        **kwargs: Additional signal arguments
    """
    if not instance.assignment_id:
        logger.warning("Deleted AssignmentSubmission has no assignment_id")
        return

    try:
        # Invalidate T_ASSIGN_013 analytics cache
        AssignmentStatsCache.invalidate_assignment(instance.assignment_id)

        # Invalidate T_ASN_005 statistics caches
        AssignmentStatisticsService.invalidate_assignment(instance.assignment_id)

        logger.info(
            f"Invalidated all statistics caches for assignment {instance.assignment_id} "
            f"(submission {instance.id} deleted)"
        )
    except Exception as e:
        logger.error(
            f"Error invalidating cache for assignment {instance.assignment_id}: {e}",
            exc_info=True
        )


def invalidate_cache_for_peer_review(peer_review_instance):
    """
    Invalidate cache when a peer review is created/updated.

    This is a standalone function that can be called from PeerReview signals
    if the model exists in the project.

    Args:
        peer_review_instance: The PeerReview instance
    """
    if hasattr(peer_review_instance, 'assignment_id') and peer_review_instance.assignment_id:
        try:
            AssignmentStatsCache.invalidate_assignment(peer_review_instance.assignment_id)
            logger.info(
                f"Invalidated stats cache for assignment {peer_review_instance.assignment_id} "
                f"(peer review {peer_review_instance.id} changed)"
            )
        except Exception as e:
            logger.error(
                f"Error invalidating cache for peer review: {e}",
                exc_info=True
            )
    elif hasattr(peer_review_instance, 'submission') and peer_review_instance.submission:
        try:
            assignment_id = peer_review_instance.submission.assignment_id
            AssignmentStatsCache.invalidate_assignment(assignment_id)
            logger.info(
                f"Invalidated stats cache for assignment {assignment_id} "
                f"(peer review {peer_review_instance.id} changed)"
            )
        except Exception as e:
            logger.error(
                f"Error invalidating cache for peer review: {e}",
                exc_info=True
            )


# If PeerReview model exists, register its signals
def register_peer_review_signals():
    """
    Register cache invalidation for PeerReview model if it exists.

    This should be called from assignments/apps.py ready() method.
    """
    try:
        from assignments.models import PeerReview

        @receiver(post_save, sender=PeerReview)
        def invalidate_cache_on_peer_review_change(sender, instance, **kwargs):
            """Invalidate cache when peer review is created/updated."""
            invalidate_cache_for_peer_review(instance)

        @receiver(post_delete, sender=PeerReview)
        def invalidate_cache_on_peer_review_delete(sender, instance, **kwargs):
            """Invalidate cache when peer review is deleted."""
            invalidate_cache_for_peer_review(instance)

        logger.info("Registered cache invalidation signals for PeerReview model")
    except ImportError:
        logger.debug("PeerReview model not found, skipping its signal registration")
