"""
API Gateway Middleware for THE BOT Platform

Implements request/response transformation, authentication, and rate limiting
at the application level to complement nginx/Kong gateway layer.

Features:
- Request ID injection (X-Request-ID header for tracing)
- Request/response logging at gateway level
- API versioning support (/api/v1/, /api/v2/)
- Rate limiting per API key (not just per IP)
- Request validation (content-type, size limits)
- Response transformation (CORS headers, security headers)
- Circuit breaker pattern with fallback responses
- Request/response timing metrics
"""

import logging
import uuid
import json
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from django.utils.functional import SimpleLazyObject

from core.decorators import get_logger

# Initialize logger
logger = get_logger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Inject or forward X-Request-ID header for distributed request tracing.

    If client doesn't provide X-Request-ID, generates a new UUID.
    Forwards request ID through all downstream services.

    Headers:
    - X-Request-ID: Unique request identifier (UUID format)
    - X-Correlation-ID: Optional correlation ID for related requests
    """

    def process_request(self, request):
        """Inject request ID if not provided."""
        # Try to get existing request ID from headers
        request_id = request.META.get('HTTP_X_REQUEST_ID')

        if not request_id:
            # Generate new UUID for tracing
            request_id = str(uuid.uuid4())

        # Store request ID for later use
        request.request_id = request_id
        request.META['HTTP_X_REQUEST_ID'] = request_id

        # Correlation ID for related requests (optional)
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID', request_id)
        request.correlation_id = correlation_id

        # Record request start time for metrics
        request.gateway_start_time = time.time()

        return None

    def process_response(self, request, response):
        """Add request ID to response headers."""
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
        return response


class APIVersioningMiddleware(MiddlewareMixin):
    """
    Extract and validate API version from request path.

    Supports versions:
    - /api/v1/ → API v1 (default)
    - /api/v2/ → API v2 (beta)

    Stores version in request for use by views.
    """

    VERSION_PATTERN = {
        'v1': 1,
        'v2': 2,
        'default': 1,
    }

    def process_request(self, request):
        """Extract API version from path."""
        path = request.path
        request.api_version = self.VERSION_PATTERN['default']

        # Parse path: /api/v{N}/*
        if path.startswith('/api/'):
            parts = path.split('/')
            if len(parts) > 2 and parts[2].startswith('v'):
                version_str = parts[2]
                try:
                    # Extract version number
                    version_num = int(version_str[1:])
                    if version_num in self.VERSION_PATTERN.values():
                        request.api_version = version_num
                except (ValueError, IndexError):
                    pass

        # Add version to response headers
        return None

    def process_response(self, request, response):
        """Add API version to response headers."""
        if hasattr(request, 'api_version'):
            response['X-API-Version'] = str(request.api_version)
        return response


class RateLimitingMiddleware(MiddlewareMixin):
    """
    Rate limiting per API key and IP address.

    Strategies:
    1. Per API key (X-API-Key header): 100 req/s (configurable)
    2. Per IP (fallback): 50 req/s (configurable)
    3. Strict endpoints (auth): 5 req/m

    Uses Redis for distributed rate limiting.

    Returns 429 Too Many Requests when limit exceeded.
    """

    # Rate limit configurations
    LIMITS = {
        'default': {'requests': 100, 'period': 1},  # 100 req/s
        'ip': {'requests': 50, 'period': 1},  # 50 req/s per IP
        'api_key': {'requests': 100, 'period': 1},  # 100 req/s per key
        'auth': {'requests': 5, 'period': 60},  # 5 req/min
        'upload': {'requests': 10, 'period': 60},  # 10 req/min
    }

    # Strict endpoints requiring lower rate limits
    STRICT_ENDPOINTS = [
        '/api/auth/login',
        '/api/accounts/login',
        '/api/accounts/register',
        '/api/accounts/password-reset',
    ]

    def process_request(self, request):
        """Check rate limits."""
        # Skip rate limiting for health checks
        if request.path in ['/health', '/health/detailed', '/metrics']:
            return None

        # Determine rate limit category
        limit_key, limit_config = self._get_limit_key(request)

        # Check rate limit
        current_count = cache.get(limit_key, 0)
        limit = limit_config['requests']

        if current_count >= limit:
            return self._rate_limit_exceeded(request)

        # Increment counter
        cache.set(limit_key, current_count + 1, limit_config['period'])

        # Store limit info for response headers
        request.rate_limit_key = limit_key
        request.rate_limit_current = current_count + 1
        request.rate_limit_max = limit
        request.rate_limit_reset = limit_config['period']

        return None

    def _get_limit_key(self, request) -> tuple:
        """Determine rate limit key and config."""
        # Check for strict endpoint
        if any(request.path.startswith(ep) for ep in self.STRICT_ENDPOINTS):
            # Use stricter limits for auth endpoints
            api_key = self._get_api_key(request)
            if api_key:
                return f"ratelimit:auth:key:{api_key}", self.LIMITS['auth']
            else:
                remote_addr = self._get_client_ip(request)
                return f"ratelimit:auth:ip:{remote_addr}", self.LIMITS['auth']

        # Check for upload endpoint
        if '/upload' in request.path:
            api_key = self._get_api_key(request)
            if api_key:
                return f"ratelimit:upload:key:{api_key}", self.LIMITS['upload']
            else:
                remote_addr = self._get_client_ip(request)
                return f"ratelimit:upload:ip:{remote_addr}", self.LIMITS['upload']

        # Default limits
        api_key = self._get_api_key(request)
        if api_key:
            return f"ratelimit:key:{api_key}", self.LIMITS['api_key']
        else:
            remote_addr = self._get_client_ip(request)
            return f"ratelimit:ip:{remote_addr}", self.LIMITS['ip']

    def _get_api_key(self, request) -> Optional[str]:
        """Extract API key from request."""
        # Try multiple header sources
        return (
            request.META.get('HTTP_X_API_KEY') or
            request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '') or
            None
        )

    def _get_client_ip(self, request) -> str:
        """Extract client IP address."""
        # Check X-Forwarded-For (from reverse proxy)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        # Fallback to remote address
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _rate_limit_exceeded(self, request):
        """Return 429 Too Many Requests response."""
        response = JsonResponse(
            {
                'error': 'Too Many Requests',
                'message': 'Rate limit exceeded',
                'status': 429,
                'request_id': getattr(request, 'request_id', None),
            },
            status=429,
        )

        # Add rate limit headers
        response['Retry-After'] = str(self.LIMITS['default']['period'])
        response['X-RateLimit-Limit'] = str(self.LIMITS['default']['requests'])
        response['X-RateLimit-Remaining'] = '0'

        logger.warning(
            f"Rate limit exceeded: {request.path}",
            extra={
                'request_id': getattr(request, 'request_id', None),
                'path': request.path,
                'method': request.method,
                'ip': self._get_client_ip(request),
            }
        )

        return response

    def process_response(self, request, response):
        """Add rate limit headers to response."""
        if hasattr(request, 'rate_limit_max'):
            response['X-RateLimit-Limit'] = str(request.rate_limit_max)
            response['X-RateLimit-Remaining'] = str(
                max(0, request.rate_limit_max - request.rate_limit_current)
            )
            response['X-RateLimit-Reset'] = str(
                int(time.time()) + request.rate_limit_reset
            )

        return response


class RequestValidationMiddleware(MiddlewareMixin):
    """
    Validate incoming requests:
    - Content-Type validation for POST/PUT/PATCH
    - Request size limits
    - Content validation

    Returns 400 Bad Request or 415 Unsupported Media Type on validation failure.
    """

    ALLOWED_CONTENT_TYPES = [
        'application/json',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
    ]

    MAX_REQUEST_SIZE = 100 * 1024 * 1024  # 100 MB

    def process_request(self, request):
        """Validate request."""
        # Check request size
        content_length = request.META.get('CONTENT_LENGTH', 0)
        try:
            content_length = int(content_length)
            if content_length > self.MAX_REQUEST_SIZE:
                return self._request_too_large(request)
        except ValueError:
            pass

        # Validate content-type for POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.META.get('CONTENT_TYPE', '')

            # Extract base content-type (without charset)
            base_content_type = content_type.split(';')[0].strip()

            if content_type and not self._is_valid_content_type(base_content_type):
                return self._unsupported_media_type(request)

        return None

    def _is_valid_content_type(self, content_type: str) -> bool:
        """Check if content-type is allowed."""
        return any(
            content_type.startswith(allowed)
            for allowed in self.ALLOWED_CONTENT_TYPES
        )

    def _request_too_large(self, request):
        """Return 413 Payload Too Large response."""
        response = JsonResponse(
            {
                'error': 'Payload Too Large',
                'message': f'Request size exceeds maximum limit of {self.MAX_REQUEST_SIZE} bytes',
                'status': 413,
                'request_id': getattr(request, 'request_id', None),
            },
            status=413,
        )
        return response

    def _unsupported_media_type(self, request):
        """Return 415 Unsupported Media Type response."""
        content_type = request.META.get('CONTENT_TYPE', 'not specified')
        response = JsonResponse(
            {
                'error': 'Unsupported Media Type',
                'message': f'Content-Type "{content_type}" is not supported. '
                          f'Supported types: {", ".join(self.ALLOWED_CONTENT_TYPES)}',
                'status': 415,
                'request_id': getattr(request, 'request_id', None),
            },
            status=415,
        )
        return response


class ResponseTransformationMiddleware(MiddlewareMixin):
    """
    Add CORS headers, security headers, and gateway information to responses.

    Headers added:
    - CORS: Access-Control-* headers
    - Security: X-Content-Type-Options, X-Frame-Options, HSTS, CSP
    - Gateway: X-API-Gateway, X-Response-Time
    """

    # CORS configuration
    CORS_ALLOW_ORIGINS = [
        'http://localhost:8080',
        'http://localhost:3000',
        'http://127.0.0.1:8080',
        'http://127.0.0.1:3000',
        'https://the-bot.ru',
        'https://www.the-bot.ru',
    ]

    CORS_ALLOW_METHODS = [
        'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'
    ]

    CORS_ALLOW_HEADERS = [
        'Content-Type',
        'Authorization',
        'X-API-Key',
        'X-Request-ID',
        'X-API-Version',
    ]

    def process_response(self, request, response):
        """Transform response."""
        # Add CORS headers
        self._add_cors_headers(request, response)

        # Add security headers
        self._add_security_headers(response)

        # Add gateway headers
        self._add_gateway_headers(request, response)

        return response

    def _add_cors_headers(self, request, response):
        """Add CORS headers to response."""
        origin = request.META.get('HTTP_ORIGIN', '')

        if origin in self.CORS_ALLOW_ORIGINS or origin.startswith('http://localhost'):
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = ', '.join(self.CORS_ALLOW_METHODS)
            response['Access-Control-Allow-Headers'] = ', '.join(self.CORS_ALLOW_HEADERS)
            response['Access-Control-Max-Age'] = '3600'
            response['Access-Control-Allow-Credentials'] = 'true'

    def _add_security_headers(self, response):
        """Add security headers to response."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Content-Security-Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' wss: ws:; "
            "frame-ancestors 'none';"
        )

    def _add_gateway_headers(self, request, response):
        """Add gateway information headers."""
        response['X-API-Gateway'] = 'THE-BOT-GATEWAY/1.0'

        # Response time
        if hasattr(request, 'gateway_start_time'):
            response_time = time.time() - request.gateway_start_time
            response['X-Response-Time'] = f'{response_time:.3f}s'


class CircuitBreakerMiddleware(MiddlewareMixin):
    """
    Implement circuit breaker pattern to handle backend failures gracefully.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, return fallback response
    - HALF_OPEN: Testing if backend recovered

    Configuration:
    - Failure threshold: 10 failures in 60 seconds
    - Recovery timeout: 30 seconds
    """

    CIRCUIT_BREAKER_KEY = 'circuit_breaker_state'
    FAILURE_THRESHOLD = 10
    FAILURE_WINDOW = 60  # seconds
    RECOVERY_TIMEOUT = 30  # seconds

    def process_request(self, request):
        """Check circuit breaker state."""
        state = cache.get(self.CIRCUIT_BREAKER_KEY, 'CLOSED')
        request.circuit_breaker_state = state

        if state == 'OPEN':
            # Circuit is open, return fallback
            return self._circuit_breaker_open(request)

        return None

    def _circuit_breaker_open(self, request):
        """Return fallback response when circuit is open."""
        response = JsonResponse(
            {
                'error': 'Service Temporarily Unavailable',
                'message': 'The API is currently unable to process requests. '
                          'Please try again in a few moments.',
                'status': 503,
                'request_id': getattr(request, 'request_id', None),
            },
            status=503,
        )

        response['Retry-After'] = '30'
        response['X-Circuit-Breaker'] = 'OPEN'

        logger.warning(
            'Circuit breaker is OPEN',
            extra={
                'request_id': getattr(request, 'request_id', None),
                'path': request.path,
            }
        )

        return response

    def record_failure(self, request):
        """Record a failure for circuit breaker."""
        failure_key = f'{self.CIRCUIT_BREAKER_KEY}:failures'

        # Get current failure count
        failures = cache.get(failure_key, 0)
        failures += 1

        # Set/update failure count
        cache.set(failure_key, failures, self.FAILURE_WINDOW)

        # Check if threshold exceeded
        if failures >= self.FAILURE_THRESHOLD:
            cache.set(self.CIRCUIT_BREAKER_KEY, 'OPEN', self.RECOVERY_TIMEOUT)
            logger.error(
                f'Circuit breaker opened: {failures} failures detected',
                extra={'request_id': getattr(request, 'request_id', None)}
            )

    def record_success(self, request):
        """Record a success and reset circuit breaker."""
        failure_key = f'{self.CIRCUIT_BREAKER_KEY}:failures'
        cache.delete(failure_key)
        cache.set(self.CIRCUIT_BREAKER_KEY, 'CLOSED', 1)


class GatewayLoggingMiddleware(MiddlewareMixin):
    """
    Log all API requests and responses at gateway level.

    Logs:
    - Request details (method, path, headers, size)
    - Response details (status, size, time)
    - Performance metrics (latency, upstream time)
    - Security events (rate limits, auth failures)

    Format: JSON for machine-readable parsing
    """

    def process_request(self, request):
        """Log incoming request."""
        if self._should_log(request):
            logger.info(
                'API Request',
                extra={
                    'request_id': getattr(request, 'request_id', None),
                    'method': request.method,
                    'path': request.path,
                    'api_version': getattr(request, 'api_version', 1),
                    'remote_addr': self._get_client_ip(request),
                    'content_type': request.META.get('CONTENT_TYPE', ''),
                    'content_length': request.META.get('CONTENT_LENGTH', 0),
                }
            )

        return None

    def process_response(self, request, response):
        """Log response."""
        if self._should_log(request):
            response_time = (
                time.time() - getattr(request, 'gateway_start_time', time.time())
            )

            logger.info(
                'API Response',
                extra={
                    'request_id': getattr(request, 'request_id', None),
                    'method': request.method,
                    'path': request.path,
                    'status': response.status_code,
                    'response_time': f'{response_time:.3f}s',
                    'content_length': len(response.content),
                }
            )

        return response

    def _should_log(self, request) -> bool:
        """Check if request should be logged."""
        # Skip logging for health checks
        return request.path not in ['/health', '/health/detailed', '/metrics']

    def _get_client_ip(self, request) -> str:
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


# Export middleware for Django configuration
__all__ = [
    'RequestIDMiddleware',
    'APIVersioningMiddleware',
    'RateLimitingMiddleware',
    'RequestValidationMiddleware',
    'ResponseTransformationMiddleware',
    'CircuitBreakerMiddleware',
    'GatewayLoggingMiddleware',
]
