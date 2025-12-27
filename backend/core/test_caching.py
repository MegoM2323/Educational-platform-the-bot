"""
Tests for caching system (T_SYS_007).

Tests:
- Cache key generation and consistency
- Cache decorator functionality
- Per-user cache isolation
- Cache invalidation
- Cache statistics and monitoring
- Cache headers (ETags, Cache-Control)
- Cache backend health
"""

import pytest
from django.test import TestCase, Client, RequestFactory
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from config.cache import (
    CacheKeyBuilder,
    CacheInvalidator,
    CACHE_KEY_PREFIX,
    cache_response,
    get_cache_headers,
    CacheStatsCollector,
)
from core.cache_utils import (
    cache_page_conditional,
    cache_query_result,
    invalidate_cache,
    get_or_compute,
)


class CacheKeyBuilderTests(TestCase):
    """Test cache key generation."""

    def test_simple_key_generation(self):
        """Test basic cache key generation."""
        key = CacheKeyBuilder.make_key('test', 'value')
        assert key.startswith(CACHE_KEY_PREFIX)
        assert 'test' in key
        assert 'value' in key

    def test_key_with_multiple_args(self):
        """Test cache key with multiple arguments."""
        key = CacheKeyBuilder.make_key('materials', 'list', 123)
        assert 'materials' in key
        assert '123' in key

    def test_key_with_kwargs(self):
        """Test cache key with keyword arguments."""
        key = CacheKeyBuilder.make_key('search', page=1, limit=10)
        assert 'page' in key
        assert '1' in key

    def test_user_key_generation(self):
        """Test per-user cache key generation."""
        key = CacheKeyBuilder.user_key('dashboard', user_id=42)
        assert 'user_42' in key
        assert 'dashboard' in key

    def test_key_consistency(self):
        """Test that same inputs produce same keys."""
        key1 = CacheKeyBuilder.make_key('test', 'value', id=1)
        key2 = CacheKeyBuilder.make_key('test', 'value', id=1)
        assert key1 == key2

    def test_key_with_none_values(self):
        """Test cache key generation with None values."""
        key = CacheKeyBuilder.make_key('test', None, value=None)
        assert 'none' in key

    def test_long_key_hashing(self):
        """Test that very long keys are hashed."""
        long_value = 'x' * 500
        key = CacheKeyBuilder.make_key('test', long_value)
        assert len(key) < 300  # Should be hashed to short key


class CacheDecoratorTests(APITestCase):
    """Test cache decorators."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.factory = RequestFactory()
        cache.clear()

    def test_cache_response_decorator_basic(self):
        """Test basic cache_response decorator."""
        call_count = [0]

        @cache_response(ttl=300)
        def test_view(request):
            from rest_framework.response import Response
            call_count[0] += 1
            return Response({'count': call_count[0]})

        request = self.factory.get('/test/')
        request.user = self.user

        # First call should execute function
        response1 = test_view(request)
        assert response1.data['count'] == 1

        # Second call should return cached response
        response2 = test_view(request)
        assert response2.data['count'] == 1  # Should still be 1

    def test_cache_response_skips_non_get(self):
        """Test that cache_response skips non-GET requests."""
        @cache_response(ttl=300)
        def test_view(request):
            from rest_framework.response import Response
            return Response({'ok': True})

        request = self.factory.post('/test/')
        request.user = self.user

        # POST request should not use cache
        response = test_view(request)
        assert response.status_code == 200

    def test_cache_response_skips_unauthenticated(self):
        """Test that cache_response skips unauthenticated requests."""
        @cache_response(ttl=300)
        def test_view(request):
            from rest_framework.response import Response
            return Response({'ok': True})

        request = self.factory.get('/test/')
        request.user = None

        # Unauthenticated request should not use cache
        response = test_view(request)
        assert response.status_code == 200

    def test_cache_response_custom_key_func(self):
        """Test cache_response with custom key function."""
        @cache_response(
            ttl=300,
            key_func=lambda r: f"custom_{r.user.id}"
        )
        def test_view(request):
            from rest_framework.response import Response
            return Response({'user_id': request.user.id})

        request = self.factory.get('/test/')
        request.user = self.user

        response = test_view(request)
        assert response.data['user_id'] == self.user.id


class CacheInvalidationTests(TestCase):
    """Test cache invalidation."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()

    def test_invalidate_material_cache(self):
        """Test material cache invalidation."""
        # Set some cache values
        key1 = CacheKeyBuilder.make_key('materials', 'list')
        key2 = CacheKeyBuilder.make_key('materials', 'detail', 1)
        cache.set(key1, 'cached_list', 300)
        cache.set(key2, 'cached_detail', 300)

        # Verify cached
        assert cache.get(key1) == 'cached_list'
        assert cache.get(key2) == 'cached_detail'

        # Invalidate
        CacheInvalidator.invalidate_material(1)

        # Verify cleared
        assert cache.get(key1) is None
        assert cache.get(key2) is None

    def test_invalidate_user_data(self):
        """Test user data cache invalidation."""
        user_id = 42

        # Set user cache values
        key = CacheKeyBuilder.user_key('profile', user_id)
        cache.set(key, {'profile': 'data'}, 300)
        assert cache.get(key) is not None

        # Invalidate
        CacheInvalidator.invalidate_user_data(user_id)

        # Verify cleared
        assert cache.get(key) is None

    def test_clear_dashboard_cache(self):
        """Test dashboard cache clearing."""
        user_id = 42
        key = CacheKeyBuilder.user_key('dashboard', user_id)
        cache.set(key, {'dashboard': 'data'}, 300)

        CacheInvalidator.clear_dashboard_cache(user_id)

        assert cache.get(key) is None


class CacheHeadersTests(TestCase):
    """Test cache header generation."""

    def test_get_cache_headers_public(self):
        """Test public cache headers."""
        headers = get_cache_headers(ttl=3600, is_private=False)
        assert 'Cache-Control' in headers
        assert 'public' in headers['Cache-Control']
        assert 'max-age=3600' in headers['Cache-Control']

    def test_get_cache_headers_private(self):
        """Test private cache headers."""
        headers = get_cache_headers(ttl=300, is_private=True)
        assert 'Cache-Control' in headers
        assert 'private' in headers['Cache-Control']
        assert 'max-age=300' in headers['Cache-Control']

    def test_cache_headers_include_vary(self):
        """Test that Vary header is included."""
        headers = get_cache_headers()
        assert 'Vary' in headers
        assert 'Accept' in headers['Vary']
        assert 'Authorization' in headers['Vary']


class CacheUtilsTests(TestCase):
    """Test cache utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()

    def test_get_or_compute_cache_hit(self):
        """Test get_or_compute with cache hit."""
        key = 'test_key'
        cache.set(key, 'cached_value', 300)

        result = get_or_compute(key, lambda: 'computed_value')
        assert result == 'cached_value'

    def test_get_or_compute_cache_miss(self):
        """Test get_or_compute with cache miss."""
        key = 'test_key'

        result = get_or_compute(key, lambda: 'computed_value', ttl=300)
        assert result == 'computed_value'
        assert cache.get(key) == 'computed_value'

    def test_invalidate_cache(self):
        """Test cache invalidation utility."""
        key = CacheKeyBuilder.make_key('test', 'namespace')
        cache.set(key, 'value', 300)

        assert cache.get(key) == 'value'
        invalidate_cache('test', 'namespace')
        assert cache.get(key) is None


class CacheStatsTests(APITestCase):
    """Test cache statistics and monitoring."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        cache.clear()

    def test_cache_stats_endpoint(self):
        """Test cache stats API endpoint."""
        response = self.client.get('/api/core/cache-stats/')
        assert response.status_code == status.HTTP_200_OK
        assert 'cache_stats' in response.data
        assert response.data['status'] == 'success'

    def test_cache_health_check(self):
        """Test cache health check endpoint."""
        response = self.client.get('/api/core/cache-health/')
        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert response.data['status'] in ['healthy', 'unhealthy']

    def test_cache_clear_endpoint(self):
        """Test cache clear endpoint."""
        # Set a cache value
        cache.set('test_key', 'test_value', 300)
        assert cache.get('test_key') == 'test_value'

        # Clear cache
        response = self.client.post('/api/core/cache-clear/', {})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'

    def test_cache_clear_by_pattern(self):
        """Test cache clear by pattern."""
        # Set cache values
        cache.set('test:1', 'value1', 300)
        cache.set('test:2', 'value2', 300)

        # Clear by namespace
        response = self.client.post(
            '/api/core/cache-clear/',
            {'namespace': 'test'}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_cache_reset_stats(self):
        """Test cache stats reset endpoint."""
        response = self.client.post('/api/core/cache-reset-stats/', {})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'

    def test_cache_stats_returns_metrics(self):
        """Test that cache stats returns expected metrics."""
        stats = CacheStatsCollector.get_stats()
        assert 'backend' in stats
        # Should have either Redis or LocMem stats
        assert stats['backend'] in ['redis', 'locmem', 'RedisCache', 'LocMemCache']


class CachePermissionTests(APITestCase):
    """Test cache endpoint permissions."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        self.client = APIClient()

    def test_cache_stats_requires_auth(self):
        """Test that cache stats requires authentication."""
        response = self.client.get('/api/core/cache-stats/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cache_clear_requires_admin(self):
        """Test that cache clear requires admin permission."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/core/cache-clear/', {})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cache_clear_allowed_for_admin(self):
        """Test that admin can clear cache."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/core/cache-clear/', {})
        assert response.status_code == status.HTTP_200_OK

    def test_cache_health_requires_admin(self):
        """Test that cache health check requires admin."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/cache-health/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


class CacheIntegrationTests(APITestCase):
    """Integration tests for caching across endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        cache.clear()

    def test_cache_different_for_different_users(self):
        """Test that cache is isolated per user."""
        user2 = User.objects.create_user(
            username='testuser2',
            password='testpass123'
        )

        # Create cache keys for different users
        key1 = CacheKeyBuilder.user_key('dashboard', self.user.id)
        key2 = CacheKeyBuilder.user_key('dashboard', user2.id)

        # Set different values
        cache.set(key1, 'user1_data', 300)
        cache.set(key2, 'user2_data', 300)

        # Verify isolation
        assert cache.get(key1) == 'user1_data'
        assert cache.get(key2) == 'user2_data'

    def test_cache_invalidation_on_logout(self):
        """Test cache invalidation on user logout."""
        user_id = self.user.id
        key = CacheKeyBuilder.user_key('profile', user_id)
        cache.set(key, {'data': 'value'}, 300)

        assert cache.get(key) == {'data': 'value'}

        # Simulate cache invalidation on logout
        CacheInvalidator.invalidate_user_data(user_id)
        assert cache.get(key) is None


# Django test runner configuration
pytestmark = pytest.mark.django_db
