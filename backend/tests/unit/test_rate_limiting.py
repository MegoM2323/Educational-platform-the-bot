"""
Comprehensive unit tests for rate limiting functionality.

Tests cover:
- Sliding window algorithm accuracy
- Tiered rate limits (anonymous, authenticated, premium, admin)
- Endpoint-specific limits
- Rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
- 429 Too Many Requests responses
- Retry-After header
- Admin bypass mechanism
- Decorator-based rate limiting
- Cache expiration and cleanup
- Edge cases and race conditions
"""

import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import pytest
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS

from core.rate_limiting import (
    SlidingWindowRateLimiter,
    RateLimitThrottle,
    AnonUserThrottle,
    AuthenticatedUserThrottle,
    PremiumUserThrottle,
    AdminThrottle,
    LoginThrottle,
    UploadThrottle,
    SearchThrottle,
    AnalyticsThrottle,
    ChatMessageThrottle,
    ChatRoomThrottle,
    AssignmentSubmissionThrottle,
    ReportGenerationThrottle,
    rate_limit,
)

User = get_user_model()


@pytest.mark.django_db
class TestSlidingWindowRateLimiter(TestCase):
    """Test sliding window rate limiter algorithm."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_limiter_initialization(self):
        """Test limiter initializes with correct parameters."""
        limiter = SlidingWindowRateLimiter("test_key", 10, 60)
        self.assertEqual(limiter.key, "test_key")
        self.assertEqual(limiter.limit, 10)
        self.assertEqual(limiter.window, 60)

    def test_first_request_allowed(self):
        """Test first request is always allowed."""
        limiter = SlidingWindowRateLimiter("test_key", 10, 60)
        is_allowed, headers = limiter.is_allowed()

        self.assertTrue(is_allowed)
        self.assertEqual(headers["X-RateLimit-Limit"], "10")
        self.assertEqual(headers["X-RateLimit-Remaining"], "9")

    def test_requests_within_limit(self):
        """Test requests within limit are allowed."""
        limiter = SlidingWindowRateLimiter("test_key", 5, 60)

        for i in range(5):
            is_allowed, headers = limiter.is_allowed()
            self.assertTrue(is_allowed)
            expected_remaining = 4 - i
            self.assertEqual(headers["X-RateLimit-Remaining"], str(expected_remaining))

    def test_request_exceeding_limit(self):
        """Test request exceeding limit is rejected."""
        limiter = SlidingWindowRateLimiter("test_key", 3, 60)

        # Make 3 allowed requests
        for _ in range(3):
            is_allowed, _ = limiter.is_allowed()
            self.assertTrue(is_allowed)

        # 4th request should be rejected
        is_allowed, headers = limiter.is_allowed()
        self.assertFalse(is_allowed)
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")

    def test_rate_limit_headers(self):
        """Test rate limit headers are properly formatted."""
        limiter = SlidingWindowRateLimiter("test_key", 10, 60)
        is_allowed, headers = limiter.is_allowed()

        self.assertIn("X-RateLimit-Limit", headers)
        self.assertIn("X-RateLimit-Remaining", headers)
        self.assertIn("X-RateLimit-Reset", headers)

        # Reset timestamp should be in future
        reset_ts = int(headers["X-RateLimit-Reset"])
        now_ts = int(datetime.now().timestamp())
        self.assertGreater(reset_ts, now_ts)

    def test_sliding_window_cleanup(self):
        """Test old timestamps are removed from window."""
        limiter = SlidingWindowRateLimiter("test_key", 5, 2)  # 2-second window

        # Make 5 requests (should be at limit)
        for _ in range(5):
            limiter.is_allowed()

        # Wait for window to expire
        time.sleep(2.5)

        # Create new limiter instance with same key
        new_limiter = SlidingWindowRateLimiter("test_key", 5, 2)
        is_allowed, headers = new_limiter.is_allowed()

        # Should be allowed because old requests are out of window
        self.assertTrue(is_allowed)

    def test_retry_after_calculation(self):
        """Test retry-after value is calculated correctly."""
        limiter = SlidingWindowRateLimiter("test_key", 2, 60)

        # Make 2 requests to hit limit
        for _ in range(2):
            limiter.is_allowed()

        # Get retry-after time
        retry_after = limiter.get_retry_after()

        # Should be between 0 and window duration
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 61)


@pytest.mark.django_db
class TestRateLimitThrottle(APITestCase):
    """Test RateLimitThrottle class."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="user@test.com", password="TestPass123!")
        self.admin = User.objects.create_user(
            email="admin@test.com", password="TestPass123!", is_staff=True, is_superuser=True
        )

    def tearDown(self):
        """Clean up."""
        cache.clear()

    def test_throttle_identifies_anonymous_user(self):
        """Test throttle correctly identifies anonymous users."""
        request = self.factory.get("/")
        throttle = RateLimitThrottle()
        identifier = throttle.get_identifier(request)

        self.assertTrue(identifier.startswith("ip_"))

    def test_throttle_identifies_authenticated_user(self):
        """Test throttle correctly identifies authenticated users."""
        request = self.factory.get("/")
        request.user = self.user
        throttle = RateLimitThrottle()
        identifier = throttle.get_identifier(request)

        self.assertEqual(identifier, f"user_{self.user.id}")

    def test_anonymous_user_limit(self):
        """Test anonymous users get default tier limit."""
        request = self.factory.get("/")
        throttle = RateLimitThrottle()
        limit, window = throttle.get_limit_and_window(request)

        # Default anonymous: 20/min
        self.assertEqual(limit, 20)
        self.assertEqual(window, 60)

    def test_authenticated_user_limit(self):
        """Test authenticated users get higher limit."""
        request = self.factory.get("/")
        request.user = self.user
        throttle = RateLimitThrottle()
        limit, window = throttle.get_limit_and_window(request)

        # Default authenticated: 100/min
        self.assertEqual(limit, 100)
        self.assertEqual(window, 60)

    def test_admin_user_bypass(self):
        """Test admin users bypass rate limiting."""
        request = self.factory.get("/")
        request.user = self.admin
        throttle = RateLimitThrottle()

        # Admin should never be throttled
        for _ in range(100):
            result = throttle.throttle(request, None)
            self.assertTrue(result)

    def test_throttle_allows_within_limit(self):
        """Test throttle allows requests within limit."""
        request = self.factory.get("/")
        throttle = AnonUserThrottle()

        # Make 20 requests (at limit)
        for i in range(20):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Request {i+1} should be allowed")

    def test_throttle_rejects_exceeding_limit(self):
        """Test throttle rejects requests exceeding limit."""
        request = self.factory.get("/")
        throttle = AnonUserThrottle()

        # Make 20 requests (at limit)
        for _ in range(20):
            throttle.throttle(request, None)

        # 21st request should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_throttle_headers_included(self):
        """Test rate limit headers are included in response."""
        request = self.factory.get("/")
        throttle = AnonUserThrottle()
        throttle.throttle(request, None)

        headers = throttle.get_headers()
        self.assertIn("X-RateLimit-Limit", headers)
        self.assertIn("X-RateLimit-Remaining", headers)
        self.assertIn("X-RateLimit-Reset", headers)

    def test_different_users_separate_limits(self):
        """Test different users have separate rate limit buckets."""
        throttle1 = AnonUserThrottle()
        throttle2 = AnonUserThrottle()

        request1 = self.factory.get("/", REMOTE_ADDR="192.168.1.1")
        request2 = self.factory.get("/", REMOTE_ADDR="192.168.1.2")

        # Each IP should have separate limit of 20
        for _ in range(20):
            result1 = throttle1.throttle(request1, None)
            self.assertTrue(result1)

        for _ in range(20):
            result2 = throttle2.throttle(request2, None)
            self.assertTrue(result2)

        # Both should now be at limit
        result1 = throttle1.throttle(request1, None)
        result2 = throttle2.throttle(request2, None)
        self.assertFalse(result1)
        self.assertFalse(result2)


@pytest.mark.django_db
class TestEndpointSpecificThrottles(APITestCase):
    """Test endpoint-specific throttle classes."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="user@test.com", password="TestPass123!")

    def tearDown(self):
        """Clean up."""
        cache.clear()

    def test_login_throttle_5_per_minute(self):
        """Test login throttle allows 5 per minute."""
        request = self.factory.post("/api/auth/login/")
        throttle = LoginThrottle()

        # Allow 5 requests
        for i in range(5):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Login request {i+1} should be allowed")

        # 6th should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_upload_throttle_10_per_hour(self):
        """Test upload throttle allows 10 per hour."""
        request = self.factory.post("/api/materials/upload/")
        request.user = self.user
        throttle = UploadThrottle()

        # Allow 10 requests
        for i in range(10):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Upload {i+1} should be allowed")

        # 11th should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_search_throttle_200_per_minute(self):
        """Test search throttle allows 200 per minute."""
        request = self.factory.get("/api/materials/search/")
        request.user = self.user
        throttle = SearchThrottle()

        # Allow 200 requests
        for i in range(200):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Search {i+1} should be allowed")

        # 201st should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_analytics_throttle_5000_per_hour(self):
        """Test analytics throttle allows 5000 per hour."""
        request = self.factory.get("/api/reports/analytics/")
        request.user = self.user
        throttle = AnalyticsThrottle()

        # Allow 5000 requests would be impractical for test, verify limit/window instead
        limit, window = throttle.get_limit_and_window(request)
        self.assertEqual(limit, 5000)
        self.assertEqual(window, 3600)

    def test_chat_message_throttle_300_per_minute(self):
        """Test chat message throttle allows 300 per minute."""
        request = self.factory.post("/api/chat/messages/")
        request.user = self.user
        throttle = ChatMessageThrottle()

        # Allow 300 requests would be impractical for test, verify limit/window instead
        limit, window = throttle.get_limit_and_window(request)
        self.assertEqual(limit, 300)
        self.assertEqual(window, 60)

    def test_chat_room_throttle_5_per_hour(self):
        """Test chat room creation throttle allows 5 per hour."""
        request = self.factory.post("/api/chat/rooms/")
        request.user = self.user
        throttle = ChatRoomThrottle()

        # Allow 5 requests
        for i in range(5):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Room creation {i+1} should be allowed")

        # 6th should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_assignment_submission_throttle_10_per_hour(self):
        """Test assignment submission throttle allows 10 per hour."""
        request = self.factory.post("/api/assignments/submit/")
        request.user = self.user
        throttle = AssignmentSubmissionThrottle()

        # Allow 10 requests
        for i in range(10):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Submission {i+1} should be allowed")

        # 11th should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_report_generation_throttle_10_per_hour(self):
        """Test report generation throttle allows 10 per hour."""
        request = self.factory.post("/api/reports/generate/")
        request.user = self.user
        throttle = ReportGenerationThrottle()

        # Allow 10 requests
        for i in range(10):
            result = throttle.throttle(request, None)
            self.assertTrue(result, f"Report {i+1} should be allowed")

        # 11th should be rejected
        result = throttle.throttle(request, None)
        self.assertFalse(result)

    def test_admin_panel_throttle_5000_per_hour(self):
        """Test admin panel throttle allows 5000 per hour."""
        from core.rate_limiting import AdminPanelThrottle

        request = self.factory.get("/api/admin/")
        request.user = self.user
        throttle = AdminPanelThrottle()

        # Verify limit/window
        limit, window = throttle.get_limit_and_window(request)
        self.assertEqual(limit, 5000)
        self.assertEqual(window, 3600)

    def test_admin_panel_burst_throttle_200_per_minute(self):
        """Test admin panel burst throttle allows 200 per minute."""
        from core.rate_limiting import AdminPanelBurstThrottle

        request = self.factory.get("/api/admin/")
        request.user = self.user
        throttle = AdminPanelBurstThrottle()

        # Verify limit/window
        limit, window = throttle.get_limit_and_window(request)
        self.assertEqual(limit, 200)
        self.assertEqual(window, 60)


@pytest.mark.django_db
class TestRateLimitDecorator(TestCase):
    """Test @rate_limit decorator."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email="user@test.com", password="TestPass123!")

    def tearDown(self):
        """Clean up."""
        cache.clear()

    def test_decorator_allows_within_limit(self):
        """Test decorator allows requests within limit."""

        @rate_limit(limit=3, window=60)
        def test_view(request):
            return Response({"status": "ok"})

        request = self.factory.get("/")
        for i in range(3):
            response = test_view(request)
            self.assertEqual(response.status_code, 200)

    def test_decorator_rejects_exceeding_limit(self):
        """Test decorator rejects requests exceeding limit."""

        @rate_limit(limit=2, window=60)
        def test_view(request):
            return Response({"status": "ok"})

        request = self.factory.get("/")
        # Allow 2 requests
        for _ in range(2):
            response = test_view(request)
            self.assertEqual(response.status_code, 200)

        # 3rd should return 429
        response = test_view(request)
        self.assertEqual(response.status_code, 429)

    def test_decorator_includes_headers(self):
        """Test decorator includes rate limit headers."""

        @rate_limit(limit=5, window=60)
        def test_view(request):
            return Response({"status": "ok"})

        request = self.factory.get("/")
        response = test_view(request)

        self.assertIn("X-RateLimit-Limit", response)
        self.assertIn("X-RateLimit-Remaining", response)
        self.assertIn("X-RateLimit-Reset", response)

    def test_decorator_different_scopes(self):
        """Test decorator with different scopes."""

        @rate_limit(limit=2, scope="view1")
        def view1(request):
            return Response({"status": "ok"})

        @rate_limit(limit=2, scope="view2")
        def view2(request):
            return Response({"status": "ok"})

        request = self.factory.get("/")

        # Each view should have separate limit
        for _ in range(2):
            self.assertEqual(view1(request).status_code, 200)
            self.assertEqual(view2(request).status_code, 200)

        # Both should be at limit
        self.assertEqual(view1(request).status_code, 429)
        self.assertEqual(view2(request).status_code, 429)


@pytest.mark.django_db
class TestRateLimitEdgeCases(APITestCase):
    """Test edge cases and race conditions."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.factory = APIRequestFactory()

    def tearDown(self):
        """Clean up."""
        cache.clear()

    def test_zero_remaining_header(self):
        """Test X-RateLimit-Remaining is 0 when at limit."""
        request = self.factory.get("/")
        throttle = AnonUserThrottle()

        # Make 20 requests (at limit)
        for _ in range(20):
            throttle.throttle(request, None)

        headers = throttle.get_headers()
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")

    def test_reset_timestamp_is_future(self):
        """Test X-RateLimit-Reset is always in the future."""
        request = self.factory.get("/")
        throttle = AnonUserThrottle()
        throttle.throttle(request, None)

        headers = throttle.get_headers()
        reset_ts = int(headers["X-RateLimit-Reset"])
        now_ts = int(datetime.now().timestamp())

        self.assertGreaterEqual(reset_ts, now_ts)

    def test_x_forwarded_for_handling(self):
        """Test X-Forwarded-For header is properly handled for proxied requests."""
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="192.168.1.100, 192.168.1.1")
        throttle = AnonUserThrottle()

        identifier = throttle.get_identifier(request)
        # Should use first IP from X-Forwarded-For
        self.assertEqual(identifier, "ip_192.168.1.100")

    def test_cache_expiration(self):
        """Test cache is properly expired after window."""
        limiter = SlidingWindowRateLimiter("test_key", 1, 1)

        # First request
        limiter.is_allowed()

        # Should be at limit
        limiter2 = SlidingWindowRateLimiter("test_key", 1, 1)
        is_allowed, _ = limiter2.is_allowed()
        self.assertFalse(is_allowed)

        # Wait for window to expire
        time.sleep(1.5)

        # Should now be allowed
        limiter3 = SlidingWindowRateLimiter("test_key", 1, 1)
        is_allowed, _ = limiter3.is_allowed()
        self.assertTrue(is_allowed)

    def test_concurrent_requests_same_user(self):
        """Test multiple requests from same user are tracked correctly."""
        request = self.factory.get("/")
        request.user = User.objects.create_user(email="user@test.com", password="TestPass123!")

        throttle1 = AnonUserThrottle()
        throttle2 = AnonUserThrottle()

        # Both should use same cache key since same user
        # Make requests concurrently (simulated)
        throttle1.throttle(request, None)
        throttle2.throttle(request, None)

        # History should be updated in cache
        limiter = SlidingWindowRateLimiter(f"rate_limit_anon_user_{request.user.id}", 20, 60)
        cache_data = cache.get(limiter.key)
        # Should have 2 entries from both throttle instances
        self.assertIsNotNone(cache_data)

    def test_premium_user_higher_limit(self):
        """Test premium users get higher limit (if premium feature exists)."""
        user = User.objects.create_user(email="premium@test.com", password="TestPass123!")
        # Mock premium user attribute
        user.is_premium = True

        request = self.factory.get("/")
        request.user = user

        throttle = PremiumUserThrottle()
        limit, window = throttle.get_limit_and_window(request)

        # Premium should get 500/min
        self.assertEqual(limit, 500)
        self.assertEqual(window, 60)


@pytest.mark.django_db
@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class TestRateLimitIntegration(APITestCase):
    """Integration tests for rate limiting."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(email="user@test.com", password="TestPass123!")

    def tearDown(self):
        """Clean up."""
        cache.clear()

    def test_multiple_throttles_different_limits(self):
        """Test multiple throttles with different limits work independently."""
        request = self.factory.post("/api/auth/login/")

        login_throttle = LoginThrottle()  # 5/min
        anon_throttle = AnonUserThrottle()  # 20/min

        # Both should track separately
        login_throttle.throttle(request, None)
        anon_throttle.throttle(request, None)

        # Cache should have separate entries
        login_key = f'rate_limit_login_ip_{request.META.get("REMOTE_ADDR")}'
        anon_key = f'rate_limit_anon_ip_{request.META.get("REMOTE_ADDR")}'

        self.assertIsNotNone(cache.get(login_key))
        self.assertIsNotNone(cache.get(anon_key))

    def test_user_switching_different_limits(self):
        """Test switching from anonymous to authenticated changes limits."""
        factory = APIRequestFactory()

        # Anonymous request
        anon_request = factory.get("/")
        anon_throttle = RateLimitThrottle()
        anon_limit, anon_window = anon_throttle.get_limit_and_window(anon_request)

        # Authenticated request (same IP)
        auth_request = factory.get("/")
        auth_request.user = self.user
        auth_throttle = RateLimitThrottle()
        auth_limit, auth_window = auth_throttle.get_limit_and_window(auth_request)

        # Should have different limits
        self.assertNotEqual(anon_limit, auth_limit)
        self.assertEqual(anon_limit, 20)
        self.assertEqual(auth_limit, 100)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
