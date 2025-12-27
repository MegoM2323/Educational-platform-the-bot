"""
T_ASSIGN_013: Assignment Statistics Cache Layer.

Redis-cached statistics for fast dashboard loading.
Depends on T_ASSIGN_007 (GradeDistributionAnalytics).

Features:
- Cache key: `assignment_stats:{assignment_id}`
- TTL: 5 minutes
- Cache invalidation on: grade change, new submission, peer review
- Cache warming on teacher login
- Hit rate monitoring and metrics

Cache Structure:
{
    'assignment_id': int,
    'assignment_title': str,
    'max_score': int,
    'statistics': {
        'mean': float,
        'median': float,
        'mode': float,
        'std_dev': float,
        'min': int,
        'max': int,
        'q1': float,
        'q2': float,
        'q3': float,
        'sample_size': int,
    },
    'distribution': {
        'buckets': {...},
        'total': int,
        'pie_chart_data': [...]
    },
    'submission_stats': {
        'count': int,
        'late_count': int,
        'ungraded_count': int,
        'graded_count': int,
        'submission_rate': float,
    },
    'time_stats': {
        'avg_time_to_grade': float,  # in seconds
        'avg_response_time': float,  # in seconds
    },
    'cached_at': datetime,
    'hit_rate': {...}  # Filled only in hit-rate endpoint
}
"""

from typing import Any, Dict, Optional
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Avg, Count, Q
from datetime import timedelta
import logging

from assignments.models import Assignment, AssignmentSubmission

logger = logging.getLogger(__name__)


class AssignmentStatsCache:
    """
    Manages caching of assignment statistics.

    Handles:
    - Cache key generation
    - Statistics calculation and caching
    - Cache invalidation
    - Cache warming
    - Hit rate tracking
    """

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    # Cache key prefix
    CACHE_KEY_PREFIX = "assignment_stats"
    CACHE_KEY_HIT_RATE = "assignment_stats_hit_rate"

    def __init__(self, assignment_id: int):
        """
        Initialize cache manager for an assignment.

        Args:
            assignment_id: Assignment ID to cache statistics for
        """
        self.assignment_id = assignment_id
        self.cache_key = self._get_cache_key(assignment_id)
        self.hit_rate_key = self._get_hit_rate_key(assignment_id)

    @staticmethod
    def _get_cache_key(assignment_id: int) -> str:
        """Generate cache key for assignment statistics."""
        return f"{AssignmentStatsCache.CACHE_KEY_PREFIX}:{assignment_id}"

    @staticmethod
    def _get_hit_rate_key(assignment_id: int) -> str:
        """Generate cache key for hit rate metrics."""
        return f"{AssignmentStatsCache.CACHE_KEY_HIT_RATE}:{assignment_id}"

    def get_or_calculate(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get cached statistics or calculate and cache them.

        Args:
            analytics_data: Pre-calculated analytics data from GradeDistributionAnalytics

        Returns:
            Complete statistics dict with cached timestamp
        """
        # Try to get from cache
        cached = cache.get(self.cache_key)
        if cached is not None:
            self._record_cache_hit()
            logger.debug(f"Cache HIT for assignment {self.assignment_id}")
            return cached

        # Calculate stats if not cached
        self._record_cache_miss()
        logger.debug(f"Cache MISS for assignment {self.assignment_id}")

        # Build extended stats
        stats = self._build_extended_stats(analytics_data)

        # Cache the result
        cache.set(self.cache_key, stats, self.CACHE_TTL)
        logger.info(f"Cached statistics for assignment {self.assignment_id} (TTL: {self.CACHE_TTL}s)")

        return stats

    def _build_extended_stats(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build extended statistics including submission and time stats.

        Args:
            analytics_data: Base analytics from GradeDistributionAnalytics

        Returns:
            Extended statistics dict
        """
        try:
            assignment = Assignment.objects.get(id=self.assignment_id)
        except Assignment.DoesNotExist:
            logger.warning(f"Assignment {self.assignment_id} not found")
            return analytics_data

        # Build stats from analytics
        stats = {
            **analytics_data,
            'submission_stats': self._calculate_submission_stats(assignment),
            'time_stats': self._calculate_time_stats(assignment),
            'cached_at': timezone.now().isoformat(),
        }

        return stats

    def _calculate_submission_stats(self, assignment: Assignment) -> Dict[str, Any]:
        """
        Calculate submission-related statistics.

        Args:
            assignment: Assignment instance

        Returns:
            Submission statistics dict
        """
        submissions = AssignmentSubmission.objects.filter(assignment=assignment)

        total_count = submissions.count()
        late_count = submissions.filter(is_late=True).count()
        ungraded_count = submissions.exclude(status=AssignmentSubmission.Status.GRADED).count()
        graded_count = submissions.filter(status=AssignmentSubmission.Status.GRADED).count()

        assigned_count = assignment.assigned_to.count()
        submission_rate = (total_count / assigned_count * 100) if assigned_count > 0 else 0

        return {
            'count': total_count,
            'late_count': late_count,
            'ungraded_count': ungraded_count,
            'graded_count': graded_count,
            'assigned_count': assigned_count,
            'submission_rate': round(submission_rate, 2),
        }

    def _calculate_time_stats(self, assignment: Assignment) -> Dict[str, Optional[float]]:
        """
        Calculate time-related statistics.

        Args:
            assignment: Assignment instance

        Returns:
            Time statistics dict (avg time to grade, response time)
        """
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment,
            status=AssignmentSubmission.Status.GRADED,
            graded_at__isnull=False,
            submitted_at__isnull=False
        )

        if not submissions.exists():
            return {
                'avg_time_to_grade': None,
                'avg_response_time': None,
            }

        # Calculate time to grade (from submission to grading)
        total_time_to_grade = timedelta(seconds=0)
        count = 0

        for submission in submissions:
            if submission.graded_at and submission.submitted_at:
                time_diff = submission.graded_at - submission.submitted_at
                total_time_to_grade += time_diff
                count += 1

        avg_time_to_grade = None
        avg_response_time = None

        if count > 0:
            avg_seconds = total_time_to_grade.total_seconds() / count
            avg_time_to_grade = round(avg_seconds, 2)
            avg_response_time = round(avg_seconds, 2)  # Same as avg time to grade

        return {
            'avg_time_to_grade': avg_time_to_grade,
            'avg_response_time': avg_response_time,
        }

    def invalidate(self):
        """Invalidate cached statistics for this assignment."""
        cache.delete(self.cache_key)
        logger.info(f"Invalidated cache for assignment {self.assignment_id}")

    def get_hit_rate(self) -> Dict[str, Any]:
        """
        Get cache hit rate metrics for this assignment.

        Returns:
            Dict with hits, misses, and ratio
        """
        hit_rate_data = cache.get(self.hit_rate_key) or {
            'hits': 0,
            'misses': 0,
        }

        hits = hit_rate_data.get('hits', 0)
        misses = hit_rate_data.get('misses', 0)
        total = hits + misses

        ratio = (hits / total * 100) if total > 0 else 0

        return {
            'hits': hits,
            'misses': misses,
            'total': total,
            'hit_rate_percentage': round(ratio, 2),
            'cache_key': self.cache_key,
            'ttl_seconds': self.CACHE_TTL,
        }

    def _record_cache_hit(self):
        """Record cache hit for metrics."""
        hit_rate_data = cache.get(self.hit_rate_key) or {
            'hits': 0,
            'misses': 0,
        }
        hit_rate_data['hits'] = hit_rate_data.get('hits', 0) + 1
        # Store hit rate data with longer TTL (24 hours)
        cache.set(self.hit_rate_key, hit_rate_data, 86400)

    def _record_cache_miss(self):
        """Record cache miss for metrics."""
        hit_rate_data = cache.get(self.hit_rate_key) or {
            'hits': 0,
            'misses': 0,
        }
        hit_rate_data['misses'] = hit_rate_data.get('misses', 0) + 1
        # Store hit rate data with longer TTL (24 hours)
        cache.set(self.hit_rate_key, hit_rate_data, 86400)

    @staticmethod
    def invalidate_assignment(assignment_id: int):
        """
        Static method to invalidate cache for a specific assignment.

        Args:
            assignment_id: Assignment ID to invalidate
        """
        cache_key = AssignmentStatsCache._get_cache_key(assignment_id)
        cache.delete(cache_key)
        logger.info(f"Invalidated cache for assignment {assignment_id}")

    @staticmethod
    def warm_cache(assignment_ids: list, batch_size: int = 10) -> Dict[str, Any]:
        """
        Warm cache for multiple assignments.

        Useful for preloading stats for teacher's assignments on login.

        Args:
            assignment_ids: List of assignment IDs to warm cache for
            batch_size: Number of assignments to process at once

        Returns:
            Dict with warming results
        """
        from assignments.services.analytics import GradeDistributionAnalytics
        from assignments.tasks import warm_assignment_cache_async

        results = {
            'total': len(assignment_ids),
            'warmed': 0,
            'failed': 0,
            'async_scheduled': False,
        }

        # Estimate time needed
        estimated_time = len(assignment_ids) * 0.5  # Rough estimate: 0.5s per assignment

        # If taking too long, schedule async via Celery
        if estimated_time > 2.0:
            logger.info(
                f"Estimated warming time {estimated_time}s > 2s. "
                f"Scheduling async cache warming for {len(assignment_ids)} assignments."
            )
            warm_assignment_cache_async.delay(assignment_ids)
            results['async_scheduled'] = True
            return results

        # Otherwise, warm cache synchronously
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

        logger.info(
            f"Cache warming complete: {results['warmed']} warmed, "
            f"{results['failed']} failed out of {results['total']}"
        )

        return results
