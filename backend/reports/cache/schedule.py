"""
Celery Beat schedule configuration for cache tasks.

Defines periodic cache maintenance tasks:
- Cache warming (before peak hours)
- Cache refresh (every 30 minutes)
- Stale cache invalidation (hourly)
- Cache statistics generation (every 6 hours)
"""

from celery.schedules import crontab
from datetime import timedelta

# Cache task schedule for Celery Beat
# Add to settings.CELERY_BEAT_SCHEDULE

CACHE_BEAT_SCHEDULE = {
    # Warm analytics cache at 7 AM UTC (before peak hours)
    'warm_analytics_cache': {
        'task': 'reports.cache.tasks.warm_analytics_cache_task',
        'schedule': crontab(hour=7, minute=0),  # Daily at 7 AM UTC
        'options': {
            'queue': 'default',
            'priority': 9,  # High priority
        },
        'kwargs': {
            'query_types': [
                'student',
                'assignment',
                'progress',
                'engagement',
            ],
        },
    },

    # Refresh cache every 30 minutes
    'refresh_analytics_cache': {
        'task': 'reports.cache.tasks.refresh_analytics_cache',
        'schedule': timedelta(minutes=30),
        'options': {
            'queue': 'default',
            'priority': 7,
        },
    },

    # Invalidate stale cache entries hourly
    'invalidate_stale_cache': {
        'task': 'reports.cache.tasks.invalidate_stale_cache_entries',
        'schedule': timedelta(hours=1),
        'options': {
            'queue': 'default',
            'priority': 5,
        },
    },

    # Generate cache statistics every 6 hours
    'generate_cache_stats': {
        'task': 'reports.cache.tasks.generate_cache_statistics',
        'schedule': timedelta(hours=6),
        'options': {
            'queue': 'default',
            'priority': 3,
        },
    },

    # Clean up expired cache keys every 12 hours
    'cleanup_cache_keys': {
        'task': 'reports.cache.tasks.cleanup_expired_cache_keys',
        'schedule': timedelta(hours=12),
        'options': {
            'queue': 'default',
            'priority': 3,
        },
    },
}


# Integration instructions for settings.py:
# Add to CELERY_BEAT_SCHEDULE in config/settings.py:
#
# from reports.cache.schedule import CACHE_BEAT_SCHEDULE
# CELERY_BEAT_SCHEDULE = {
#     ...existing tasks...
#     **CACHE_BEAT_SCHEDULE,
# }


# Cache warming strategy recommendations:
CACHE_WARMING_STRATEGY = {
    # Before peak hours (7 AM UTC)
    'peak_hours': {
        'start': 8,  # 8 AM UTC (peak starts)
        'end': 18,   # 6 PM UTC (peak ends)
        'warm_before': 1,  # Warm 1 hour before
        'query_types': [
            'student',
            'assignment',
            'progress',
            'engagement',
        ],
    },

    # Off-peak cache refresh (maintain freshness)
    'off_peak_refresh': {
        'interval_minutes': 30,
        'query_types': ['student', 'assignment'],
    },

    # Dashboard warming on user login (optional, can be triggered via signal)
    'user_login_warm': {
        'enabled': True,
        'delay_seconds': 5,  # Async task, 5 second delay
    },
}


# TTL recommendations per query type
RECOMMENDED_TTLS = {
    'student_analytics': 300,      # 5 minutes (frequently changes)
    'assignment_analytics': 600,   # 10 minutes
    'progress_analytics': 1800,    # 30 minutes
    'engagement_analytics': 1800,  # 30 minutes
    'dashboard': 300,              # 5 minutes
    'reports': 3600,               # 1 hour
    'materialized_views': 86400,   # 24 hours
}


def get_beat_schedule():
    """Get Celery Beat schedule dictionary."""
    return CACHE_BEAT_SCHEDULE


def get_warming_strategy():
    """Get cache warming strategy configuration."""
    return CACHE_WARMING_STRATEGY


def get_ttl_for_query(query_type: str) -> int:
    """
    Get recommended TTL for query type.

    Args:
        query_type: Type of query

    Returns:
        TTL in seconds
    """
    return RECOMMENDED_TTLS.get(query_type, 300)  # Default 5 minutes
