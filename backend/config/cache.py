"""
Caching configuration and utilities for THE_BOT Platform.

This module provides:
- Multi-layer caching setup (Redis for production, LocMem for development)
- Cache key generation utilities
- Cache invalidation helpers
- Per-user cache management
- CDN header configuration
"""

import os
from typing import Optional, List, Callable
import hashlib
import logging
from functools import wraps
from django.conf import settings
from django.core.cache import cache, caches
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import decorator_from_middleware_with_args
from datetime import timedelta

logger = logging.getLogger(__name__)

# Get environment from os.environ (more reliable than settings during import)
_ENVIRONMENT = os.getenv('ENVIRONMENT', 'production').lower()

# Cache TTL Configuration (in seconds)
CACHE_TIMEOUTS = {
    'default': 300,  # 5 minutes
    'short': 60,     # 1 minute
    'medium': 600,   # 10 minutes
    'long': 3600,    # 1 hour
    'static': 86400, # 24 hours

    # Endpoint-specific TTLs
    'materials_list': 1800,      # 30 minutes
    'material_detail': 3600,     # 1 hour
    'reports': 300,              # 5 minutes
    'analytics': 1800,           # 30 minutes
    'notifications': 60,         # 1 minute
    'user_profile': 600,         # 10 minutes
    'dashboard': 300,            # 5 minutes
}

# Cache key prefix to avoid conflicts across environments
CACHE_KEY_PREFIX = f"thebot:{_ENVIRONMENT}:"


class CacheKeyBuilder:
    """Helper class for consistent cache key generation."""

    @staticmethod
    def make_key(namespace: str, *args, **kwargs) -> str:
        """
        Generate a cache key from namespace and parameters.

        Args:
            namespace: Cache namespace (e.g., 'materials')
            *args: Positional arguments for the key
            **kwargs: Keyword arguments for the key

        Returns:
            A unique cache key string
        """
        parts = [CACHE_KEY_PREFIX, namespace]

        # Add positional arguments
        for arg in args:
            if arg is None:
                parts.append('none')
            elif isinstance(arg, (str, int, float, bool)):
                parts.append(str(arg))
            else:
                # Hash complex objects
                parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            if value is None:
                parts.append(f"{key}=none")
            elif isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}={value}")
            else:
                parts.append(f"{key}={hashlib.md5(str(value).encode()).hexdigest()[:8]}")

        key_str = ":".join(parts)

        # Limit key length to 250 characters (Redis limit is 512)
        if len(key_str) > 250:
            key_str = CACHE_KEY_PREFIX + hashlib.md5(key_str.encode()).hexdigest()

        return key_str

    @staticmethod
    def user_key(namespace: str, user_id: int, *args, **kwargs) -> str:
        """Generate a per-user cache key."""
        return CacheKeyBuilder.make_key(f"user_{user_id}:{namespace}", *args, **kwargs)

    @staticmethod
    def pattern_key(namespace: str, pattern: str = "*") -> str:
        """Generate a cache key pattern for deletion."""
        return CacheKeyBuilder.make_key(namespace, pattern)


class CacheInvalidator:
    """Handle cache invalidation for data changes."""

    @staticmethod
    def invalidate_material(material_id: int):
        """Invalidate caches when a material is modified."""
        try:
            # Invalidate material-specific caches
            keys_to_delete = [
                CacheKeyBuilder.make_key("materials", "list"),
                CacheKeyBuilder.make_key("materials", "detail", material_id),
                CacheKeyBuilder.make_key("materials", "progress", material_id),
            ]

            for key in keys_to_delete:
                cache.delete(key)

            logger.info(f"Invalidated caches for material {material_id}")
        except Exception as e:
            logger.warning(f"Error invalidating material cache: {e}")

    @staticmethod
    def invalidate_user_data(user_id: int):
        """Invalidate all user-specific caches."""
        try:
            namespaces = [
                'profile',
                'dashboard',
                'notifications',
                'progress',
                'assignments',
            ]

            for namespace in namespaces:
                key = CacheKeyBuilder.user_key(namespace, user_id)
                cache.delete(key)

            logger.info(f"Invalidated all caches for user {user_id}")
        except Exception as e:
            logger.warning(f"Error invalidating user cache: {e}")

    @staticmethod
    def invalidate_assignments(assignment_id: int):
        """Invalidate caches when an assignment is modified."""
        try:
            keys_to_delete = [
                CacheKeyBuilder.make_key("assignments", "list"),
                CacheKeyBuilder.make_key("assignments", "detail", assignment_id),
                CacheKeyBuilder.make_key("assignments", "submissions", assignment_id),
            ]

            for key in keys_to_delete:
                cache.delete(key)

            logger.info(f"Invalidated caches for assignment {assignment_id}")
        except Exception as e:
            logger.warning(f"Error invalidating assignment cache: {e}")

    @staticmethod
    def clear_dashboard_cache(user_id: int):
        """Clear dashboard cache for a user."""
        try:
            key = CacheKeyBuilder.user_key("dashboard", user_id)
            cache.delete(key)
            logger.info(f"Cleared dashboard cache for user {user_id}")
        except Exception as e:
            logger.warning(f"Error clearing dashboard cache: {e}")


def cache_response(ttl: Optional[int] = None,
                  key_func: Optional[Callable] = None,
                  cache_name: str = 'default'):
    """
    Decorator to cache API response.

    Args:
        ttl: Time to live in seconds (defaults to CACHE_TIMEOUTS['default'])
        key_func: Optional function to generate cache key (receives request, *args, **kwargs)
        cache_name: Name of cache backend to use

    Example:
        @cache_response(ttl=3600)
        def get_materials(request):
            return Response(...)

        @cache_response(ttl=600, key_func=lambda r: f"dashboard_{r.user.id}")
        def dashboard(request):
            return Response(...)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Don't cache non-GET requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)

            # Don't cache unauthenticated users
            if not request.user or not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            # Don't cache requests with cache-control: no-cache
            if request.META.get('HTTP_CACHE_CONTROL') == 'no-cache':
                return view_func(request, *args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = CacheKeyBuilder.make_key(
                    view_func.__name__,
                    request.user.id,
                    request.path,
                    request.GET.urlencode() if request.GET else ""
                )

            # Check cache
            cache_instance = caches[cache_name]
            cached_response = cache_instance.get(cache_key)

            if cached_response is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_response

            # Execute view function
            logger.debug(f"Cache MISS: {cache_key}")
            response = view_func(request, *args, **kwargs)

            # Cache successful responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                timeout = ttl or CACHE_TIMEOUTS.get('default', 300)
                try:
                    cache_instance.set(cache_key, response, timeout)
                except Exception as e:
                    logger.warning(f"Error setting cache: {e}")

            return response

        return wrapper
    return decorator


def get_cache_headers(ttl: int = 300, is_private: bool = False) -> dict:
    """
    Generate appropriate Cache-Control headers.

    Args:
        ttl: Time to live in seconds
        is_private: If True, cache is private to the user

    Returns:
        Dictionary of cache headers
    """
    cache_control = []

    if is_private:
        cache_control.append('private')
    else:
        cache_control.append('public')

    cache_control.append(f'max-age={ttl}')

    return {
        'Cache-Control': ', '.join(cache_control),
        'ETag': None,  # Will be computed by middleware
        'Vary': 'Accept, Accept-Encoding, Authorization',
    }


class CacheStatsCollector:
    """Collect and report cache statistics."""

    @staticmethod
    def get_stats() -> dict:
        """Get cache statistics."""
        try:
            cache_instance = caches['default']

            # Try to get stats from Redis
            if hasattr(cache_instance, 'client'):
                info = cache_instance.client(0).info()
                return {
                    'backend': 'redis',
                    'memory_usage': info.get('used_memory', 0),
                    'memory_usage_human': info.get('used_memory_human', 'N/A'),
                    'keys_count': info.get('db' + str(cache_instance.client(0).connection_pool.connection_kwargs.get('db', 0)), {}).get('keys', 0),
                    'evicted_keys': info.get('evicted_keys', 0),
                    'hit_rate': _calculate_hit_rate(info),
                    'uptime_seconds': info.get('uptime_in_seconds', 0),
                }
            else:
                # LocMem backend stats
                return {
                    'backend': 'locmem',
                    'keys_count': len(cache_instance._cache),
                    'memory_usage': 'N/A',
                    'hit_rate': 'N/A',
                }
        except Exception as e:
            logger.warning(f"Error collecting cache stats: {e}")
            return {'error': str(e)}

    @staticmethod
    def clear_stats():
        """Clear cache statistics."""
        try:
            cache_instance = caches['default']
            if hasattr(cache_instance, 'client'):
                cache_instance.client(0).config_resetstat()
        except Exception as e:
            logger.warning(f"Error clearing cache stats: {e}")


def _calculate_hit_rate(info: dict) -> float:
    """Calculate cache hit rate from Redis info."""
    hits = info.get('keyspace_hits', 0)
    misses = info.get('keyspace_misses', 0)

    if hits + misses == 0:
        return 0.0

    return round(hits / (hits + misses) * 100, 2)


# Export configuration to Django settings
def setup_cache_config():
    """Setup cache configuration in Django settings."""
    if not hasattr(settings, 'CACHE_TIMEOUTS'):
        settings.CACHE_TIMEOUTS = CACHE_TIMEOUTS

    if not hasattr(settings, 'CACHE_KEY_PREFIX'):
        settings.CACHE_KEY_PREFIX = CACHE_KEY_PREFIX


# Initialize on import
setup_cache_config()
