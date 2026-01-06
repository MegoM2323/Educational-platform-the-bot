"""
Unit tests for health check enhancement (T_ADM_004).

Tests focus on response format and component status determination.
"""

import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone

from core.health import HealthChecker


class TestHealthCheckerLivenessResponse:
    """Test liveness endpoint response"""

    def test_liveness_response_has_status(self):
        """Liveness should always be healthy"""
        checker = HealthChecker()
        response = checker.get_liveness_response()
        assert "status" in response
        assert response["status"] == "healthy"

    def test_liveness_response_has_timestamp(self):
        """Liveness response should include timestamp"""
        checker = HealthChecker()
        response = checker.get_liveness_response()
        assert "timestamp" in response
        # Should be valid ISO format
        timezone.datetime.fromisoformat(response["timestamp"])

    def test_liveness_response_format(self):
        """Liveness response should have minimal required fields"""
        checker = HealthChecker()
        response = checker.get_liveness_response()
        assert isinstance(response, dict)
        assert len(response) == 2  # status and timestamp


class TestHealthCheckerReadinessResponse:
    """Test readiness endpoint response"""

    def test_readiness_response_includes_components(self):
        """Readiness should include all critical components"""
        checker = HealthChecker()
        response, _ = checker.get_readiness_response()

        assert "components" in response
        assert "database" in response["components"]
        assert "redis" in response["components"]
        assert "celery" in response["components"]

    def test_readiness_response_http_status(self):
        """Readiness should return correct HTTP status"""
        checker = HealthChecker()
        response, http_status = checker.get_readiness_response()

        assert http_status in [200, 503]
        if response["status"] == "healthy":
            assert http_status == 200
        else:
            assert http_status == 503

    def test_readiness_response_timestamp(self):
        """Readiness response should include timestamp"""
        checker = HealthChecker()
        response, _ = checker.get_readiness_response()
        assert "timestamp" in response
        timezone.datetime.fromisoformat(response["timestamp"])


class TestHealthCheckerStartupResponse:
    """Test startup endpoint response"""

    def test_startup_response_includes_critical_checks(self):
        """Startup should only check critical components"""
        checker = HealthChecker()
        response, _ = checker.get_startup_response()

        assert "checks" in response
        assert "database" in response["checks"]
        assert "redis" in response["checks"]
        # Celery is not critical at startup
        assert "celery" not in response["checks"]

    def test_startup_response_status_values(self):
        """Startup response should have correct status values"""
        checker = HealthChecker()
        response, _ = checker.get_startup_response()

        assert response["status"] in ["healthy", "startup_failed"]

    def test_startup_response_http_status(self):
        """Startup should return correct HTTP status"""
        checker = HealthChecker()
        response, http_status = checker.get_startup_response()

        assert http_status in [200, 503]
        if response["status"] == "healthy":
            assert http_status == 200
        else:
            assert http_status == 503

    def test_startup_sets_flag(self):
        """Startup check should update startup_checks_passed flag"""
        checker = HealthChecker()
        checker.startup_checks_passed = False

        response, _ = checker.get_startup_response()

        if response["status"] == "healthy":
            assert checker.startup_checks_passed is True
        else:
            assert checker.startup_checks_passed is False


class TestHealthCheckerDetailedResponse:
    """Test detailed endpoint response"""

    def test_detailed_response_includes_all_components(self):
        """Detailed response should include all components"""
        checker = HealthChecker()
        response = checker.get_detailed_response()

        expected_components = ["database", "redis", "celery", "websocket", "cpu", "memory", "disk"]
        assert "components" in response

        for component in expected_components:
            assert component in response["components"], f"Missing {component}"

    def test_detailed_response_status_values(self):
        """Detailed response should have correct status values"""
        checker = HealthChecker()
        response = checker.get_detailed_response()

        assert response["status"] in ["healthy", "degraded", "unhealthy"]

    def test_detailed_response_timestamp(self):
        """Detailed response should include timestamp"""
        checker = HealthChecker()
        response = checker.get_detailed_response()
        assert "timestamp" in response
        timezone.datetime.fromisoformat(response["timestamp"])

    @patch('core.health.HealthChecker.check_database')
    @patch('core.health.HealthChecker.check_redis')
    @patch('core.health.HealthChecker.check_celery')
    @patch('core.health.HealthChecker.check_websocket')
    @patch('core.health.HealthChecker.get_cpu_metrics')
    @patch('core.health.HealthChecker.get_memory_metrics')
    @patch('core.health.HealthChecker.get_disk_metrics')
    def test_detailed_response_unhealthy_when_component_unhealthy(
        self, mock_disk, mock_mem, mock_cpu, mock_ws, mock_celery, mock_redis, mock_db
    ):
        """Detailed response should be unhealthy if any component unhealthy"""
        checker = HealthChecker()

        mock_db.return_value = {"status": "unhealthy", "error": "Connection refused"}
        mock_redis.return_value = {"status": "healthy"}
        mock_celery.return_value = {"status": "healthy"}
        mock_ws.return_value = {"status": "healthy"}
        mock_cpu.return_value = {"status": "healthy"}
        mock_mem.return_value = {"status": "healthy"}
        mock_disk.return_value = {"status": "healthy"}

        response = checker.get_detailed_response()

        assert response["status"] == "unhealthy"

    @patch('django.core.cache.cache.delete')
    @patch('core.health.HealthChecker.get_readiness_response')
    @patch('core.health.HealthChecker.check_websocket')
    @patch('core.health.HealthChecker.get_cpu_metrics')
    @patch('core.health.HealthChecker.get_memory_metrics')
    @patch('core.health.HealthChecker.get_disk_metrics')
    def test_detailed_response_degraded_when_component_degraded(
        self, mock_disk, mock_mem, mock_cpu, mock_ws, mock_readiness, mock_cache_delete
    ):
        """Detailed response should be degraded if any component degraded"""
        checker = HealthChecker()

        mock_readiness.return_value = ({
            "status": "healthy",
            "components": {
                "database": {"status": "healthy"},
                "redis": {"status": "healthy"},
                "celery": {"status": "healthy"}
            }
        }, 200)
        mock_ws.return_value = {"status": "healthy"}
        mock_cpu.return_value = {"status": "degraded", "used_percent": 85}
        mock_mem.return_value = {"status": "healthy"}
        mock_disk.return_value = {"status": "healthy"}

        # Clear any cached result
        with patch('django.core.cache.cache.get', return_value=None):
            response = checker.get_detailed_response()

        assert response["status"] == "degraded"

    @patch('django.core.cache.cache.delete')
    @patch('core.health.HealthChecker.get_readiness_response')
    @patch('core.health.HealthChecker.check_websocket')
    @patch('core.health.HealthChecker.get_cpu_metrics')
    @patch('core.health.HealthChecker.get_memory_metrics')
    @patch('core.health.HealthChecker.get_disk_metrics')
    def test_detailed_response_healthy_when_all_healthy(
        self, mock_disk, mock_mem, mock_cpu, mock_ws, mock_readiness, mock_cache_delete
    ):
        """Detailed response should be healthy when all components healthy"""
        checker = HealthChecker()

        mock_readiness.return_value = ({
            "status": "healthy",
            "components": {
                "database": {"status": "healthy"},
                "redis": {"status": "healthy"},
                "celery": {"status": "healthy"}
            }
        }, 200)
        mock_ws.return_value = {"status": "healthy"}
        mock_cpu.return_value = {"status": "healthy"}
        mock_mem.return_value = {"status": "healthy"}
        mock_disk.return_value = {"status": "healthy"}

        # Clear any cached result
        with patch('django.core.cache.cache.get', return_value=None):
            response = checker.get_detailed_response()

        assert response["status"] == "healthy"


class TestHealthCheckerComponentFormats:
    """Test component response formats"""

    def test_database_component_has_required_fields(self):
        """Database component should include response time"""
        checker = HealthChecker()
        result = checker.check_database()

        assert "status" in result
        assert "response_time_ms" in result
        assert isinstance(result["response_time_ms"], int)
        assert result["response_time_ms"] >= 0

    def test_redis_component_has_required_fields(self):
        """Redis component should include response time and memory"""
        checker = HealthChecker()
        result = checker.check_redis()

        assert "status" in result
        assert "response_time_ms" in result
        assert "memory_mb" in result
        assert isinstance(result["response_time_ms"], int)

    def test_celery_component_has_required_fields(self):
        """Celery component should include workers and queue length"""
        checker = HealthChecker()
        result = checker.check_celery()

        assert "status" in result
        assert "workers" in result
        assert "queue_length" in result
        assert isinstance(result["workers"], int)
        assert isinstance(result["queue_length"], int)

    def test_websocket_component_has_required_fields(self):
        """WebSocket component should include connection info"""
        checker = HealthChecker()
        result = checker.check_websocket()

        assert "status" in result
        assert "connections" in result
        assert isinstance(result["connections"], int)

    def test_cpu_component_has_required_fields(self):
        """CPU component should include usage metrics"""
        checker = HealthChecker()
        result = checker.get_cpu_metrics()

        assert "status" in result
        assert "used_percent" in result
        assert "load_average" in result
        assert "cpu_count" in result
        assert 0 <= result["used_percent"] <= 100

    def test_memory_component_has_required_fields(self):
        """Memory component should include usage metrics"""
        checker = HealthChecker()
        result = checker.get_memory_metrics()

        assert "status" in result
        assert "used_percent" in result
        assert "available_mb" in result
        assert "total_mb" in result
        assert 0 <= result["used_percent"] <= 100

    def test_disk_component_has_required_fields(self):
        """Disk component should include usage metrics"""
        checker = HealthChecker()
        result = checker.get_disk_metrics()

        assert "status" in result
        assert "used_percent" in result
        assert "free_mb" in result
        assert "total_mb" in result
        assert 0 <= result["used_percent"] <= 100


class TestHealthCheckerStatusDetermination:
    """Test status determination logic"""

    def test_cpu_high_usage_unhealthy(self):
        """CPU over 90% should be unhealthy"""
        checker = HealthChecker()

        with patch('psutil.cpu_percent', return_value=95.0):
            result = checker.get_cpu_metrics()
            assert result["status"] == "unhealthy"

    def test_cpu_medium_usage_degraded(self):
        """CPU 80-90% should be degraded"""
        checker = HealthChecker()

        with patch('psutil.cpu_percent', return_value=85.0):
            result = checker.get_cpu_metrics()
            assert result["status"] == "degraded"

    def test_memory_high_usage_unhealthy(self):
        """Memory over 90% should be unhealthy"""
        checker = HealthChecker()

        with patch('psutil.virtual_memory') as mock_mem:
            mock_mem.return_value = MagicMock(
                percent=92.0,
                available=100 * 1024 * 1024,
                total=1000 * 1024 * 1024
            )
            result = checker.get_memory_metrics()
            assert result["status"] == "unhealthy"

    def test_disk_high_usage_unhealthy(self):
        """Disk over 90% should be unhealthy"""
        checker = HealthChecker()

        with patch('psutil.disk_usage') as mock_disk:
            mock_disk.return_value = MagicMock(
                percent=91.0,
                free=50 * 1024 * 1024,
                total=1000 * 1024 * 1024
            )
            result = checker.get_disk_metrics()
            assert result["status"] == "unhealthy"


class TestHealthCheckerTimeouts:
    """Test timeout handling"""

    def test_checker_has_timeout_setting(self):
        """HealthChecker should have timeout configuration"""
        checker = HealthChecker()
        assert hasattr(checker, 'timeout')
        assert checker.timeout == 5

    def test_cache_key_and_timeout_constants(self):
        """HealthChecker should have cache configuration"""
        assert hasattr(HealthChecker, 'CACHE_KEY_DETAILED')
        assert hasattr(HealthChecker, 'CACHE_TIMEOUT')
        assert HealthChecker.CACHE_TIMEOUT == 10
