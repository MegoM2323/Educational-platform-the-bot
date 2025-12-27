"""
Comprehensive DRF throttle classes for per-endpoint rate limiting.

Implements multiple throttle classes with different limits for different user types
and endpoints. Uses Django cache (Redis-backed in production) for tracking requests.

Rate limit tracking:
- Cache key: "throttle_{scope}_{identifier}"
- Value: [timestamp1, timestamp2, ...] of requests
- Old timestamps are cleaned on each throttle check

Response headers:
- X-RateLimit-Limit: maximum requests allowed
- X-RateLimit-Remaining: requests remaining in current window
- X-RateLimit-Reset: Unix timestamp when limit resets
- Retry-After: seconds to wait before retrying (on 429 response)
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from rest_framework.throttling import BaseThrottle
from rest_framework.response import Response
from django.core.cache import cache


class BaseRateLimitThrottle(BaseThrottle):
    """
    Base class for all rate limit throttles.
    Provides common functionality for tracking and reporting rate limits.
    """

    scope = None  # Must be overridden in subclasses

    def get_rate(self) -> Optional[str]:
        """
        Determine the string representation of the throttle rate.
        Format: "10/h" (10 requests per hour), "5/m" (5 per minute), etc.

        Returns:
            str: Rate limit string (e.g., "100/h")
        """
        if not self.scope:
            return None

        # Get rate from Django settings REST_FRAMEWORK.DEFAULT_THROTTLE_RATES
        from django.conf import settings
        try:
            return settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}).get(self.scope)
        except AttributeError:
            return None

    def parse_rate(self, rate: str) -> Tuple[int, int]:
        """
        Parse rate string and return (request_count, duration_in_seconds).

        Args:
            rate (str): Rate limit string (e.g., "5/m", "100/h", "1000/d")

        Returns:
            tuple: (num_requests, duration_seconds)

        Raises:
            ValueError: If rate format is invalid
        """
        if not rate:
            return (None, None)

        num, period = rate.split('/')
        num_requests = int(num)

        duration_map = {
            's': 1,          # second
            'm': 60,         # minute
            'h': 3600,       # hour
            'd': 86400,      # day
        }

        duration = duration_map.get(period.lower(), 3600)
        return (num_requests, duration)

    def get_cache_key(self) -> Optional[str]:
        """
        Generate unique cache key for this request.
        Uses scope and identifier (user ID or IP).

        Returns:
            str: Cache key for throttle tracking
        """
        if self.request.user and self.request.user.is_authenticated:
            identifier = self.request.user.id
        else:
            identifier = self.get_ident(self.request)

        return f'throttle_{self.scope}_{identifier}'

    def throttle_success(self) -> Tuple[bool, dict]:
        """
        Check if request should be allowed.

        Returns:
            tuple: (allow, headers_dict)
        """
        if self.rate is None:
            return (True, {})

        self.key = self.get_cache_key()
        self.history = cache.get(self.key, [])
        self.now = datetime.now()

        num_requests, duration = self.parse_rate(self.rate)

        # Drop requests from history older than duration window
        cutoff = self.now - timedelta(seconds=duration)
        self.history = [timestamp for timestamp in self.history
                        if timestamp > cutoff]

        if len(self.history) >= num_requests:
            # Rate limit exceeded
            return (False, self._get_headers(num_requests, duration))

        # Record this request
        self.history.append(self.now)
        # Set cache with duration timeout
        cache.set(self.key, self.history, duration)

        return (True, self._get_headers(num_requests, duration))

    def _get_headers(self, num_requests: int, duration: int) -> dict:
        """
        Generate response headers for rate limit information.

        Args:
            num_requests (int): Maximum requests allowed in window
            duration (int): Window duration in seconds

        Returns:
            dict: Headers with rate limit information
        """
        if self.rate is None:
            return {}

        remaining = max(0, num_requests - len(self.history))

        # Calculate reset time (end of current window)
        if self.history:
            reset_time = self.history[0] + timedelta(seconds=duration)
        else:
            reset_time = self.now + timedelta(seconds=duration)

        reset_timestamp = int(reset_time.timestamp())

        return {
            'X-RateLimit-Limit': str(num_requests),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_timestamp),
        }

    def throttle(self, request, view) -> bool:
        """
        Return True if the request should be allowed, False if throttled.
        """
        # Set request and rate first before calling throttle_success
        self.request = request
        self.rate = self.get_rate()

        # Call the actual throttle check
        allow, headers = self.throttle_success()
        self.headers = headers

        return allow

    def get_ident(self, request) -> str:
        """
        Identify the machine making the request.
        Default: Use IP address from request.
        """
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        num_proxies = getattr(self, 'num_proxies', None)

        if num_proxies is not None and num_proxies != 0 and xff:
            # `x_forwarded_for` header is a comma separated list of IP addresses.
            # The first `num_proxies` items should be trusted.
            client_addr = xff.split(',')[0].strip()
        else:
            client_addr = remote_addr or ''

        return client_addr


class AnonUserThrottle(BaseRateLimitThrottle):
    """
    Throttle for anonymous users: 50 requests per hour (IP-based).
    """
    scope = 'anon'


class GeneralUserThrottle(BaseRateLimitThrottle):
    """
    Throttle for authenticated users: 500 requests per hour (user-based).
    """
    scope = 'user'


class StudentUserThrottle(BaseRateLimitThrottle):
    """
    Throttle for student users: 1000 requests per hour.
    """
    scope = 'student'


class AdminUserThrottle(BaseRateLimitThrottle):
    """
    Throttle for admin users: unlimited (no throttling).
    Admin users can bypass rate limiting for emergency access.
    """
    scope = 'admin'

    def throttle(self, request, view) -> bool:
        """
        Admins are never throttled.
        """
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        return super().throttle(request, view)


class BurstThrottle(BaseRateLimitThrottle):
    """
    Prevent request spam: 10 requests per second (per IP/user).
    Applied globally to prevent DoS attacks.
    """
    scope = 'burst'


# Endpoint-specific throttles

class LoginThrottle(BaseRateLimitThrottle):
    """
    Auth endpoint throttle: 5 requests per minute per IP.
    Protects against brute force password attacks.
    """
    scope = 'login'


class UploadThrottle(BaseRateLimitThrottle):
    """
    File upload throttle: 10 requests per hour per user.
    Prevents server storage abuse.
    """
    scope = 'upload'


class SearchThrottle(BaseRateLimitThrottle):
    """
    Search endpoint throttle: 30 requests per minute per user.
    Prevents database abuse from excessive searches.
    """
    scope = 'search'


class AnalyticsThrottle(BaseRateLimitThrottle):
    """
    Analytics endpoint throttle: 100 requests per hour per user.
    Prevents excessive report generation.
    """
    scope = 'analytics'


class ChatMessageThrottle(BaseRateLimitThrottle):
    """
    Chat message throttle: 60 messages per minute per user.
    Prevents chat spam and abuse.
    """
    scope = 'chat_message'


class ChatRoomThrottle(BaseRateLimitThrottle):
    """
    Chat room creation throttle: 5 rooms per hour per user.
    Prevents creation spam.
    """
    scope = 'chat_room'


class AssignmentSubmissionThrottle(BaseRateLimitThrottle):
    """
    Assignment submission throttle: 10 submissions per hour per user.
    Prevents submission spam.
    """
    scope = 'assignment_submission'


class ReportGenerationThrottle(BaseRateLimitThrottle):
    """
    Report generation throttle: 10 reports per hour per user.
    Prevents excessive CPU usage from report generation.
    """
    scope = 'report_generation'


class AdminEndpointThrottle(BaseRateLimitThrottle):
    """
    Admin endpoint throttle: 1000 requests per hour per admin.
    Allows admin operations to proceed quickly.
    """
    scope = 'admin_endpoint'

    def throttle(self, request, view) -> bool:
        """
        Admins can use higher limits.
        """
        if request.user and request.user.is_authenticated and request.user.is_staff:
            self.rate = self.get_rate()
            return True
        return super().throttle(request, view)
