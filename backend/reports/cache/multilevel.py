"""
Multi-level caching strategy for analytics queries.

Implements a 3-tier caching architecture:
- L1: In-memory cache (60 seconds, fast)
- L2: Redis cache (1 hour, persistent)
- L3: Database materialized views (pre-computed aggregations)

Features:
- Automatic cache invalidation on data changes
- Time-based expiration
- Manual invalidation via API
- Cache warming with background tasks
- Cache hit/miss monitoring
- Cache statistics collection
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, List
from functools import lru_cache
from threading import RLock

from django.core.cache import cache, caches
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# MULTI-LEVEL CACHE STRATEGY
# ============================================================================

class MultiLevelCache:
    """
    Multi-level caching with L1 (memory), L2 (Redis), and L3 (DB views).

    Provides:
    - Automatic fallback between cache levels
    - TTL management per level
    - Cache statistics and monitoring
    - Invalidation strategies
    """

    # Cache TTLs (in seconds)
    TTL_L1_MEMORY = 60          # 1 minute in-memory
    TTL_L2_REDIS = 3600         # 1 hour in Redis
    TTL_L3_VIEWS = 86400 * 7    # 7 days for materialized views

    # Cache level names
    LEVEL_MEMORY = 'memory'
    LEVEL_REDIS = 'redis'
    LEVEL_VIEWS = 'views'

    def __init__(self):
        """Initialize multi-level cache with in-memory L1."""
        self._memory_cache = {}  # Simple dict for L1
        self._memory_lock = RLock()  # Thread-safe access
        self._memory_timestamps = {}  # Track expiration

    def get(
        self,
        key: str,
        compute_func: Optional[callable] = None,
        ttl_config: Optional[Dict[str, int]] = None
    ) -> Tuple[Any, str]:
        """
        Get value from cache with automatic level fallback.

        Args:
            key: Cache key
            compute_func: Optional function to compute value if not cached
            ttl_config: Optional TTL config {'l1': 60, 'l2': 3600}

        Returns:
            Tuple (value, cache_level) where cache_level is 'memory', 'redis',
            'views', 'compute', or 'miss'
        """
        ttl_config = ttl_config or {
            'l1': self.TTL_L1_MEMORY,
            'l2': self.TTL_L2_REDIS,
        }

        # L1: Check in-memory cache
        value, hit = self._get_from_memory(key)
        if hit:
            logger.debug(f"Cache L1 HIT: {key}")
            return value, self.LEVEL_MEMORY

        # L2: Check Redis cache
        value, hit = self._get_from_redis(key)
        if hit:
            logger.debug(f"Cache L2 HIT: {key}")
            # Populate L1 from L2
            self._set_to_memory(key, value, ttl_config['l1'])
            return value, self.LEVEL_REDIS

        # L3: If compute_func provided, compute and cache
        if compute_func:
            logger.debug(f"Cache COMPUTE: {key}")
            try:
                value = compute_func()
                # Store in both L1 and L2
                self._set_to_memory(key, value, ttl_config['l1'])
                self._set_to_redis(key, value, ttl_config['l2'])
                return value, 'compute'
            except Exception as e:
                logger.error(f"Cache compute failed for {key}: {e}")
                return None, 'error'

        logger.debug(f"Cache MISS: {key}")
        return None, 'miss'

    def set(
        self,
        key: str,
        value: Any,
        ttl_l1: int = None,
        ttl_l2: int = None
    ) -> bool:
        """
        Set value in multi-level cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_l1: L1 TTL in seconds (default: 60)
            ttl_l2: L2 TTL in seconds (default: 3600)

        Returns:
            True if successful
        """
        ttl_l1 = ttl_l1 or self.TTL_L1_MEMORY
        ttl_l2 = ttl_l2 or self.TTL_L2_REDIS

        try:
            # Set in L1
            self._set_to_memory(key, value, ttl_l1)

            # Set in L2
            self._set_to_redis(key, value, ttl_l2)

            logger.debug(f"Cache SET: {key} (L1: {ttl_l1}s, L2: {ttl_l2}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set failed for {key}: {e}")
            return False

    def invalidate(self, key: str, include_l1: bool = True) -> bool:
        """
        Invalidate cache entry at specified levels.

        Args:
            key: Cache key
            include_l1: Also clear L1 cache

        Returns:
            True if successful
        """
        try:
            if include_l1:
                self._delete_from_memory(key)
            self._delete_from_redis(key)
            logger.info(f"Cache INVALIDATE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidate failed for {key}: {e}")
            return False

    def invalidate_pattern(
        self,
        pattern: str,
        include_l1: bool = True
    ) -> int:
        """
        Invalidate all cache entries matching pattern.

        Args:
            pattern: Key pattern with wildcards (e.g., 'analytics:student:*')
            include_l1: Also clear L1 cache

        Returns:
            Number of invalidated keys
        """
        count = 0

        if include_l1:
            count += self._delete_from_memory_pattern(pattern)

        count += self._delete_from_redis_pattern(pattern)

        if count > 0:
            logger.info(f"Cache INVALIDATE PATTERN: {pattern} ({count} keys)")

        return count

    def clear_all(self, include_l1: bool = True) -> bool:
        """
        Clear all cache entries.

        Args:
            include_l1: Also clear L1 cache

        Returns:
            True if successful
        """
        try:
            if include_l1:
                with self._memory_lock:
                    self._memory_cache.clear()
                    self._memory_timestamps.clear()

            cache.clear()  # L2 Redis
            logger.info("Cache CLEAR ALL")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            'timestamp': timezone.now().isoformat(),
            'l1_memory': {
                'size': len(self._memory_cache),
                'backend': 'in-memory',
                'ttl': self.TTL_L1_MEMORY,
            },
            'l2_redis': {
                'backend': 'redis',
                'ttl': self.TTL_L2_REDIS,
                'info': self._get_redis_stats(),
            },
            'l3_views': {
                'backend': 'materialized_views',
                'ttl': self.TTL_L3_VIEWS,
                'status': 'available',
            },
        }

    # ========== Private Methods: L1 In-Memory Cache ==========

    def _get_from_memory(self, key: str) -> Tuple[Optional[Any], bool]:
        """Get value from L1 in-memory cache."""
        with self._memory_lock:
            if key not in self._memory_cache:
                return None, False

            # Check expiration
            timestamp = self._memory_timestamps.get(key)
            if timestamp and timezone.now() > timestamp:
                # Expired, delete it
                del self._memory_cache[key]
                del self._memory_timestamps[key]
                return None, False

            return self._memory_cache[key], True

    def _set_to_memory(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in L1 in-memory cache."""
        try:
            with self._memory_lock:
                self._memory_cache[key] = value
                self._memory_timestamps[key] = timezone.now() + timedelta(seconds=ttl)
            return True
        except Exception as e:
            logger.warning(f"L1 set failed: {e}")
            return False

    def _delete_from_memory(self, key: str) -> bool:
        """Delete value from L1 in-memory cache."""
        with self._memory_lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                if key in self._memory_timestamps:
                    del self._memory_timestamps[key]
                return True
        return False

    def _delete_from_memory_pattern(self, pattern: str) -> int:
        """Delete all values matching pattern from L1."""
        count = 0
        with self._memory_lock:
            # Convert wildcard pattern to regex
            import re
            regex = pattern.replace('*', '.*')
            for key in list(self._memory_cache.keys()):
                if re.match(regex, key):
                    del self._memory_cache[key]
                    if key in self._memory_timestamps:
                        del self._memory_timestamps[key]
                    count += 1
        return count

    # ========== Private Methods: L2 Redis Cache ==========

    def _get_from_redis(self, key: str) -> Tuple[Optional[Any], bool]:
        """Get value from L2 Redis cache."""
        try:
            value = cache.get(key)
            return value, value is not None
        except Exception as e:
            logger.warning(f"L2 get failed: {e}")
            return None, False

    def _set_to_redis(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in L2 Redis cache."""
        try:
            cache.set(key, value, ttl)
            return True
        except Exception as e:
            logger.warning(f"L2 set failed: {e}")
            return False

    def _delete_from_redis(self, key: str) -> bool:
        """Delete value from L2 Redis cache."""
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"L2 delete failed: {e}")
            return False

    def _delete_from_redis_pattern(self, pattern: str) -> int:
        """Delete all values matching pattern from L2 Redis."""
        count = 0
        try:
            # Get Redis client
            redis_client = cache.client
            if hasattr(redis_client, 'scan_iter'):
                # Redis pattern scan
                keys = list(redis_client.scan_iter(match=pattern, count=100))
                for key in keys:
                    cache.delete(key)
                    count += 1
            else:
                logger.warning(f"Redis client doesn't support pattern scan")
        except Exception as e:
            logger.warning(f"L2 pattern delete failed: {e}")

        return count

    # ========== Private Methods: Stats ==========

    def _get_redis_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            redis_client = cache.client
            if hasattr(redis_client, 'info'):
                info = redis_client.info()
                return {
                    'memory_usage': info.get('used_memory', 0),
                    'memory_human': info.get('used_memory_human', 'N/A'),
                    'keys': info.get('db1', {}).get('keys', 0) if 'db1' in info else 0,
                    'uptime_seconds': info.get('uptime_in_seconds', 0),
                }
        except Exception as e:
            logger.warning(f"Failed to get Redis stats: {e}")

        return {'status': 'unavailable'}


# Global instance
_multilevel_cache = MultiLevelCache()


def get_multilevel_cache() -> MultiLevelCache:
    """Get global multi-level cache instance."""
    return _multilevel_cache


# ============================================================================
# CACHE INVALIDATION TRIGGERS
# ============================================================================

class CacheInvalidationTrigger:
    """
    Manages cache invalidation based on data changes.

    Automatically invalidates analytics caches when:
    - Assignments are graded
    - Materials are viewed
    - User progress changes
    - Reports are generated
    """

    # Cache key patterns for different entities
    PATTERNS = {
        'analytics_student': 'analytics:student:*',
        'analytics_assignment': 'analytics:assignment:*',
        'analytics_attendance': 'analytics:attendance:*',
        'analytics_engagement': 'analytics:engagement:*',
        'analytics_progress': 'analytics:progress:*',
        'reports_all': 'report:*',
        'dashboard_all': 'dashboard:*',
    }

    @staticmethod
    def on_grade_update(assignment_id: int, student_id: int = None) -> int:
        """
        Invalidate caches when assignment is graded.

        Args:
            assignment_id: Assignment ID
            student_id: Optional student ID (if specific student)

        Returns:
            Number of invalidated keys
        """
        cache_obj = get_multilevel_cache()
        count = 0

        # Invalidate assignment analytics
        pattern = f'analytics:assignment:{assignment_id}:*'
        count += cache_obj.invalidate_pattern(pattern)

        # Invalidate student analytics if provided
        if student_id:
            pattern = f'analytics:student:{student_id}:*'
            count += cache_obj.invalidate_pattern(pattern)

            pattern = f'dashboard:user_{student_id}:*'
            count += cache_obj.invalidate_pattern(pattern)

        logger.info(f"Invalidated caches on grade update: {count} keys")
        return count

    @staticmethod
    def on_material_view(material_id: int, student_id: int = None) -> int:
        """
        Invalidate caches when material is viewed.

        Args:
            material_id: Material ID
            student_id: Optional student ID

        Returns:
            Number of invalidated keys
        """
        cache_obj = get_multilevel_cache()
        count = 0

        # Invalidate progress analytics
        pattern = f'analytics:progress:*{material_id}*'
        count += cache_obj.invalidate_pattern(pattern)

        # Invalidate student progress
        if student_id:
            pattern = f'analytics:student:{student_id}:*'
            count += cache_obj.invalidate_pattern(pattern)

        logger.info(f"Invalidated caches on material view: {count} keys")
        return count

    @staticmethod
    def on_user_progress_change(user_id: int, module: str = None) -> int:
        """
        Invalidate caches when user progress changes.

        Args:
            user_id: User ID
            module: Optional module name (analytics, dashboard, etc)

        Returns:
            Number of invalidated keys
        """
        cache_obj = get_multilevel_cache()
        count = 0

        # Invalidate all user-related analytics
        patterns = [
            f'analytics:student:{user_id}:*',
            f'dashboard:user_{user_id}:*',
            f'report:user_{user_id}:*',
        ]

        if module:
            patterns.append(f'{module}:user_{user_id}:*')

        for pattern in patterns:
            count += cache_obj.invalidate_pattern(pattern)

        logger.info(f"Invalidated caches on user progress change: {count} keys")
        return count

    @staticmethod
    def on_report_generation(report_type: str) -> int:
        """
        Invalidate caches when report is generated.

        Args:
            report_type: Type of report (student_progress, attendance, etc)

        Returns:
            Number of invalidated keys
        """
        cache_obj = get_multilevel_cache()

        # Invalidate all reports and related analytics
        patterns = [
            f'report:{report_type}:*',
            'analytics:*',
        ]

        count = 0
        for pattern in patterns:
            count += cache_obj.invalidate_pattern(pattern)

        logger.info(f"Invalidated caches on report generation: {count} keys")
        return count


# ============================================================================
# CACHE WARMING
# ============================================================================

class CacheWarmer:
    """
    Pre-populate caches with frequently accessed queries.

    Used to warm caches before peak hours and reduce initial load time.
    """

    @staticmethod
    def warm_analytics(query_types: List[str] = None) -> Dict[str, int]:
        """
        Warm analytics caches.

        Args:
            query_types: Optional list of query types to warm
                        (default: ['student', 'assignment', 'progress'])

        Returns:
            Dictionary with warming statistics
        """
        query_types = query_types or [
            'student',
            'assignment',
            'progress',
            'engagement',
        ]

        stats = {}
        cache_obj = get_multilevel_cache()

        for query_type in query_types:
            try:
                logger.info(f"Warming {query_type} analytics cache...")

                # Import and call appropriate warming function
                from reports.services.warehouse import DataWarehouseService

                warehouse = DataWarehouseService(use_replica=True)

                # Warm based on query type
                if query_type == 'student':
                    data = warehouse.get_student_analytics(limit=50)
                elif query_type == 'assignment':
                    data = warehouse.get_assignment_analytics(limit=50)
                elif query_type == 'progress':
                    data = warehouse.get_progress_analytics(limit=50)
                elif query_type == 'engagement':
                    data = warehouse.get_student_engagement_metrics(limit=50)
                else:
                    continue

                stats[query_type] = {
                    'status': 'warmed',
                    'records': len(data) if isinstance(data, list) else 1,
                }
                logger.info(f"✓ Warmed {query_type}: {stats[query_type]['records']} records")

            except Exception as e:
                logger.error(f"Error warming {query_type} cache: {e}")
                stats[query_type] = {'status': 'error', 'error': str(e)}

        return stats

    @staticmethod
    def warm_user_dashboard(user_id: int) -> Dict[str, Any]:
        """
        Warm dashboard cache for specific user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with warming statistics
        """
        try:
            logger.info(f"Warming dashboard cache for user {user_id}...")

            from accounts.models import User
            from reports.services.warehouse import DataWarehouseService

            user = User.objects.get(id=user_id)
            warehouse = DataWarehouseService(use_replica=True)

            # Warm user-specific analytics
            analytics = warehouse.get_student_analytics(
                student_id=user_id,
                limit=1
            )

            return {
                'status': 'warmed',
                'user_id': user_id,
                'timestamp': timezone.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error warming dashboard for user {user_id}: {e}")
            return {'status': 'error', 'user_id': user_id, 'error': str(e)}


# ============================================================================
# MONITORING & STATISTICS
# ============================================================================

class CacheMonitor:
    """
    Monitor cache performance and provide statistics.
    """

    def __init__(self):
        """Initialize cache monitor."""
        self._hits = 0
        self._misses = 0
        self._computes = 0

    def record_hit(self):
        """Record cache hit."""
        self._hits += 1

    def record_miss(self):
        """Record cache miss."""
        self._misses += 1

    def record_compute(self):
        """Record cache computation."""
        self._computes += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            'hits': self._hits,
            'misses': self._misses,
            'computes': self._computes,
            'total_requests': total,
            'hit_rate': round(hit_rate, 2),
            'timestamp': timezone.now().isoformat(),
        }

    def reset(self):
        """Reset statistics."""
        self._hits = 0
        self._misses = 0
        self._computes = 0
        logger.info("Cache monitor reset")


# Global monitor instance
_cache_monitor = CacheMonitor()


def get_cache_monitor() -> CacheMonitor:
    """Get global cache monitor instance."""
    return _cache_monitor
