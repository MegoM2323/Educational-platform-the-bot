"""
Views for cache statistics and management.

Endpoints:
- GET /api/core/cache-stats/ - Get cache statistics
- POST /api/core/cache-clear/ - Clear cache (admin only)
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache
from config.cache import CacheStatsCollector, CacheKeyBuilder

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cache_stats_view(request):
    """
    Get cache statistics.

    Returns:
        Cache statistics including hit rate, size, memory usage
    """
    try:
        stats = CacheStatsCollector.get_stats()
        return Response({
            'status': 'success',
            'cache_stats': stats,
            'timestamp': None,
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return Response(
            {'error': f'Error getting cache stats: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def cache_clear_view(request):
    """
    Clear cache entries.

    Query parameters:
        - pattern: Optional pattern to clear (e.g., 'materials:*')
        - namespace: Optional namespace to clear

    Returns:
        Success message
    """
    try:
        pattern = request.data.get('pattern')
        namespace = request.data.get('namespace')

        if pattern:
            # Redis-specific pattern deletion
            try:
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern(pattern)
                    logger.info(f"Cleared cache pattern: {pattern}")
                else:
                    logger.warning("Cache backend doesn't support pattern deletion")
            except Exception as e:
                logger.warning(f"Error deleting cache pattern: {e}")

        elif namespace:
            # Clear all cache keys in a namespace
            from config.cache import CACHE_KEY_PREFIX
            pattern = f"{CACHE_KEY_PREFIX}{namespace}:*"
            try:
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern(pattern)
                    logger.info(f"Cleared cache namespace: {namespace}")
            except Exception as e:
                logger.warning(f"Error clearing namespace: {e}")
        else:
            # Clear entire cache
            cache.clear()
            logger.info("Cleared entire cache")

        return Response({
            'status': 'success',
            'message': 'Cache cleared',
            'pattern': pattern,
            'namespace': namespace,
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return Response(
            {'error': f'Error clearing cache: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def cache_reset_stats_view(request):
    """
    Reset cache statistics counters.

    Returns:
        Success message
    """
    try:
        CacheStatsCollector.clear_stats()
        logger.info("Reset cache statistics")
        return Response({
            'status': 'success',
            'message': 'Cache statistics reset',
        })
    except Exception as e:
        logger.error(f"Error resetting cache stats: {e}")
        return Response(
            {'error': f'Error resetting cache stats: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def cache_health_view(request):
    """
    Check cache backend health.

    Returns:
        Health status of cache backend
    """
    try:
        # Test cache operations
        test_key = 'health_check_test'
        test_value = 'test_value'

        # Try to set a value
        cache.set(test_key, test_value, 10)

        # Try to get the value
        retrieved = cache.get(test_key)

        # Try to delete the value
        cache.delete(test_key)

        is_healthy = retrieved == test_value

        return Response({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'backend': cache.__class__.__name__,
            'tests': {
                'set': 'passed',
                'get': 'passed' if is_healthy else 'failed',
                'delete': 'passed',
            },
        })
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'backend': cache.__class__.__name__,
            'error': str(e),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
