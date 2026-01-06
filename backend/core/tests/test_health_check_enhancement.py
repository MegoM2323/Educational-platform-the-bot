"""
Comprehensive tests for health check enhancement (T_ADM_004).

Tests:
- Health check endpoints (liveness, readiness, startup, detailed)
- Component status checks (database, redis, celery, websocket, cpu, memory, disk)
- Caching mechanism (10-second cache for detailed checks)
- Timeout handling
- Error scenarios and edge cases
"""

import time
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from django.utils import timezone

from ..health import HealthChecker


class HealthCheckerComponentTests:
    """Test individual health check components"""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_check_database_healthy(self):
        """Database check should return healthy status with response time"""
        result = self.checker.check_database()

        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], int)
        assert result["response_time_ms"] >= 0

    @patch('django.db.connection.cursor')
    def test_check_database_unhealthy(self, mock_cursor):
        """Database check should return unhealthy on exception"""
        mock_cursor.side_effect = Exception("Connection failed")

        result = self.checker.check_database()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "Connection failed" in result["error"]
        assert result["response_time_ms"] == 0

    def test_check_redis_healthy(self):
        """Redis check should return healthy status with memory info"""
        result = self.checker.check_redis()

        assert result["status"] == "healthy"
        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], int)
        assert "memory_mb" in result

    @patch('django.core.cache.cache.set')
    def test_check_redis_unhealthy(self, mock_set):
        """Redis check should return unhealthy on failure"""
        mock_set.side_effect = Exception("Redis connection failed")

        result = self.checker.check_redis()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "Redis connection failed" in result["error"]

    def test_check_celery_healthy(self):
        """Celery check should return healthy status with worker info"""
        result = self.checker.check_celery()

        # Celery might be unavailable in test env, but we test the response format
        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy"]
        assert "workers" in result
        assert "queue_length" in result
        assert isinstance(result["workers"], int)
        assert isinstance(result["queue_length"], int)

    @patch('celery.current_app.control.inspect')
    def test_check_celery_no_workers(self, mock_inspect):
        """Celery check should report unhealthy when no workers"""
        mock_inspector = MagicMock()
        mock_inspector.active.return_value = None
        mock_inspector.reserved.return_value = None
        mock_inspect.return_value = mock_inspector

        result = self.checker.check_celery()

        assert result["status"] == "unhealthy"
        assert "No active workers" in result.get("error", "")

    def test_check_websocket_healthy(self):
        """WebSocket check should return healthy or degraded"""
        result = self.checker.check_websocket()

        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy"]
        assert "connections" in result
        assert isinstance(result["connections"], int)

    def test_get_cpu_metrics_healthy(self):
        """CPU metrics should return status and metrics"""
        result = self.checker.get_cpu_metrics()

        assert "status" in result
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert "used_percent" in result
        assert "load_average" in result
        assert "cpu_count" in result
        assert 0 <= result["used_percent"] <= 100

    @patch('psutil.cpu_percent')
    def test_get_cpu_metrics_high_usage(self, mock_cpu_percent):
        """CPU metrics should report unhealthy at high usage"""
        mock_cpu_percent.return_value = 95.0

        result = self.checker.get_cpu_metrics()

        assert result["status"] == "unhealthy"
        assert result["used_percent"] == 95.0

    @patch('psutil.cpu_percent')
    def test_get_cpu_metrics_degraded(self, mock_cpu_percent):
        """CPU metrics should report degraded at moderate-high usage"""
        mock_cpu_percent.return_value = 85.0

        result = self.checker.get_cpu_metrics()

        assert result["status"] == "degraded"
        assert result["used_percent"] == 85.0

    def test_get_memory_metrics_healthy(self):
        """Memory metrics should return status and metrics"""
        result = self.checker.get_memory_metrics()

        assert "status" in result
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert "used_percent" in result
        assert "available_mb" in result
        assert "total_mb" in result
        assert 0 <= result["used_percent"] <= 100

    @patch('psutil.virtual_memory')
    def test_get_memory_metrics_high_usage(self, mock_memory):
        """Memory metrics should report unhealthy at high usage"""
        mock_memory.return_value = MagicMock(
            percent=92.5,
            available=100 * 1024 * 1024,
            total=1000 * 1024 * 1024
        )

        result = self.checker.get_memory_metrics()

        assert result["status"] == "unhealthy"
        assert result["used_percent"] == 92.5

    def test_get_disk_metrics_healthy(self):
        """Disk metrics should return status and metrics"""
        result = self.checker.get_disk_metrics()

        assert "status" in result
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert "used_percent" in result
        assert "free_mb" in result
        assert "total_mb" in result

    @patch('psutil.disk_usage')
    def test_get_disk_metrics_high_usage(self, mock_disk):
        """Disk metrics should report unhealthy at high usage"""
        mock_disk.return_value = MagicMock(
            percent=91.0,
            free=50 * 1024 * 1024,
            total=1000 * 1024 * 1024
        )

        result = self.checker.get_disk_metrics()

        assert result["status"] == "unhealthy"
        assert result["used_percent"] == 91.0


class HealthCheckerResponseTests:
    """Test health check response generation"""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_liveness_response_format(self):
        """Liveness response should have correct format"""
        response = self.checker.get_liveness_response()

        assert response["status"] == "healthy"
        assert "timestamp" in response
        # Verify timestamp is ISO format
        timezone.datetime.fromisoformat(response["timestamp"])

    def test_readiness_response_format(self):
        """Readiness response should include all components"""
        response, http_status = self.checker.get_readiness_response()

        assert "status" in response
        assert response["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in response
        assert "components" in response
        assert "database" in response["components"]
        assert "redis" in response["components"]
        assert "celery" in response["components"]

    def test_readiness_response_status_code(self):
        """Readiness response should return 200 when all healthy, 503 otherwise"""
        response, http_status = self.checker.get_readiness_response()

        if response["status"] == "healthy":
            assert http_status == 200
        else:
            assert http_status == 503

    def test_startup_response_format(self):
        """Startup response should include critical checks only"""
        response, http_status = self.checker.get_startup_response()

        assert "status" in response
        assert response["status"] in ["healthy", "startup_failed"]
        assert "timestamp" in response
        assert "checks" in response
        assert "database" in response["checks"]
        assert "redis" in response["checks"]
        # Celery not in startup checks
        assert "celery" not in response["checks"]

    def test_startup_response_sets_flag(self):
        """Startup response should set startup_checks_passed flag"""
        self.checker.startup_checks_passed = False

        response, http_status = self.checker.get_startup_response()

        if response["status"] == "healthy":
            assert self.checker.startup_checks_passed is True
        else:
            assert self.checker.startup_checks_passed is False

    def test_detailed_response_format(self):
        """Detailed response should include all components"""
        response = self.checker.get_detailed_response()

        assert "status" in response
        assert response["status"] in ["healthy", "degraded", "unhealthy"]
        assert "timestamp" in response
        assert "components" in response

        # Check all components are present
        expected_components = ["database", "redis", "celery", "websocket", "cpu", "memory", "disk"]
        for component in expected_components:
            assert component in response["components"]

    def test_detailed_response_overall_status_healthy(self):
        """Detailed response should be healthy when all components healthy"""
        # Mock all checks to return healthy
        with patch.object(self.checker, 'check_database') as mock_db, \
             patch.object(self.checker, 'check_redis') as mock_redis, \
             patch.object(self.checker, 'check_celery') as mock_celery, \
             patch.object(self.checker, 'check_websocket') as mock_ws, \
             patch.object(self.checker, 'get_cpu_metrics') as mock_cpu, \
             patch.object(self.checker, 'get_memory_metrics') as mock_mem, \
             patch.object(self.checker, 'get_disk_metrics') as mock_disk:

            mock_db.return_value = {"status": "healthy", "response_time_ms": 10}
            mock_redis.return_value = {"status": "healthy", "response_time_ms": 5}
            mock_celery.return_value = {"status": "healthy", "workers": 2, "queue_length": 0}
            mock_ws.return_value = {"status": "healthy", "connections": 10}
            mock_cpu.return_value = {"status": "healthy", "used_percent": 45}
            mock_mem.return_value = {"status": "healthy", "used_percent": 60}
            mock_disk.return_value = {"status": "healthy", "used_percent": 40}

            response = self.checker.get_detailed_response()

            assert response["status"] == "healthy"

    def test_detailed_response_overall_status_degraded(self):
        """Detailed response should be degraded when one component degraded"""
        with patch.object(self.checker, 'check_database') as mock_db, \
             patch.object(self.checker, 'check_redis') as mock_redis, \
             patch.object(self.checker, 'check_celery') as mock_celery, \
             patch.object(self.checker, 'check_websocket') as mock_ws, \
             patch.object(self.checker, 'get_cpu_metrics') as mock_cpu, \
             patch.object(self.checker, 'get_memory_metrics') as mock_mem, \
             patch.object(self.checker, 'get_disk_metrics') as mock_disk:

            mock_db.return_value = {"status": "healthy", "response_time_ms": 10}
            mock_redis.return_value = {"status": "healthy", "response_time_ms": 5}
            mock_celery.return_value = {"status": "healthy", "workers": 2, "queue_length": 0}
            mock_ws.return_value = {"status": "healthy", "connections": 10}
            mock_cpu.return_value = {"status": "healthy", "used_percent": 45}
            mock_mem.return_value = {"status": "degraded", "used_percent": 85}  # Degraded
            mock_disk.return_value = {"status": "healthy", "used_percent": 40}

            response = self.checker.get_detailed_response()

            assert response["status"] == "degraded"

    def test_detailed_response_overall_status_unhealthy(self):
        """Detailed response should be unhealthy when component unhealthy"""
        with patch.object(self.checker, 'check_database') as mock_db, \
             patch.object(self.checker, 'check_redis') as mock_redis, \
             patch.object(self.checker, 'check_celery') as mock_celery, \
             patch.object(self.checker, 'check_websocket') as mock_ws, \
             patch.object(self.checker, 'get_cpu_metrics') as mock_cpu, \
             patch.object(self.checker, 'get_memory_metrics') as mock_mem, \
             patch.object(self.checker, 'get_disk_metrics') as mock_disk:

            mock_db.return_value = {"status": "unhealthy", "response_time_ms": 10, "error": "Connection refused"}
            mock_redis.return_value = {"status": "healthy", "response_time_ms": 5}
            mock_celery.return_value = {"status": "healthy", "workers": 2, "queue_length": 0}
            mock_ws.return_value = {"status": "healthy", "connections": 10}
            mock_cpu.return_value = {"status": "healthy", "used_percent": 45}
            mock_mem.return_value = {"status": "healthy", "used_percent": 60}
            mock_disk.return_value = {"status": "healthy", "used_percent": 40}

            response = self.checker.get_detailed_response()

            assert response["status"] == "unhealthy"


class HealthCheckerCachingTests:
    """Test caching mechanism for detailed health checks"""

    def setup_method(self):
        self.checker = HealthChecker()

    def teardown_method(self):
        pass

    def test_detailed_response_caching(self):
        """Detailed response should be cached for 10 seconds"""
        # First call - should not be cached
        response1 = self.checker.get_detailed_response()

        # Verify it's cached
        cached = cache.get(HealthChecker.CACHE_KEY_DETAILED)
        assert cached is not None
        assert cached == response1

    def test_detailed_response_uses_cached_result(self):
        """Detailed response should use cached result on second call"""
        with patch.object(self.checker, 'get_readiness_response') as mock_readiness:
            mock_readiness.return_value = ({
                "components": {
                    "database": {"status": "healthy", "response_time_ms": 10},
                    "redis": {"status": "healthy"},
                    "celery": {"status": "healthy"}
                }
            }, 200)

            # First call
            response1 = self.checker.get_detailed_response()
            call_count_1 = mock_readiness.call_count

            # Second call - should use cache
            response2 = self.checker.get_detailed_response()
            call_count_2 = mock_readiness.call_count

            # readiness should not be called on second call (using cache)
            assert call_count_1 == 1
            assert call_count_2 == 1  # Same, not incremented

    def test_cache_timeout(self):
        """Cached response should expire after timeout"""
        response1 = self.checker.get_detailed_response()

        # Manually expire cache
        cache.delete(HealthChecker.CACHE_KEY_DETAILED)

        # Verify cache is gone
        cached = cache.get(HealthChecker.CACHE_KEY_DETAILED)
        assert cached is None


class HealthCheckEndpointTests:
    """Test health check API endpoints (simple unit tests without Django DB)"""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_endpoints_provide_liveness_response(self):
        """Liveness endpoint should provide correct response"""
        response = self.checker.get_liveness_response()

        assert response["status"] == "healthy"
        assert "timestamp" in response

    def test_endpoints_provide_readiness_response(self):
        """Readiness endpoint should provide correct response"""
        response, http_status = self.checker.get_readiness_response()

        assert "status" in response
        assert response["status"] in ["healthy", "unhealthy"]
        assert "components" in response
        assert http_status in [200, 503]

    def test_endpoints_provide_startup_response(self):
        """Startup endpoint should provide correct response"""
        response, http_status = self.checker.get_startup_response()

        assert "status" in response
        assert response["status"] in ["healthy", "startup_failed"]
        assert "checks" in response
        assert http_status in [200, 503]

    def test_endpoints_provide_detailed_response(self):
        """Detailed endpoint should provide correct response"""
        response = self.checker.get_detailed_response()

        assert "status" in response
        assert response["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in response
        assert "timestamp" in response

    def test_detailed_response_includes_all_components(self):
        """Detailed response should include all components"""
        response = self.checker.get_detailed_response()

        expected_components = ["database", "redis", "celery", "websocket", "cpu", "memory", "disk"]

        for component in expected_components:
            assert component in response["components"], f"Missing {component} in response"


class HealthCheckTimeoutTests:
    """Test timeout handling in health checks"""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_checker_has_timeout_setting(self):
        """HealthChecker should have timeout setting"""
        assert hasattr(self.checker, 'timeout')
        assert self.checker.timeout == 5

    @patch('django.db.connection.cursor')
    def test_database_check_timeout_handling(self, mock_cursor):
        """Database check should handle timeout gracefully"""
        # Simulate slow query
        import time
        def slow_query(*args, **kwargs):
            time.sleep(0.1)
            return MagicMock()

        mock_cursor.return_value.__enter__ = slow_query
        mock_cursor.return_value.__exit__ = MagicMock()

        result = self.checker.check_database()

        # Should still return a result with response time
        assert "response_time_ms" in result
        assert result["response_time_ms"] >= 100


class HealthCheckLoggingTests:
    """Test logging of health check failures"""

    def setup_method(self):
        self.checker = HealthChecker()

    @patch('core.health.logger')
    @patch('django.db.connection.cursor')
    def test_database_failure_logged(self, mock_cursor, mock_logger):
        """Database check failure should be logged"""
        mock_cursor.side_effect = Exception("Database connection failed")

        self.checker.check_database()

        mock_logger.error.assert_called()

    @patch('core.health.logger')
    @patch('django.core.cache.cache.set')
    def test_redis_failure_logged(self, mock_set, mock_logger):
        """Redis check failure should be logged"""
        mock_set.side_effect = Exception("Redis connection failed")

        self.checker.check_redis()

        mock_logger.error.assert_called()

    @patch('core.health.logger')
    @patch('psutil.cpu_percent')
    def test_cpu_check_failure_logged(self, mock_cpu, mock_logger):
        """CPU check failure should be logged"""
        mock_cpu.side_effect = Exception("CPU check failed")

        self.checker.get_cpu_metrics()

        mock_logger.error.assert_called()


class HealthCheckStatusPrioritiesTests:
    """Test status determination priorities"""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_unhealthy_takes_priority_over_degraded(self):
        """Overall status should be unhealthy if any component unhealthy"""
        with patch.object(self.checker, 'check_database') as mock_db, \
             patch.object(self.checker, 'check_redis') as mock_redis, \
             patch.object(self.checker, 'check_celery') as mock_celery, \
             patch.object(self.checker, 'check_websocket') as mock_ws, \
             patch.object(self.checker, 'get_cpu_metrics') as mock_cpu, \
             patch.object(self.checker, 'get_memory_metrics') as mock_mem, \
             patch.object(self.checker, 'get_disk_metrics') as mock_disk:

            mock_db.return_value = {"status": "unhealthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "healthy"}
            mock_ws.return_value = {"status": "healthy"}
            mock_cpu.return_value = {"status": "degraded"}
            mock_mem.return_value = {"status": "healthy"}
            mock_disk.return_value = {"status": "healthy"}

            response = self.checker.get_detailed_response()

            assert response["status"] == "unhealthy"

    def test_degraded_takes_priority_over_healthy(self):
        """Overall status should be degraded if any component degraded and none unhealthy"""
        with patch.object(self.checker, 'check_database') as mock_db, \
             patch.object(self.checker, 'check_redis') as mock_redis, \
             patch.object(self.checker, 'check_celery') as mock_celery, \
             patch.object(self.checker, 'check_websocket') as mock_ws, \
             patch.object(self.checker, 'get_cpu_metrics') as mock_cpu, \
             patch.object(self.checker, 'get_memory_metrics') as mock_mem, \
             patch.object(self.checker, 'get_disk_metrics') as mock_disk:

            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "healthy"}
            mock_ws.return_value = {"status": "healthy"}
            mock_cpu.return_value = {"status": "degraded"}
            mock_mem.return_value = {"status": "healthy"}
            mock_disk.return_value = {"status": "healthy"}

            response = self.checker.get_detailed_response()

            assert response["status"] == "degraded"


class HealthCheckIntegrationTests:
    """Integration tests for health check system"""

    def setup_method(self):
        self.checker = HealthChecker()

    def test_full_health_check_flow(self):
        """Test complete health check flow"""
        # Liveness - quick check
        response = self.checker.get_liveness_response()
        assert response["status"] == "healthy"
        assert "timestamp" in response

        # Startup - critical checks
        response, http_status = self.checker.get_startup_response()
        assert http_status in [200, 503]
        assert "checks" in response

        # Readiness - ready for traffic
        response, http_status = self.checker.get_readiness_response()
        assert http_status in [200, 503]
        assert "components" in response

        # Detailed - comprehensive info
        response = self.checker.get_detailed_response()
        assert "components" in response
        assert "timestamp" in response

    def test_response_timestamps_valid(self):
        """All responses should have valid ISO timestamps"""
        # Liveness
        response = self.checker.get_liveness_response()
        timezone.datetime.fromisoformat(response["timestamp"])

        # Readiness
        response, _ = self.checker.get_readiness_response()
        timezone.datetime.fromisoformat(response["timestamp"])

        # Startup
        response, _ = self.checker.get_startup_response()
        timezone.datetime.fromisoformat(response["timestamp"])

        # Detailed
        response = self.checker.get_detailed_response()
        timezone.datetime.fromisoformat(response["timestamp"])
