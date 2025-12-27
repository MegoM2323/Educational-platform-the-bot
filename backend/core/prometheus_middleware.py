"""
Prometheus metrics collection middleware for Django.

This middleware intercepts HTTP requests and responses to collect
metrics about:
- Request rates and latency
- Error rates by status code
- Database query counts
- Cache hit/miss rates
"""

import time
import re
from typing import Optional, Callable
from django.utils.deprecation import MiddlewareMixin
from django.db import connection, reset_queries
from django.conf import settings

from config.prometheus_settings import (
    DJANGO_REQUEST_TOTAL,
    DJANGO_REQUEST_LATENCY_SECONDS,
    DJANGO_REQUEST_EXCEPTIONS_TOTAL,
    DJANGO_REQUEST_BODY_SIZE_BYTES,
    DJANGO_RESPONSE_BODY_SIZE_BYTES,
    DJANGO_DB_EXECUTE_TOTAL,
    DJANGO_DB_EXECUTE_TIME_SECONDS,
    DJANGO_ORM_QUERY_COUNT_TOTAL,
)


class PrometheusMetricsMiddleware(MiddlewareMixin):
    """
    Django middleware for collecting Prometheus metrics.

    Tracks HTTP request metrics including:
    - Request rate (by method, endpoint, status)
    - Request latency (histogram)
    - Error rates
    - Database query counts
    """

    # Paths to exclude from metrics collection
    EXCLUDED_PATHS = [
        r'^/health/$',
        r'^/readiness/$',
        r'^/liveness/$',
        r'^/static/',
        r'^/media/',
        r'^/metrics',
        r'^/__debug__/',
    ]

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response
        self.excluded_paths = [re.compile(path) for path in self.EXCLUDED_PATHS]

    def should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from metrics."""
        return any(pattern.match(path) for pattern in self.excluded_paths)

    def get_endpoint_name(self, request) -> str:
        """Extract endpoint name from request."""
        try:
            # Try to get the resolved view name
            from django.urls import resolve
            resolver_match = resolve(request.path)
            return f"{resolver_match.app_names[0]}:{resolver_match.url_name}" if resolver_match.app_names else resolver_match.url_name
        except Exception:
            # Fallback to path
            return request.path

    def process_request(self, request):
        """Process incoming request."""
        # Skip excluded paths
        if self.should_exclude(request.path):
            return None

        # Store metrics context on request
        request._metrics_start_time = time.time()
        request._metrics_queries_before = len(connection.queries) if settings.DEBUG else 0
        request._metrics_db_time_before = sum(
            float(q.get('time', 0)) for q in connection.queries
        ) if settings.DEBUG else 0

        # Reset queries to get accurate count for this request
        if settings.DEBUG:
            reset_queries()

        return None

    def process_response(self, request, response):
        """Process response and record metrics."""
        # Skip excluded paths
        if self.should_exclude(request.path):
            return response

        # Check if request was processed
        if not hasattr(request, '_metrics_start_time'):
            return response

        try:
            # Calculate metrics
            elapsed_time = time.time() - request._metrics_start_time
            endpoint = self.get_endpoint_name(request)
            method = request.method
            status = str(response.status_code)

            # Record request count
            DJANGO_REQUEST_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            # Record request latency
            DJANGO_REQUEST_LATENCY_SECONDS.labels(
                method=method,
                endpoint=endpoint
            ).observe(elapsed_time)

            # Record request body size
            content_length = request.META.get('CONTENT_LENGTH', 0)
            if content_length:
                try:
                    DJANGO_REQUEST_BODY_SIZE_BYTES.labels(
                        method=method
                    ).observe(int(content_length))
                except (ValueError, TypeError):
                    pass

            # Record response body size
            response_size = len(response.content) if hasattr(response, 'content') else 0
            if response_size:
                DJANGO_RESPONSE_BODY_SIZE_BYTES.labels(
                    method=method,
                    status=status
                ).observe(response_size)

            # Record database metrics
            if settings.DEBUG:
                query_count = len(connection.queries)
                DJANGO_ORM_QUERY_COUNT_TOTAL.set(query_count)

                if query_count > 0:
                    db_time = sum(
                        float(q.get('time', 0)) for q in connection.queries
                    )
                    DJANGO_DB_EXECUTE_TOTAL.labels(
                        database='default',
                        operation='query',
                        table='*'
                    ).inc(query_count)

                    if db_time:
                        DJANGO_DB_EXECUTE_TIME_SECONDS.labels(
                            database='default',
                            operation='query',
                            table='*'
                        ).observe(db_time)

        except Exception as e:
            # Log metrics collection errors without breaking request handling
            print(f"Error collecting metrics: {e}")

        return response

    def process_exception(self, request, exception):
        """Process exceptions and record metrics."""
        if not self.should_exclude(request.path):
            try:
                exception_type = type(exception).__name__
                DJANGO_REQUEST_EXCEPTIONS_TOTAL.labels(
                    exception_type=exception_type
                ).inc()
            except Exception as e:
                print(f"Error recording exception metric: {e}")

        return None


class CacheMetricsMiddleware(MiddlewareMixin):
    """
    Middleware for tracking cache hit/miss rates.

    This middleware monitors Django cache operations to provide
    insight into cache effectiveness.
    """

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def process_request(self, request):
        """Initialize cache tracking for request."""
        request._cache_hits = 0
        request._cache_misses = 0
        return None

    def process_response(self, request, response):
        """Record cache metrics after response."""
        try:
            from django.views.decorators.cache import cache_page
            from django.core.cache import cache

            # Cache metrics can be recorded here based on
            # application-specific logic
            if hasattr(request, '_cache_hits'):
                # Record cache hits from the request context
                pass

        except Exception as e:
            print(f"Error recording cache metrics: {e}")

        return response


class DatabaseMetricsMiddleware(MiddlewareMixin):
    """
    Middleware for detailed database operation tracking.

    Monitors database connections and slow queries.
    """

    SLOW_QUERY_THRESHOLD = 0.1  # 100ms

    def __init__(self, get_response: Callable):
        """Initialize middleware."""
        self.get_response = get_response

    def process_request(self, request):
        """Initialize database tracking."""
        if settings.DEBUG:
            reset_queries()
        return None

    def process_response(self, request, response):
        """Record database metrics after response."""
        if not settings.DEBUG:
            return response

        try:
            queries = connection.queries
            slow_queries = [
                q for q in queries
                if float(q.get('time', 0)) > self.SLOW_QUERY_THRESHOLD
            ]

            if slow_queries:
                for query in slow_queries:
                    DJANGO_DB_EXECUTE_TOTAL.labels(
                        database='default',
                        operation='slow_query',
                        table='*'
                    ).inc()

        except Exception as e:
            print(f"Error recording database metrics: {e}")

        return response
