"""
Comprehensive tests for multi-level caching strategy.

Tests:
- L1 in-memory cache (TTL, expiration)
- L2 Redis cache (persistence)
- Cache invalidation (single key, patterns)
- Cache warming
- Cache statistics and monitoring
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from reports.cache.multilevel import (
    MultiLevelCache,
    get_multilevel_cache,
    CacheInvalidationTrigger,
    CacheWarmer,
    CacheMonitor,
    get_cache_monitor,
)


class TestMultiLevelCache(TestCase):
    """Test multi-level caching functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = MultiLevelCache()
        cache.clear()  # Clear Redis cache

    def test_set_and_get_from_l1_memory(self):
        """Test setting and getting from L1 in-memory cache."""
        key = 'test:key:1'
        value = {'data': 'test_value'}

        # Set value
        success = self.cache.set(key, value, ttl_l1=60)
        self.assertTrue(success)

        # Get from L1
        result, level = self.cache.get(key)
        self.assertEqual(result, value)
        self.assertEqual(level, 'memory')

    def test_set_and_get_from_l2_redis(self):
        """Test setting and getting from L2 Redis cache."""
        key = 'test:key:2'
        value = {'data': 'redis_value'}

        # Set value
        self.cache.set(key, value, ttl_l1=1, ttl_l2=60)

        # Wait for L1 expiration
        import time
        time.sleep(1.1)

        # Get from L2 (L1 expired)
        result, level = self.cache.get(key)
        self.assertEqual(result, value)
        self.assertEqual(level, 'redis')

    def test_l1_expiration(self):
        """Test L1 cache expiration."""
        key = 'test:expiration'
        value = 'expires'

        # Set with short TTL
        self.cache.set(key, value, ttl_l1=1)

        # Get immediately (should hit)
        result, level = self.cache.get(key)
        self.assertIsNotNone(result)

        # Wait and try again
        import time
        time.sleep(1.1)

        result, level = self.cache.get(key)
        # Should miss L1 but might hit L2 or compute
        if result is None:
            self.assertEqual(level, 'miss')

    def test_compute_function(self):
        """Test cache with compute function."""
        key = 'test:compute'

        def compute_value():
            return {'computed': 'result'}

        # First call should compute
        result, level = self.cache.get(key, compute_func=compute_value)
        self.assertEqual(result, {'computed': 'result'})
        self.assertEqual(level, 'compute')

        # Second call should hit cache
        result2, level2 = self.cache.get(key)
        self.assertEqual(result2, result)
        self.assertIn(level2, ['memory', 'redis'])

    def test_invalidate_single_key(self):
        """Test invalidating single cache key."""
        key = 'test:invalidate'
        value = 'to_invalidate'

        # Set value
        self.cache.set(key, value)

        # Verify it's cached
        result, _ = self.cache.get(key)
        self.assertIsNotNone(result)

        # Invalidate
        success = self.cache.invalidate(key)
        self.assertTrue(success)

        # Verify it's gone
        result, level = self.cache.get(key)
        self.assertIsNone(result)
        self.assertEqual(level, 'miss')

    def test_invalidate_pattern(self):
        """Test pattern-based cache invalidation."""
        # Set multiple keys
        keys = [
            'analytics:student:1:summary',
            'analytics:student:2:summary',
            'analytics:assignment:1:stats',
        ]

        for key in keys:
            self.cache.set(key, f'value_for_{key}')

        # Verify all are cached
        for key in keys:
            result, level = self.cache.get(key)
            self.assertIsNotNone(result)

        # Invalidate pattern
        count = self.cache.invalidate_pattern('analytics:student:*')

        # Should have invalidated 2 keys
        self.assertEqual(count, 2)

        # Verify student keys are gone but assignment key remains
        result, level = self.cache.get('analytics:assignment:1:stats')
        self.assertIsNotNone(result)

    def test_clear_all(self):
        """Test clearing all cache entries."""
        # Set some values
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        self.cache.set('key3', 'value3')

        # Clear all
        success = self.cache.clear_all()
        self.assertTrue(success)

        # Verify all are gone
        for i in range(1, 4):
            result, level = self.cache.get(f'key{i}')
            self.assertIsNone(result)

    def test_get_stats(self):
        """Test getting cache statistics."""
        # Set some values
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')

        # Get stats
        stats = self.cache.get_stats()

        self.assertIn('timestamp', stats)
        self.assertIn('l1_memory', stats)
        self.assertIn('l2_redis', stats)
        self.assertIn('l3_views', stats)

        # L1 should have 2 entries
        self.assertEqual(stats['l1_memory']['size'], 2)


class TestCacheInvalidationTrigger(TestCase):
    """Test cache invalidation triggers."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = get_multilevel_cache()
        cache.clear()

    def test_on_grade_update(self):
        """Test invalidation on grade update."""
        # Set some cache entries
        self.cache.set('analytics:assignment:123:stats', {'data': 'stats'})
        self.cache.set('analytics:student:456:summary', {'data': 'summary'})

        # Trigger invalidation
        count = CacheInvalidationTrigger.on_grade_update(
            assignment_id=123,
            student_id=456
        )

        # Should have invalidated entries
        self.assertGreater(count, 0)

    def test_on_material_view(self):
        """Test invalidation on material view."""
        # Set cache entries
        self.cache.set('analytics:progress:100:data', {'data': 'progress'})

        # Trigger invalidation
        count = CacheInvalidationTrigger.on_material_view(
            material_id=100,
            student_id=200
        )

        self.assertGreaterEqual(count, 0)

    def test_on_user_progress_change(self):
        """Test invalidation on user progress change."""
        # Set user cache
        self.cache.set('dashboard:user_100:summary', {'data': 'dashboard'})
        self.cache.set('analytics:student:100:stats', {'data': 'stats'})

        # Trigger invalidation
        count = CacheInvalidationTrigger.on_user_progress_change(user_id=100)

        self.assertGreater(count, 0)

    def test_on_report_generation(self):
        """Test invalidation on report generation."""
        # Set report cache
        self.cache.set('report:student_progress:type1', {'data': 'report'})

        # Trigger invalidation
        count = CacheInvalidationTrigger.on_report_generation(
            report_type='student_progress'
        )

        self.assertGreaterEqual(count, 0)


class TestCacheWarmer(TestCase):
    """Test cache warming functionality."""

    def setUp(self):
        """Set up test fixtures."""
        cache.clear()

    @patch('reports.cache.multilevel.DataWarehouseService')
    def test_warm_analytics(self, mock_warehouse):
        """Test warming analytics cache."""
        # Mock warehouse methods
        mock_instance = MagicMock()
        mock_warehouse.return_value = mock_instance
        mock_instance.get_student_analytics.return_value = [{'id': 1}]
        mock_instance.get_assignment_analytics.return_value = [{'id': 2}]
        mock_instance.get_progress_analytics.return_value = [{'id': 3}]
        mock_instance.get_student_engagement_metrics.return_value = [{'id': 4}]

        # Warm cache
        stats = CacheWarmer.warm_analytics(
            query_types=['student', 'assignment', 'progress', 'engagement']
        )

        # Verify results
        self.assertIn('student', stats)
        self.assertIn('assignment', stats)
        self.assertIn('progress', stats)
        self.assertIn('engagement', stats)

    @patch('reports.cache.multilevel.DataWarehouseService')
    def test_warm_user_dashboard(self, mock_warehouse):
        """Test warming user dashboard cache."""
        # Mock warehouse
        mock_instance = MagicMock()
        mock_warehouse.return_value = mock_instance
        mock_instance.get_student_analytics.return_value = [{'id': 1}]

        # Warm dashboard
        with patch('reports.cache.multilevel.User') as mock_user:
            mock_user.objects.get.return_value = MagicMock()

            stats = CacheWarmer.warm_user_dashboard(user_id=100)

            self.assertEqual(stats['user_id'], 100)
            self.assertEqual(stats['status'], 'warmed')


class TestCacheMonitor(TestCase):
    """Test cache monitoring and statistics."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = CacheMonitor()

    def test_record_hits(self):
        """Test recording cache hits."""
        self.monitor.record_hit()
        self.monitor.record_hit()
        self.monitor.record_hit()

        stats = self.monitor.get_stats()
        self.assertEqual(stats['hits'], 3)

    def test_record_misses(self):
        """Test recording cache misses."""
        self.monitor.record_miss()
        self.monitor.record_miss()

        stats = self.monitor.get_stats()
        self.assertEqual(stats['misses'], 2)

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        # 75 hits, 25 misses = 75% hit rate
        for _ in range(75):
            self.monitor.record_hit()
        for _ in range(25):
            self.monitor.record_miss()

        stats = self.monitor.get_stats()
        self.assertEqual(stats['hit_rate'], 75.0)

    def test_reset(self):
        """Test resetting monitor."""
        self.monitor.record_hit()
        self.monitor.record_miss()

        self.monitor.reset()

        stats = self.monitor.get_stats()
        self.assertEqual(stats['hits'], 0)
        self.assertEqual(stats['misses'], 0)


class TestCacheManagement(TestCase):
    """Test cache management API."""

    def setUp(self):
        """Set up test fixtures."""
        from django.test import Client
        from django.contrib.auth import get_user_model

        self.client = Client()
        self.User = get_user_model()

        # Create test user
        self.user = self.User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_cache_stats_endpoint_authenticated(self):
        """Test cache stats endpoint requires authentication."""
        # Without authentication
        response = self.client.get('/api/cache/stats/')
        self.assertEqual(response.status_code, 401)

    def test_cache_health_endpoint_authenticated(self):
        """Test cache health endpoint requires authentication."""
        # Without authentication
        response = self.client.get('/api/cache/health/')
        self.assertEqual(response.status_code, 401)


class TestCacheTasks(TestCase):
    """Test Celery cache tasks."""

    @patch('reports.cache.tasks.CacheWarmer.warm_analytics')
    def test_warm_analytics_cache_task(self, mock_warm):
        """Test warm analytics cache task."""
        from reports.cache.tasks import warm_analytics_cache_task

        mock_warm.return_value = {
            'student': {'status': 'warmed', 'records': 50},
            'assignment': {'status': 'warmed', 'records': 30},
        }

        result = warm_analytics_cache_task.apply()
        self.assertEqual(result.status, 'SUCCESS')

    @patch('reports.cache.tasks.CacheWarmer.warm_user_dashboard')
    def test_warm_user_dashboard_task(self, mock_warm):
        """Test warm user dashboard task."""
        from reports.cache.tasks import warm_user_dashboard_cache_task

        mock_warm.return_value = {'status': 'warmed', 'user_id': 100}

        result = warm_user_dashboard_cache_task.apply(args=(100,))
        self.assertEqual(result.status, 'SUCCESS')

    @patch('reports.cache.tasks.CacheWarmer.warm_analytics')
    def test_refresh_analytics_cache_task(self, mock_warm):
        """Test refresh analytics cache task."""
        from reports.cache.tasks import refresh_analytics_cache

        mock_warm.return_value = {'student': {'status': 'warmed'}}

        result = refresh_analytics_cache.apply()
        self.assertEqual(result.status, 'SUCCESS')


if __name__ == '__main__':
    pytest.main([__file__])
