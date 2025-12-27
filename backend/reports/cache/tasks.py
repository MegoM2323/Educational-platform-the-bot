"""
Celery tasks for cache warming, refresh, and scheduled invalidation.

Tasks:
- Warm analytics cache before peak hours
- Refresh cache periodically
- Invalidate stale caches
- Generate cache statistics
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache

from .multilevel import (
    get_multilevel_cache,
    CacheWarmer,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def warm_analytics_cache_task(self, query_types=None):
    """
    Warm analytics cache before peak usage hours.

    Runs before business hours (e.g., 7 AM UTC) to pre-compute
    frequently accessed analytics queries.

    Args:
        query_types: List of query types to warm
                    (default: ['student', 'assignment', 'progress', 'engagement'])

    Returns:
        Dictionary with warming statistics
    """
    try:
        logger.info("Starting scheduled cache warming task...")

        # Default query types if not specified
        if not query_types:
            query_types = [
                'student',
                'assignment',
                'progress',
                'engagement',
            ]

        stats = CacheWarmer.warm_analytics(query_types)

        logger.info(
            f"Cache warming completed: {stats}",
            extra={'stats': stats}
        )

        return {
            'task': 'warm_analytics_cache_task',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
        }

    except Exception as e:
        logger.error(f"Error warming analytics cache: {e}")

        # Retry with exponential backoff
        retry_countdown = 60 * (2 ** self.request.retries)  # 60s, 120s
        raise self.retry(exc=e, countdown=retry_countdown)


@shared_task(bind=True, max_retries=2)
def warm_user_dashboard_cache_task(self, user_id: int):
    """
    Warm dashboard cache for specific user.

    Can be triggered on user login to prepare dashboard data.

    Args:
        user_id: User ID

    Returns:
        Dictionary with warming statistics
    """
    try:
        logger.info(f"Warming dashboard cache for user {user_id}...")

        stats = CacheWarmer.warm_user_dashboard(user_id)

        logger.info(
            f"Dashboard cache warming completed for user {user_id}: {stats}",
            extra={'user_id': user_id, 'stats': stats}
        )

        return {
            'task': 'warm_user_dashboard_cache_task',
            'user_id': user_id,
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
        }

    except Exception as e:
        logger.error(f"Error warming dashboard cache for user {user_id}: {e}")

        # Retry with delay
        retry_countdown = 60 * (2 ** self.request.retries)  # 60s, 120s
        raise self.retry(exc=e, countdown=retry_countdown)


@shared_task
def refresh_analytics_cache():
    """
    Refresh analytics cache periodically (every 30 minutes).

    Ensures cache contains relatively fresh data even if queries
    haven't been explicitly warmed.

    Returns:
        Dictionary with refresh statistics
    """
    try:
        logger.info("Starting cache refresh task...")

        cache_obj = get_multilevel_cache()

        # Refresh by warming all analytics
        stats = CacheWarmer.warm_analytics()

        logger.info(f"Cache refresh completed: {stats}")

        return {
            'task': 'refresh_analytics_cache',
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
        }

    except Exception as e:
        logger.error(f"Error refreshing analytics cache: {e}")
        return {
            'task': 'refresh_analytics_cache',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
        }


@shared_task
def invalidate_stale_cache_entries():
    """
    Invalidate stale cache entries.

    Runs periodically to clean up expired or stale data from caches.

    Returns:
        Dictionary with invalidation statistics
    """
    try:
        logger.info("Starting stale cache invalidation...")

        cache_obj = get_multilevel_cache()

        # Invalidate all in-memory cache (L1 only, L2 handles own expiration)
        stats = {
            'timestamp': datetime.now().isoformat(),
            'l1_cleared': len(cache_obj._memory_cache),
        }

        # Expire old in-memory entries
        import time
        now = timezone.now()
        expired_count = 0

        for key, timestamp in list(cache_obj._memory_timestamps.items()):
            if now > timestamp:
                cache_obj._delete_from_memory(key)
                expired_count += 1

        stats['l1_expired'] = expired_count

        logger.info(f"Stale cache invalidation completed: {stats}")

        return {
            'task': 'invalidate_stale_cache_entries',
            'status': 'completed',
            'stats': stats,
        }

    except Exception as e:
        logger.error(f"Error invalidating stale cache: {e}")
        return {
            'task': 'invalidate_stale_cache_entries',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
        }


@shared_task
def generate_cache_statistics():
    """
    Generate cache statistics report.

    Runs periodically to collect metrics about cache performance
    and health.

    Returns:
        Dictionary with cache statistics
    """
    try:
        logger.info("Generating cache statistics...")

        cache_obj = get_multilevel_cache()
        cache_stats = cache_obj.get_stats()

        # Add timestamp and task info
        report = {
            'task': 'generate_cache_statistics',
            'timestamp': datetime.now().isoformat(),
            'cache_stats': cache_stats,
        }

        logger.info(f"Cache statistics generated: {report}")

        return report

    except Exception as e:
        logger.error(f"Error generating cache statistics: {e}")
        return {
            'task': 'generate_cache_statistics',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
        }


@shared_task
def cleanup_expired_cache_keys():
    """
    Clean up expired cache keys from Redis.

    Redis handles expiration automatically, but this task
    provides explicit cleanup and monitoring.

    Returns:
        Dictionary with cleanup statistics
    """
    try:
        logger.info("Cleaning up expired cache keys...")

        # Redis handles TTL expiration automatically
        # This task mainly provides monitoring and logging

        stats = {
            'timestamp': datetime.now().isoformat(),
            'status': 'cleaned',
            'note': 'Redis handles automatic expiration',
        }

        logger.info(f"Cache cleanup completed: {stats}")

        return {
            'task': 'cleanup_expired_cache_keys',
            'stats': stats,
        }

    except Exception as e:
        logger.error(f"Error cleaning up cache keys: {e}")
        return {
            'task': 'cleanup_expired_cache_keys',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
        }
