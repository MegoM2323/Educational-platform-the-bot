"""
Cache management API endpoints for monitoring and control.

Provides endpoints for:
- Cache statistics and monitoring
- Manual cache invalidation
- Cache warming
- Cache size management
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.core.cache import cache
from django.utils import timezone

from .multilevel import (
    get_multilevel_cache,
    CacheInvalidationTrigger,
    CacheWarmer,
    get_cache_monitor,
)

logger = logging.getLogger(__name__)


class CacheManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for analytics cache management.

    Endpoints:
    - GET /api/cache/stats/ - Cache statistics
    - GET /api/cache/health/ - Cache health check
    - POST /api/cache/warm/ - Warm analytics cache
    - DELETE /api/cache/clear/ - Clear all caches
    - DELETE /api/cache/{key}/ - Invalidate specific cache
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get detailed cache statistics.

        Returns:
            {
                'timestamp': '2025-01-15T10:30:00Z',
                'cache': {
                    'l1_memory': {'size': 50, 'backend': 'in-memory', 'ttl': 60},
                    'l2_redis': {...},
                    'l3_views': {...}
                },
                'monitor': {
                    'hits': 1250,
                    'misses': 450,
                    'computes': 30,
                    'hit_rate': 73.53
                }
            }
        """
        try:
            cache_obj = get_multilevel_cache()
            monitor = get_cache_monitor()

            return Response({
                'timestamp': timezone.now().isoformat(),
                'cache': cache_obj.get_stats(),
                'monitor': monitor.get_stats(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return Response(
                {'error': 'Failed to get cache statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def health(self, request):
        """
        Check cache health status.

        Returns:
            {
                'status': 'healthy',
                'l1_available': True,
                'l2_available': True,
                'response_time_ms': 5.2
            }
        """
        try:
            import time
            cache_obj = get_multilevel_cache()

            start = time.time()

            # Test L1
            l1_available = True
            try:
                cache_obj._set_to_memory('health_check_l1', 'ok', 10)
                cache_obj._get_from_memory('health_check_l1')
                cache_obj._delete_from_memory('health_check_l1')
            except Exception as e:
                l1_available = False
                logger.warning(f"L1 health check failed: {e}")

            # Test L2
            l2_available = True
            try:
                cache.set('health_check_l2', 'ok', 10)
                cache.get('health_check_l2')
                cache.delete('health_check_l2')
            except Exception as e:
                l2_available = False
                logger.warning(f"L2 health check failed: {e}")

            elapsed = (time.time() - start) * 1000  # Convert to ms

            return Response({
                'status': 'healthy' if l1_available and l2_available else 'degraded',
                'l1_available': l1_available,
                'l2_available': l2_available,
                'response_time_ms': round(elapsed, 2),
                'timestamp': timezone.now().isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error checking cache health: {e}")
            return Response(
                {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def warm(self, request):
        """
        Warm analytics cache with frequently accessed queries.

        Request body (optional):
        {
            'query_types': ['student', 'assignment', 'progress', 'engagement'],
            'include_dashboards': true
        }

        Returns:
            {
                'status': 'warming',
                'query_types': [...],
                'timestamp': '2025-01-15T10:30:00Z'
            }
        """
        try:
            query_types = request.data.get('query_types', None)
            include_dashboards = request.data.get('include_dashboards', False)

            logger.info(
                f"Starting cache warming for query_types: {query_types}",
                extra={'user_id': request.user.id}
            )

            # Warm analytics
            stats = CacheWarmer.warm_analytics(query_types)

            # Warm user dashboard if requested
            if include_dashboards and request.user.is_authenticated:
                dashboard_stat = CacheWarmer.warm_user_dashboard(request.user.id)
                stats['dashboard'] = dashboard_stat

            return Response({
                'status': 'warming_complete',
                'stats': stats,
                'timestamp': timezone.now().isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return Response(
                {'error': 'Failed to warm cache'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['delete'], permission_classes=[IsAdminUser])
    def clear(self, request):
        """
        Clear all cache entries (admin only).

        Warning: This will clear all cached data and may cause performance impact.

        Returns:
            {
                'status': 'cleared',
                'timestamp': '2025-01-15T10:30:00Z'
            }
        """
        try:
            cache_obj = get_multilevel_cache()

            # Clear all caches
            cleared = cache_obj.clear_all(include_l1=True)

            logger.warning(
                "Cache cleared by user",
                extra={
                    'user_id': request.user.id,
                    'username': request.user.username,
                }
            )

            return Response({
                'status': 'cleared',
                'timestamp': timezone.now().isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return Response(
                {'error': 'Failed to clear cache'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['delete'])
    def invalidate_key(self, request):
        """
        Invalidate specific cache key or pattern.

        Request body:
        {
            'key': 'analytics:student:123:*',  # Supports wildcards
            'include_l1': true  # Optional, default true
        }

        Returns:
            {
                'status': 'invalidated',
                'pattern': 'analytics:student:123:*',
                'keys_affected': 5
            }
        """
        try:
            key = request.data.get('key')
            include_l1 = request.data.get('include_l1', True)

            if not key:
                return Response(
                    {'error': 'Key is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cache_obj = get_multilevel_cache()

            # Check if it's a pattern (contains wildcard)
            if '*' in key:
                count = cache_obj.invalidate_pattern(key, include_l1=include_l1)
                return Response({
                    'status': 'invalidated',
                    'pattern': key,
                    'keys_affected': count,
                    'timestamp': timezone.now().isoformat(),
                }, status=status.HTTP_200_OK)
            else:
                cache_obj.invalidate(key, include_l1=include_l1)
                return Response({
                    'status': 'invalidated',
                    'key': key,
                    'timestamp': timezone.now().isoformat(),
                }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return Response(
                {'error': 'Failed to invalidate cache'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def invalidate_analytics(self, request):
        """
        Invalidate analytics cache after data changes.

        Request body:
        {
            'trigger': 'grade_update',  # grade_update, material_view, user_progress, report_generation
            'assignment_id': 123,  # For grade_update
            'student_id': 456,  # Optional
            'user_id': 789,  # For user_progress
            'material_id': 234,  # For material_view
            'report_type': 'student_progress'  # For report_generation
        }

        Returns:
            {
                'status': 'invalidated',
                'trigger': 'grade_update',
                'keys_affected': 12
            }
        """
        try:
            trigger = request.data.get('trigger')

            if not trigger:
                return Response(
                    {'error': 'Trigger is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            count = 0

            if trigger == 'grade_update':
                assignment_id = request.data.get('assignment_id')
                student_id = request.data.get('student_id')
                count = CacheInvalidationTrigger.on_grade_update(
                    assignment_id,
                    student_id
                )

            elif trigger == 'material_view':
                material_id = request.data.get('material_id')
                student_id = request.data.get('student_id')
                count = CacheInvalidationTrigger.on_material_view(
                    material_id,
                    student_id
                )

            elif trigger == 'user_progress':
                user_id = request.data.get('user_id')
                module = request.data.get('module')
                count = CacheInvalidationTrigger.on_user_progress_change(
                    user_id,
                    module
                )

            elif trigger == 'report_generation':
                report_type = request.data.get('report_type')
                count = CacheInvalidationTrigger.on_report_generation(report_type)

            else:
                return Response(
                    {'error': f'Unknown trigger: {trigger}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'status': 'invalidated',
                'trigger': trigger,
                'keys_affected': count,
                'timestamp': timezone.now().isoformat(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error invalidating analytics cache: {e}")
            return Response(
                {'error': 'Failed to invalidate cache'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
