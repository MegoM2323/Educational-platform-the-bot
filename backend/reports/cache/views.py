"""
API endpoints для управления кэшем отчётов.

Endpoints:
- GET /api/reports/cache/stats/ - Глобальная статистика кэша
- GET /api/reports/cache/hit-rate/ - Процент попаданий пользователя
- POST /api/reports/cache/warm/ - Предварительная загрузка кэша
- DELETE /api/reports/cache/{report_id}/ - Инвалидирование кэша отчёта
"""

import logging
from typing import List

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer, ListField, IntegerField, CharField

from .strategy import cache_strategy

logger = logging.getLogger(__name__)


class CacheStatsSerializer(Serializer):
    """Сериализатор для статистики кэша."""

    hits = IntegerField(read_only=True)
    misses = IntegerField(read_only=True)
    hit_rate = IntegerField(read_only=True)
    total_requests = IntegerField(read_only=True)


class CacheWarmSerializer(Serializer):
    """Сериализатор для предварительной загрузки кэша."""

    report_ids = ListField(child=IntegerField(), required=True)
    report_type = CharField(default="default", required=False)


class CacheControlViewSet(viewsets.ViewSet):
    """
    ViewSet для управления кэшем отчётов.

    Provides endpoints for:
    - Cache statistics and hit rate
    - Cache warming (precomputation)
    - Cache invalidation
    - Cache monitoring
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Получить глобальную статистику кэша.

        Returns:
            {
                "engine": "DjangoMemcached",
                "backend": "MemcacheCache",
                "ttl_map": {...},
                "max_size_per_user": 52428800,
                "status": "operational"
            }
        """
        try:
            stats = cache_strategy.get_cache_stats()
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Failed to get cache stats: {str(e)}",
                extra={"error": str(e)},
            )
            return Response(
                {"error": "Failed to get cache statistics"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def hit_rate(self, request):
        """
        Получить процент попаданий кэша для текущего пользователя.

        Returns:
            {
                "hits": 150,
                "misses": 50,
                "hit_rate": 75.0,
                "total_requests": 200,
                "last_updated": "2024-01-15T10:30:00Z"
            }
        """
        try:
            stats = cache_strategy.get_hit_rate(request.user.id)
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Failed to get hit rate for user {request.user.id}: {str(e)}",
                extra={"user_id": request.user.id, "error": str(e)},
            )
            return Response(
                {"error": "Failed to get cache hit rate"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def warm(self, request):
        """
        Предварительно загрузить кэш для пользователя.

        Обычно вызывается при входе учителя/преподавателя для
        быстрой загрузки часто используемых отчётов.

        Request body:
        {
            "report_ids": [1, 2, 3, 4, 5],
            "report_type": "analytics"  # optional, default: "default"
        }

        Returns:
            {
                "total": 5,
                "cached": 5,
                "failed": 0
            }
        """
        serializer = CacheWarmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_ids = serializer.validated_data.get('report_ids', [])
        report_type = serializer.validated_data.get('report_type', 'default')

        try:
            stats = cache_strategy.warm_cache_for_user(
                user_id=request.user.id,
                report_ids=report_ids,
                report_type=report_type,
            )

            logger.info(
                f"Cache warming completed for user {request.user.id}: "
                f"{stats['cached']}/{stats['total']} reports",
                extra={"user_id": request.user.id, "stats": stats},
            )

            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                f"Failed to warm cache for user {request.user.id}: {str(e)}",
                extra={"user_id": request.user.id, "error": str(e)},
            )
            return Response(
                {"error": "Failed to warm cache"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['delete'])
    def invalidate(self, request):
        """
        Инвалидировать весь кэш пользователя.

        Обычно вызывается после критических изменений данных.

        Returns:
            {
                "message": "Cache invalidated",
                "invalidated_keys": 10
            }
        """
        try:
            invalidated = cache_strategy.invalidate_user_cache(request.user.id)

            logger.info(
                f"User cache invalidated: {invalidated} keys",
                extra={"user_id": request.user.id, "invalidated": invalidated},
            )

            return Response(
                {
                    "message": "Cache invalidated",
                    "invalidated_keys": invalidated,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(
                f"Failed to invalidate cache for user {request.user.id}: {str(e)}",
                extra={"user_id": request.user.id, "error": str(e)},
            )
            return Response(
                {"error": "Failed to invalidate cache"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['delete'])
    def invalidate_report(self, request, pk=None):
        """
        Инвалидировать кэш конкретного отчёта.

        Args:
            pk: Report ID

        Returns:
            {
                "message": "Report cache invalidated",
                "report_id": 42,
                "invalidated_keys": 5
            }
        """
        report_id = pk

        try:
            invalidated = cache_strategy.invalidate_report_cache(
                report_id=report_id,
                user_id=request.user.id,
            )

            logger.info(
                f"Report cache invalidated: {invalidated} keys",
                extra={
                    "user_id": request.user.id,
                    "report_id": report_id,
                    "invalidated": invalidated,
                },
            )

            return Response(
                {
                    "message": "Report cache invalidated",
                    "report_id": report_id,
                    "invalidated_keys": invalidated,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(
                f"Failed to invalidate cache for report {report_id}: {str(e)}",
                extra={"report_id": report_id, "error": str(e)},
            )
            return Response(
                {"error": "Failed to invalidate report cache"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
