"""
Correlation ID Middleware for Distributed Tracing

Captures or generates a unique correlation ID for each request and:
1. Stores it in the request object for access in views
2. Sets it in OpenTelemetry baggage for trace propagation
3. Includes it in response headers for client-side tracing
4. Logs it for debugging

Supports multiple correlation ID header formats:
- X-Correlation-ID (standard)
- X-Request-ID (AWS)
- X-Trace-ID (Google Cloud)
- X-B3-Trace-ID (Zipkin/B3)
"""

import uuid
import logging
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareNotUsed

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware:
    """
    Django middleware for correlation ID handling in distributed tracing.

    Looks for correlation ID in common headers:
    1. X-Correlation-ID
    2. X-Request-ID
    3. X-Trace-ID
    4. X-B3-Trace-ID

    Generates new UUID if not found.
    """

    # Headers checked for existing correlation ID (in order)
    CORRELATION_ID_HEADERS = [
        'HTTP_X_CORRELATION_ID',
        'HTTP_X_REQUEST_ID',
        'HTTP_X_TRACE_ID',
        'HTTP_X_B3_TRACE_ID',
    ]

    def __init__(self, get_response: Callable) -> None:
        """
        Initialize middleware.

        Args:
            get_response: Django view function
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process request and response.

        Args:
            request: Django request object

        Returns:
            Django response object
        """
        # Extract or generate correlation ID
        correlation_id = self._get_or_generate_correlation_id(request)

        # Store in request for access in views
        request.correlation_id = correlation_id

        # Set in OpenTelemetry baggage if available
        self._set_otel_baggage(correlation_id)

        # Process request
        response = self.get_response(request)

        # Add correlation ID to response headers
        response['X-Correlation-ID'] = correlation_id
        response['X-Request-ID'] = correlation_id  # AWS compatibility

        return response

    @staticmethod
    def _get_or_generate_correlation_id(request: HttpRequest) -> str:
        """
        Extract correlation ID from request headers or generate new UUID.

        Checks headers in order:
        1. X-Correlation-ID (standard)
        2. X-Request-ID (AWS)
        3. X-Trace-ID (Google Cloud)
        4. X-B3-Trace-ID (Zipkin/B3)

        Args:
            request: Django request object

        Returns:
            Correlation ID string
        """
        # Check for existing correlation ID in headers
        for header in CorrelationIDMiddleware.CORRELATION_ID_HEADERS:
            correlation_id = request.META.get(header, '').strip()
            if correlation_id:
                logger.debug(f"Found correlation ID in header {header}: {correlation_id}")
                return correlation_id

        # Generate new UUID if not found
        correlation_id = str(uuid.uuid4())
        logger.debug(f"Generated new correlation ID: {correlation_id}")

        return correlation_id

    @staticmethod
    def _set_otel_baggage(correlation_id: str) -> None:
        """
        Set correlation ID in OpenTelemetry baggage.

        This makes the correlation ID available for:
        - Automatic propagation to downstream services
        - Inclusion in all spans
        - Custom instrumentation

        Args:
            correlation_id: Correlation ID to set
        """
        try:
            from config.tracing import set_correlation_id
            set_correlation_id(correlation_id)
        except ImportError:
            # OpenTelemetry not installed
            pass
        except Exception as e:
            logger.warning(f"Failed to set OTEL correlation ID: {e}")


class CorrelationIDLoggingFilter(logging.Filter):
    """
    Logging filter to add correlation ID to all log records.

    Makes correlation ID available in log format:
    - %(correlation_id)s: Correlation ID from current request
    """

    # Thread-local storage for correlation ID
    _correlation_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to log record.

        Args:
            record: Log record to filter

        Returns:
            Always True (don't filter records)
        """
        # Try to get correlation ID from current request context
        correlation_id = self._get_correlation_id()

        # Add to log record
        record.correlation_id = correlation_id or 'N/A'

        return True

    @staticmethod
    def _get_correlation_id() -> str:
        """
        Get correlation ID from current request context.

        Attempts to retrieve from:
        1. Current thread locals (if using threading)
        2. OpenTelemetry baggage
        3. Stored instance variable

        Returns:
            Correlation ID or None
        """
        try:
            # Try OpenTelemetry baggage first
            from opentelemetry.baggage import get_baggage
            correlation_id = get_baggage('correlation_id')
            if correlation_id:
                return correlation_id
        except (ImportError, Exception):
            pass

        return CorrelationIDLoggingFilter._correlation_id

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """
        Manually set correlation ID for logging.

        Useful for background tasks or management commands
        that don't have HTTP request context.

        Args:
            correlation_id: Correlation ID to set
        """
        CorrelationIDLoggingFilter._correlation_id = correlation_id


# Configure logging filter for use in settings.py:
#
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'default': {
#             'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] [%(correlation_id)s] %(message)s',
#         },
#     },
#     'filters': {
#         'correlation_id': {
#             '()': 'config.middleware.correlation_id_middleware.CorrelationIDLoggingFilter',
#         },
#     },
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#             'formatter': 'default',
#             'filters': ['correlation_id'],
#         },
#     },
# }
#
# MIDDLEWARE = [
#     'config.middleware.correlation_id_middleware.CorrelationIDMiddleware',
#     ...
# ]
