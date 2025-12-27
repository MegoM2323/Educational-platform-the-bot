"""
Prometheus metrics export views for THE_BOT Platform.

Provides endpoints for Prometheus to scrape application metrics,
health checks, and system diagnostics.
"""

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection, DatabaseError
from django.core.cache import cache
from django.conf import settings
from prometheus_client import generate_latest, REGISTRY, CollectorRegistry
import psutil
import json
import os

from config.prometheus_settings import PROMETHEUS_REGISTRY


@csrf_exempt
@require_http_methods(["GET"])
def prometheus_metrics(request):
    """
    Export metrics in Prometheus format.

    This endpoint exposes all collected metrics that Prometheus
    can scrape for monitoring and alerting.

    Returns:
        HttpResponse: Metrics in Prometheus text format
    """
    try:
        # Generate metrics from both registries
        prometheus_output = generate_latest(PROMETHEUS_REGISTRY)

        return HttpResponse(
            prometheus_output,
            content_type='text/plain; charset=utf-8'
        )
    except Exception as e:
        return HttpResponse(
            f"Error generating metrics: {str(e)}",
            status=500,
            content_type='text/plain'
        )


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for load balancers and Kubernetes.

    Returns:
        JsonResponse: Health status of the application
    """
    health_status = {
        'status': 'healthy',
        'checks': {}
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['checks']['database'] = {
            'status': 'healthy',
            'response_time_ms': 0
        }
    except DatabaseError as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }

    # Check Redis/cache
    try:
        cache.set('health_check', 'ok', 1)
        value = cache.get('health_check')
        if value == 'ok':
            health_status['checks']['cache'] = {'status': 'healthy'}
        else:
            health_status['checks']['cache'] = {'status': 'unhealthy'}
    except Exception as e:
        health_status['checks']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }

    # Overall status
    if health_status['status'] == 'healthy':
        status_code = 200
    else:
        status_code = 503

    return JsonResponse(health_status, status=status_code)


@csrf_exempt
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes.

    Returns True only if service is ready to handle requests.

    Returns:
        JsonResponse: Readiness status
    """
    readiness = {
        'ready': True,
        'checks': {}
    }

    # Check if database migrations are applied
    try:
        with connection.cursor() as cursor:
            # Check if auth user table exists (migrations applied)
            cursor.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'auth_user'
            """)
            if cursor.fetchone():
                readiness['checks']['migrations'] = 'ok'
            else:
                readiness['ready'] = False
                readiness['checks']['migrations'] = 'pending'
    except Exception as e:
        readiness['ready'] = False
        readiness['checks']['migrations'] = f'error: {str(e)}'

    # Check cache availability
    try:
        cache.set('readiness_test', '1', 1)
        readiness['checks']['cache'] = 'ok'
    except Exception as e:
        readiness['ready'] = False
        readiness['checks']['cache'] = f'error: {str(e)}'

    status_code = 200 if readiness['ready'] else 503
    return JsonResponse(readiness, status=status_code)


@csrf_exempt
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check endpoint for Kubernetes.

    Returns True if service process is alive (not hung).

    Returns:
        JsonResponse: Liveness status
    """
    return JsonResponse({
        'alive': True,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    })


@csrf_exempt
@require_http_methods(["GET"])
def system_metrics(request):
    """
    Detailed system metrics endpoint.

    Returns:
        JsonResponse: System resource utilization metrics
    """
    try:
        metrics = {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
            },
            'memory': {
                'percent': psutil.virtual_memory().percent,
                'total_mb': psutil.virtual_memory().total / 1024 / 1024,
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'used_mb': psutil.virtual_memory().used / 1024 / 1024,
            },
            'disk': {
                'percent': psutil.disk_usage('/').percent,
                'total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024,
                'free_gb': psutil.disk_usage('/').free / 1024 / 1024 / 1024,
                'used_gb': psutil.disk_usage('/').used / 1024 / 1024 / 1024,
            },
            'process': {
                'pid': os.getpid(),
                'memory_percent': psutil.Process(os.getpid()).memory_percent(),
                'cpu_percent': psutil.Process(os.getpid()).cpu_percent(interval=0.1),
                'num_threads': psutil.Process(os.getpid()).num_threads(),
            }
        }
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=500
        )


@csrf_exempt
@require_http_methods(["GET"])
def analytics(request):
    """
    Application analytics endpoint.

    Returns:
        JsonResponse: Application usage and performance analytics
    """
    analytics_data = {
        'timestamp': str(__import__('datetime').datetime.utcnow()),
        'cache': {},
        'database': {},
        'performance': {}
    }

    # Cache analytics
    try:
        cache_info = cache.get_cache()
        analytics_data['cache'] = {
            'type': str(type(cache).__name__),
            'accessible': True
        }
    except Exception as e:
        analytics_data['cache']['accessible'] = False
        analytics_data['cache']['error'] = str(e)

    # Database analytics
    if settings.DEBUG:
        analytics_data['database'] = {
            'total_queries': len(connection.queries),
            'total_time_ms': sum(
                float(q.get('time', 0)) * 1000 for q in connection.queries
            )
        }
    else:
        analytics_data['database'] = {
            'queries_available_in_debug_mode_only': True
        }

    # Performance analytics
    try:
        process = psutil.Process(os.getpid())
        analytics_data['performance'] = {
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'threads': process.num_threads(),
        }
    except Exception as e:
        analytics_data['performance']['error'] = str(e)

    return JsonResponse(analytics_data)


@csrf_exempt
@require_http_methods(["GET"])
def prometheus_config(request):
    """
    Return Prometheus configuration information.

    Returns:
        JsonResponse: Prometheus exporter configuration
    """
    from config.prometheus_settings import (
        PROMETHEUS_EXPORTER_PORT,
        PROMETHEUS_METRICS_PATH,
        PROMETHEUS_RETENTION_DAYS,
        PROMETHEUS_SCRAPE_INTERVAL,
    )

    config = {
        'exporter': {
            'port': PROMETHEUS_EXPORTER_PORT,
            'metrics_path': PROMETHEUS_METRICS_PATH,
        },
        'retention': {
            'days': PROMETHEUS_RETENTION_DAYS,
        },
        'scrape': {
            'interval_seconds': PROMETHEUS_SCRAPE_INTERVAL,
        },
        'endpoints': {
            'metrics': PROMETHEUS_METRICS_PATH,
            'health': '/api/system/health/',
            'readiness': '/api/system/readiness/',
            'liveness': '/api/system/liveness/',
            'system_metrics': '/api/system/metrics/',
            'analytics': '/api/system/analytics/',
        }
    }
    return JsonResponse(config)
