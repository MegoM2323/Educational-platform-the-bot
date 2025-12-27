"""
API endpoints для System Monitoring Dashboard

Предоставляет real-time метрики, историческую информацию и управление алертами
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from .monitoring import system_monitor, timing_decorator


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_system_metrics_view(request):
    """
    GET /api/admin/system/metrics/

    Возвращает текущие метрики системы в реальном времени

    Response:
    {
        "success": true,
        "data": {
            "timestamp": "2025-12-27T12:34:56+00:00",
            "cpu": {
                "current_percent": 45.2,
                "avg_5min_percent": 48.5,
                "avg_15min_percent": 50.1,
                "core_count": 4,
                "frequency_mhz": 2400.5,
                "status": "healthy"
            },
            "memory": {
                "total_gb": 16.0,
                "used_gb": 8.5,
                "available_gb": 7.5,
                "used_percent": 53.1,
                "swap_total_gb": 8.0,
                "swap_used_percent": 12.5,
                "status": "healthy"
            },
            "disk": {
                "partitions": [
                    {
                        "partition": "/",
                        "total_gb": 100.0,
                        "used_gb": 65.5,
                        "free_gb": 34.5,
                        "used_percent": 65.5,
                        "status": "healthy"
                    }
                ],
                "status": "healthy"
            },
            "database": {
                "response_time_ms": 25.3,
                "status": "healthy",
                "connection_pool_size": 20
            },
            "redis": {
                "response_time_ms": 2.1,
                "is_working": true,
                "status": "healthy"
            },
            "requests": {
                "per_second": 45,
                "per_minute": 2700
            },
            "errors": {
                "errors_4xx": 10,
                "errors_5xx": 0,
                "error_rate_percent": 0.37
            },
            "latency": {
                "p50_ms": 45.2,
                "p95_ms": 125.8,
                "p99_ms": 250.3,
                "avg_ms": 78.5
            }
        }
    }
    """
    try:
        metrics = system_monitor.get_system_metrics()

        return Response({
            'success': True,
            'data': metrics
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_system_health_view(request):
    """
    GET /api/admin/system/health/

    Возвращает общий статус здоровья системы

    Query Parameters:
        - detailed (bool): Include detailed metrics (default: false)

    Response:
    {
        "success": true,
        "data": {
            "status": "green|yellow|red",
            "timestamp": "2025-12-27T12:34:56+00:00",
            "health_score": 95,  // 0-100
            "components": {
                "cpu": "healthy",
                "memory": "healthy",
                "disk": "warning",
                "database": "healthy",
                "redis": "healthy",
                "requests": "healthy",
                "errors": "healthy"
            },
            "active_alerts": 0,
            "metrics": { ... }  // if detailed=true
        }
    }
    """
    try:
        detailed = request.query_params.get('detailed', 'false').lower() == 'true'

        metrics = system_monitor.get_system_metrics()
        alerts = system_monitor.alert_system.check_thresholds(metrics)
        health_status = system_monitor.alert_system.get_health_status(metrics)

        # Calculate health score (0-100)
        total_alerts = len(alerts)
        critical_count = len([a for a in alerts if a['severity'] == 'critical'])
        warning_count = len([a for a in alerts if a['severity'] == 'warning'])
        health_score = max(0, 100 - (critical_count * 20 + warning_count * 10))

        response_data = {
            'status': health_status,
            'timestamp': metrics.get('timestamp'),
            'health_score': health_score,
            'components': {
                'cpu': metrics.get('cpu', {}).get('status', 'unknown'),
                'memory': metrics.get('memory', {}).get('status', 'unknown'),
                'disk': metrics.get('disk', {}).get('status', 'unknown'),
                'database': metrics.get('database', {}).get('status', 'unknown'),
                'redis': metrics.get('redis', {}).get('status', 'unknown'),
                'requests': metrics.get('requests', {}).get('status', 'healthy'),
                'errors': metrics.get('errors', {}).get('status', 'healthy'),
            },
            'active_alerts': len([a for a in alerts if 'cleared_at' not in a]),
        }

        if detailed:
            response_data['metrics'] = metrics
            response_data['alerts'] = alerts

        return Response({
            'success': True,
            'data': response_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminSystemAlertsView(APIView):
    """
    API для управления системными алертами

    GET /api/admin/system/alerts/ - Получить активные алерты
    GET /api/admin/system/alerts/?history=true - Получить историю алертов
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить алерты"""
        try:
            show_history = request.query_params.get('history', 'false').lower() == 'true'
            limit = int(request.query_params.get('limit', 100))

            if show_history:
                alerts = system_monitor.alert_system.get_alert_history(limit)
                alert_type = 'history'
            else:
                alerts = system_monitor.alert_system.get_active_alerts()
                alert_type = 'active'

            return Response({
                'success': True,
                'data': {
                    'type': alert_type,
                    'count': len(alerts),
                    'alerts': alerts,
                    'timestamp': timezone.now().isoformat()
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminSystemHistoryView(APIView):
    """
    API для получения исторических данных метрик

    GET /api/admin/system/history/?period=1h|24h|7d
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Получить историю метрик за указанный период

        Query Parameters:
            - period (str): '1h', '24h' или '7d' (default: '24h')

        Response:
        {
            "success": true,
            "data": {
                "period": "24h",
                "start_time": "2025-12-26T12:34:56+00:00",
                "end_time": "2025-12-27T12:34:56+00:00",
                "data_points": 1440,
                "metrics": [
                    {
                        "timestamp": "2025-12-26T12:34:56+00:00",
                        "cpu": {...},
                        "memory": {...},
                        ...
                    }
                ]
            }
        }
        """
        try:
            period = request.query_params.get('period', '24h')

            # Calculate time range
            now = timezone.now()
            if period == '1h':
                start_time = now - timedelta(hours=1)
                delta = timedelta(minutes=1)
            elif period == '7d':
                start_time = now - timedelta(days=7)
                delta = timedelta(hours=1)
            else:  # default 24h
                start_time = now - timedelta(days=1)
                delta = timedelta(minutes=10)

            # Retrieve metrics from cache
            metrics_data = []
            current_time = start_time

            while current_time <= now:
                ts_key = current_time.isoformat().replace(':', '').replace('-', '').replace('T', '_')[:15]
                cache_key = f'monitoring:metrics:{ts_key}'
                cached = cache.get(cache_key)

                if cached:
                    import json
                    try:
                        metrics_data.append(json.loads(cached) if isinstance(cached, str) else cached)
                    except (json.JSONDecodeError, TypeError):
                        pass

                current_time += delta

            return Response({
                'success': True,
                'data': {
                    'period': period,
                    'start_time': start_time.isoformat(),
                    'end_time': now.isoformat(),
                    'data_points': len(metrics_data),
                    'metrics': metrics_data[:100]  # Limit response size
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
