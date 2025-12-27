"""
Cache module for reports application.

Provides multi-level caching infrastructure for analytics:
- L1: In-memory cache (fast, 60 seconds)
- L2: Redis cache (persistent, 1 hour)
- L3: Database materialized views (pre-computed, 7 days)
"""

from .strategy import ReportCacheStrategy, cache_strategy
from .multilevel import (
    MultiLevelCache,
    get_multilevel_cache,
    CacheInvalidationTrigger,
    CacheWarmer,
    CacheMonitor,
    get_cache_monitor,
)
from .management import CacheManagementViewSet
from .tasks import (
    warm_analytics_cache_task,
    warm_user_dashboard_cache_task,
    refresh_analytics_cache,
    invalidate_stale_cache_entries,
    generate_cache_statistics,
    cleanup_expired_cache_keys,
)

__all__ = [
    # Legacy strategy (still used for reports)
    "ReportCacheStrategy",
    "cache_strategy",

    # Multi-level cache (new)
    "MultiLevelCache",
    "get_multilevel_cache",
    "CacheInvalidationTrigger",
    "CacheWarmer",
    "CacheMonitor",
    "get_cache_monitor",

    # Management API
    "CacheManagementViewSet",

    # Celery tasks
    "warm_analytics_cache_task",
    "warm_user_dashboard_cache_task",
    "refresh_analytics_cache",
    "invalidate_stale_cache_entries",
    "generate_cache_statistics",
    "cleanup_expired_cache_keys",
]
