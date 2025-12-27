"""
Comprehensive API rate limiting with tiered limits, sliding window algorithm,
and standard HTTP rate limit headers.

Features:
- Tiered rate limiting: anonymous (20/min), authenticated (100/min), premium (500/min)
- Endpoint-specific limits (login: 5/min, upload: 10/min, search: 30/min)
- Redis-backed sliding window algorithm for accuracy and performance
- Standard rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
- 429 Too Many Requests response with Retry-After header
- Bypass mechanism for admin/internal requests
- Comprehensive logging of rate limit violations

Rate limit tracking:
- Cache key: "rate_limit_{scope}_{identifier}"
- Value: [timestamp1, timestamp2, ...] of requests (sliding window)
- Old timestamps are automatically cleaned when checking limits
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from functools import wraps

from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.throttling import BaseThrottle
from rest_framework.response import Response
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using Redis/cache backend.

    Tracks request timestamps and enforces rate limits based on
    a rolling time window rather than fixed time buckets.
    """

    def __init__(self, key: str, limit: int, window: int):
        """
        Initialize rate limiter.

        Args:
            key: Cache key for storing request history
            limit: Maximum requests allowed in window
            window: Time window in seconds
        """
        self.key = key
        self.limit = limit
        self.window = window
        self.now = datetime.now()

    def is_allowed(self) -> Tuple[bool, Dict[str, str]]:
        """
        Check if request is allowed and return rate limit headers.

        Returns:
            Tuple of (is_allowed, headers_dict)
        """
        # Get request history from cache
        history = cache.get(self.key, [])

        # Remove old timestamps outside the window
        cutoff = self.now - timedelta(seconds=self.window)
        history = [ts for ts in history if ts > cutoff]

        # Check if limit exceeded
        if len(history) >= self.limit:
            allowed = False
        else:
            allowed = True
            # Add current request to history
            history.append(self.now)
            # Store updated history in cache
            cache.set(self.key, history, self.window)

        # Generate response headers
        headers = self._get_rate_limit_headers(history)

        return allowed, headers

    def _get_rate_limit_headers(self, history: List[datetime]) -> Dict[str, str]:
        """Generate standard rate limit headers."""
        if not history:
            reset_time = self.now + timedelta(seconds=self.window)
        else:
            # Reset time is when the oldest request leaves the window
            reset_time = history[0] + timedelta(seconds=self.window)

        remaining = max(0, self.limit - len(history))
        reset_timestamp = int(reset_time.timestamp())

        return {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_timestamp),
        }

    def get_retry_after(self) -> int:
        """Get seconds to wait before retrying (for 429 response)."""
        history = cache.get(self.key, [])
        if not history:
            return 0

        cutoff = self.now - timedelta(seconds=self.window)
        history = [ts for ts in history if ts > cutoff]

        if len(history) < self.limit:
            return 0

        # Calculate seconds until oldest request leaves window
        oldest = history[0]
        reset_time = oldest + timedelta(seconds=self.window)
        retry_after = (reset_time - self.now).total_seconds()

        return max(1, int(retry_after) + 1)


class RateLimitThrottle(BaseThrottle):
    """
    Enhanced DRF throttle class with sliding window algorithm,
    proper rate limit headers, and comprehensive logging.

    Supports tiered limits based on user authentication level.
    """

    scope = None
    _cache_key_prefix = 'rate_limit'

    def __init__(self):
        """Initialize throttle with logging."""
        super().__init__()
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')

    def get_identifier(self, request) -> str:
        """
        Get unique identifier for the request (user ID or IP).

        Returns:
            String identifier for rate limit tracking
        """
        if request.user and request.user.is_authenticated:
            return f'user_{request.user.id}'

        # Get client IP (handle X-Forwarded-For for proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')

        return f'ip_{ip}'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """
        Determine rate limit and window for this request.

        Override in subclasses to implement custom logic.

        Returns:
            Tuple of (limit, window_seconds)
        """
        # Default tiered limits
        if request.user and request.user.is_authenticated:
            # Check if premium user (future feature)
            if hasattr(request.user, 'is_premium') and request.user.is_premium:
                return (500, 60)  # Premium: 500/min
            # Check if admin (bypass)
            if request.user.is_staff or request.user.is_superuser:
                return (99999, 60)  # Admin: no limit
            # Regular authenticated user
            return (100, 60)  # Authenticated: 100/min

        # Anonymous user
        return (20, 60)  # Anonymous: 20/min

    def throttle(self, request, view) -> bool:
        """
        Implement rate limiting check.

        Returns:
            True if request is allowed, False if throttled
        """
        # Check if admin/staff (always allow)
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True

        # Get limit and window
        limit, window = self.get_limit_and_window(request)

        # Get cache key
        identifier = self.get_identifier(request)
        cache_key = f'{self._cache_key_prefix}_{self.scope}_{identifier}'

        # Check rate limit using sliding window
        limiter = SlidingWindowRateLimiter(cache_key, limit, window)
        is_allowed, headers = limiter.is_allowed()

        # Store headers for response
        self.headers = headers

        # Log rate limit violations
        if not is_allowed:
            self.logger.warning(
                f'Rate limit exceeded: scope={self.scope}, '
                f'identifier={identifier}, limit={limit}/{window}s, '
                f'path={request.path}',
                extra={
                    'scope': self.scope,
                    'identifier': identifier,
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'ip': request.META.get('REMOTE_ADDR'),
                    'path': request.path,
                }
            )
            # Store retry-after for response
            self.retry_after = limiter.get_retry_after()

        return is_allowed

    def get_headers(self) -> Dict[str, str]:
        """Return rate limit headers for response."""
        return getattr(self, 'headers', {})


class RateLimitThrottleNoStatus(RateLimitThrottle):
    """Base class for implementing throttle_classes on views."""
    pass


# Tier-based throttles

class AnonUserThrottle(RateLimitThrottle):
    """
    Rate limit for anonymous users.
    Default: 20 requests per minute (IP-based).
    """
    scope = 'anon'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Anonymous users: 20/min."""
        return (20, 60)


class AuthenticatedUserThrottle(RateLimitThrottle):
    """
    Rate limit for authenticated users.
    Default: 100 requests per minute (user-based).
    """
    scope = 'authenticated'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Authenticated users: 100/min."""
        return (100, 60)


class PremiumUserThrottle(RateLimitThrottle):
    """
    Rate limit for premium users.
    Default: 500 requests per minute (user-based).
    """
    scope = 'premium'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Premium users: 500/min."""
        if request.user and request.user.is_authenticated:
            if hasattr(request.user, 'is_premium') and request.user.is_premium:
                return (500, 60)
        # Fallback to authenticated
        return (100, 60)


class AdminThrottle(RateLimitThrottle):
    """
    Rate limit for admin users.
    Admins bypass all rate limiting.
    """
    scope = 'admin'

    def throttle(self, request, view) -> bool:
        """Admins are never throttled."""
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
        return super().throttle(request, view)


# Endpoint-specific throttles

class LoginThrottle(RateLimitThrottle):
    """
    Rate limit for login endpoint.
    Default: 5 attempts per minute (IP-based).
    Protects against brute force password attacks.
    """
    scope = 'login'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Login: 5/min."""
        return (5, 60)


class UploadThrottle(RateLimitThrottle):
    """
    Rate limit for file upload endpoints.
    Default: 10 uploads per hour (user-based).
    Prevents server storage abuse.
    """
    scope = 'upload'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Upload: 10/hour."""
        return (10, 3600)


class SearchThrottle(RateLimitThrottle):
    """
    Rate limit for search endpoints.
    Default: 30 searches per minute (user-based).
    Prevents database abuse from excessive searches.
    """
    scope = 'search'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Search: 30/min."""
        return (30, 60)


class AnalyticsThrottle(RateLimitThrottle):
    """
    Rate limit for analytics/report endpoints.
    Default: 100 requests per hour (user-based).
    Prevents excessive report generation.
    """
    scope = 'analytics'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Analytics: 100/hour."""
        return (100, 3600)


class ChatMessageThrottle(RateLimitThrottle):
    """
    Rate limit for chat message posting.
    Default: 60 messages per minute (user-based).
    Prevents chat spam and abuse.
    """
    scope = 'chat_message'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Chat message: 60/min."""
        return (60, 60)


class ChatRoomThrottle(RateLimitThrottle):
    """
    Rate limit for chat room creation.
    Default: 5 rooms per hour (user-based).
    Prevents creation spam.
    """
    scope = 'chat_room'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Chat room creation: 5/hour."""
        return (5, 3600)


class AssignmentSubmissionThrottle(RateLimitThrottle):
    """
    Rate limit for assignment submissions.
    Default: 10 submissions per hour (user-based).
    Prevents submission spam.
    """
    scope = 'assignment_submission'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Assignment submission: 10/hour."""
        return (10, 3600)


class ReportGenerationThrottle(RateLimitThrottle):
    """
    Rate limit for report generation.
    Default: 10 reports per hour (user-based).
    Prevents excessive CPU usage from report generation.
    """
    scope = 'report_generation'

    def get_limit_and_window(self, request) -> Tuple[int, int]:
        """Report generation: 10/hour."""
        return (10, 3600)


# Rate limit decorator for function-based views

def rate_limit(limit: int, window: int = 60, scope: Optional[str] = None):
    """
    Decorator for rate limiting function-based views.

    Args:
        limit: Maximum requests allowed
        window: Time window in seconds (default: 60)
        scope: Cache key scope (default: function name)

    Example:
        @rate_limit(limit=10, window=60)
        def my_view(request):
            return Response({'status': 'ok'})
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Determine scope
            func_scope = scope or view_func.__name__

            # Get identifier
            if request.user and request.user.is_authenticated:
                identifier = f'user_{request.user.id}'
            else:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR')
                identifier = f'ip_{ip}'

            # Check rate limit
            cache_key = f'rate_limit_{func_scope}_{identifier}'
            limiter = SlidingWindowRateLimiter(cache_key, limit, window)
            is_allowed, headers = limiter.is_allowed()

            if not is_allowed:
                retry_after = limiter.get_retry_after()
                return JsonResponse(
                    {
                        'error': 'rate_limit_exceeded',
                        'message': f'Rate limit exceeded. Maximum {limit} requests per {window} seconds.',
                        'retry_after': retry_after
                    },
                    status=HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        **headers,
                        'Retry-After': str(retry_after)
                    }
                )

            # Call the view function
            response = view_func(request, *args, **kwargs)

            # Add rate limit headers
            if isinstance(response, Response):
                for header_name, header_value in headers.items():
                    response[header_name] = header_value
            elif hasattr(response, '__setitem__'):
                for header_name, header_value in headers.items():
                    response[header_name] = header_value

            return response

        return wrapper
    return decorator


# Backwards compatibility with existing throttling.py

# These classes maintain compatibility with existing code that imports from config.throttling
BurstThrottle = RateLimitThrottle  # Default burst protection
StudentUserThrottle = AuthenticatedUserThrottle  # Student is authenticated user
GeneralUserThrottle = AuthenticatedUserThrottle  # General user is authenticated
AdminUserThrottle = AdminThrottle  # Admin throttle for backward compat
