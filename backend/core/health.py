"""
Kubernetes-ready health check endpoints and utilities.

Provides:
- Liveness endpoint: Is the service running?
- Readiness endpoint: Is the service ready to handle requests?
- Detailed endpoint: Full system metrics and diagnostics
- Startup checks: Critical component verification at startup
"""

import logging
import time
import os
import signal
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import psutil

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs system health checks for Kubernetes-ready endpoints"""

    # Cache keys
    CACHE_KEY_DETAILED = "health_check:detailed"
    CACHE_TIMEOUT = 10  # seconds

    def __init__(self):
        self.timeout = 5  # seconds for individual checks
        self.startup_checks_passed = False

    def check_liveness(self) -> bool:
        """
        Check if service is alive (running).

        Returns:
            True if service is running
        """
        return True

    def check_database(self) -> Dict[str, Any]:
        """
        Check database connectivity with response time.

        Returns:
            Dict with status and response time
        """
        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            response_time_ms = int((time.time() - start) * 1000)
            return {
                "status": "healthy",
                "response_time_ms": response_time_ms
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": 0
            }

    def check_redis(self) -> Dict[str, Any]:
        """
        Check Redis connectivity with memory usage.

        Returns:
            Dict with status and memory info
        """
        try:
            start = time.time()

            # Test set/get operations
            test_key = f"health_check:{int(time.time())}"
            result = cache.set(test_key, "ping", 10)

            response_time_ms = int((time.time() - start) * 1000)

            if not result:
                logger.warning("Redis health check: set operation failed")
                return {
                    "status": "unhealthy",
                    "error": "set operation failed",
                    "response_time_ms": response_time_ms,
                    "memory_mb": None
                }

            # Try to get Redis info for memory usage
            memory_mb = None
            try:
                from django.core.cache import caches
                redis_cache = caches.get("default")
                if hasattr(redis_cache, '_cache') and hasattr(redis_cache._cache, 'info'):
                    info = redis_cache._cache.info()
                    memory_mb = round(info.get('used_memory', 0) / (1024 * 1024), 2)
            except Exception:
                pass  # If we can't get memory info, still report as healthy

            # Clean up test key
            try:
                cache.delete(test_key)
            except Exception:
                pass

            return {
                "status": "healthy",
                "response_time_ms": response_time_ms,
                "memory_mb": memory_mb
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": 0,
                "memory_mb": None
            }

    def check_celery(self) -> Dict[str, Any]:
        """
        Check Celery worker status and task queue.

        Returns:
            Dict with status, worker count and queue length
        """
        try:
            from celery import current_app

            start = time.time()

            # Get Celery inspector
            inspector = current_app.control.inspect()

            # Get active tasks
            active_tasks = inspector.active()
            reserved_tasks = inspector.reserved()
            registered_tasks = inspector.registered()

            response_time_ms = int((time.time() - start) * 1000)

            # Count workers
            worker_count = 0
            if active_tasks:
                worker_count = len(active_tasks)

            # Count pending tasks
            queue_length = 0
            if active_tasks:
                for tasks in active_tasks.values():
                    queue_length += len(tasks)
            if reserved_tasks:
                for tasks in reserved_tasks.values():
                    queue_length += len(tasks)

            # Check if we have workers
            if worker_count == 0:
                logger.warning("No Celery workers detected")
                return {
                    "status": "unhealthy",
                    "error": "No active workers",
                    "response_time_ms": response_time_ms,
                    "workers": 0,
                    "queue_length": 0
                }

            return {
                "status": "healthy",
                "response_time_ms": response_time_ms,
                "workers": worker_count,
                "queue_length": queue_length
            }
        except Exception as e:
            logger.error(f"Celery health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": 0,
                "workers": 0,
                "queue_length": 0
            }

    def check_websocket(self) -> Dict[str, Any]:
        """
        Check WebSocket service status.

        Returns:
            Dict with WebSocket connection info
        """
        try:
            # For now, check if Channels is installed
            from channels.auth import AuthMiddlewareStack
            from channels.db import database_sync_to_async

            # Try to establish a test connection count
            # In production with Channels, this would connect to the socket
            connections = 0

            # Simple check: can we import and instantiate auth middleware
            try:
                middleware = AuthMiddlewareStack(lambda x: x)
                connections = 1  # If we can create it, WebSocket is available
            except Exception:
                pass

            return {
                "status": "healthy",
                "connections": connections
            }
        except ImportError:
            logger.warning("Channels not installed - WebSocket disabled")
            return {
                "status": "healthy",
                "connections": 0,
                "note": "Channels not installed"
            }
        except Exception as e:
            logger.error(f"WebSocket health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connections": 0
            }

    def get_cpu_metrics(self) -> Dict[str, Any]:
        """
        Get CPU usage metrics.

        Returns:
            Dict with CPU status and metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

            status = "healthy"
            if cpu_percent > 90:
                status = "unhealthy"
            elif cpu_percent > 80:
                status = "degraded"

            return {
                "status": status,
                "used_percent": round(cpu_percent, 2),
                "load_average": round(load_avg[0], 2),
                "cpu_count": psutil.cpu_count()
            }
        except Exception as e:
            logger.error(f"CPU metrics check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "used_percent": 0,
                "load_average": 0,
                "cpu_count": 0
            }

    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        Get memory usage metrics.

        Returns:
            Dict with memory status and metrics
        """
        try:
            memory = psutil.virtual_memory()

            status = "healthy"
            if memory.percent > 90:
                status = "unhealthy"
            elif memory.percent > 80:
                status = "degraded"

            return {
                "status": status,
                "used_percent": round(memory.percent, 2),
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "total_mb": round(memory.total / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Memory metrics check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "used_percent": 0,
                "available_mb": 0,
                "total_mb": 0
            }

    def get_disk_metrics(self) -> Dict[str, Any]:
        """
        Get disk usage metrics.

        Returns:
            Dict with disk status and metrics
        """
        try:
            disk = psutil.disk_usage("/")

            status = "healthy"
            if disk.percent > 90:
                status = "unhealthy"
            elif disk.percent > 80:
                status = "degraded"

            return {
                "status": status,
                "used_percent": round(disk.percent, 2),
                "free_mb": round(disk.free / (1024 * 1024), 2),
                "total_mb": round(disk.total / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Disk metrics check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "used_percent": 0,
                "free_mb": 0,
                "total_mb": 0
            }

    def get_liveness_response(self) -> Dict[str, Any]:
        """
        Get response for liveness endpoint (quick check).

        Used by Kubernetes to check if pod should be restarted.
        No heavy checks - just verify process is running.

        Response format:
        {
            "status": "healthy",
            "timestamp": "2025-12-27T10:00:00Z"
        }

        Returns:
            Dict with liveness status
        """
        return {
            "status": "healthy",
            "timestamp": timezone.now().isoformat()
        }

    def get_readiness_response(self) -> Tuple[Dict[str, Any], int]:
        """
        Get response for readiness endpoint (startup checks).

        Checks if service is ready to handle requests:
        - Database connectivity
        - Redis connectivity
        - Celery task queue

        Response format:
        {
            "status": "healthy",
            "components": {
                "database": {"status": "healthy", "response_time_ms": 15},
                "redis": {"status": "healthy", "memory_mb": 256},
                "celery": {"status": "healthy", "workers": 4, "queue_length": 2}
            },
            "timestamp": "2025-12-27T10:00:00Z"
        }

        Returns:
            Tuple of (response_dict, http_status_code)
        """
        response = {
            "status": "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "components": {}
        }

        # Check database
        response["components"]["database"] = self.check_database()

        # Check Redis
        response["components"]["redis"] = self.check_redis()

        # Check Celery
        response["components"]["celery"] = self.check_celery()

        # Determine overall status
        all_healthy = all(
            component.get("status") == "healthy"
            for component in response["components"].values()
        )

        if all_healthy:
            response["status"] = "healthy"
            http_status = 200
        else:
            response["status"] = "unhealthy"
            http_status = 503

        return response, http_status

    def get_startup_response(self) -> Tuple[Dict[str, Any], int]:
        """
        Get response for startup probe (critical checks only).

        Checks only critical components required at startup:
        - Database connectivity
        - Redis connectivity

        Response format:
        {
            "status": "healthy",
            "checks": {
                "database": {"status": "healthy", "response_time_ms": 15},
                "redis": {"status": "healthy", "memory_mb": 256}
            },
            "timestamp": "2025-12-27T10:00:00Z"
        }

        Returns:
            Tuple of (response_dict, http_status_code)
        """
        response = {
            "status": "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "checks": {}
        }

        # Critical checks only
        response["checks"]["database"] = self.check_database()
        response["checks"]["redis"] = self.check_redis()

        # Both must be healthy
        all_healthy = all(
            check.get("status") == "healthy"
            for check in response["checks"].values()
        )

        if all_healthy:
            response["status"] = "healthy"
            http_status = 200
            self.startup_checks_passed = True
        else:
            response["status"] = "startup_failed"
            http_status = 503
            self.startup_checks_passed = False

        return response, http_status

    def get_detailed_response(self) -> Dict[str, Any]:
        """
        Get full health check response with all metrics (cached).

        Includes:
        - All readiness checks (database, redis, celery)
        - CPU, memory, disk usage
        - WebSocket status

        Results are cached for 10 seconds to reduce load.

        Response format:
        {
            "status": "healthy|degraded|unhealthy",
            "components": {
                "database": {"status": "healthy", "response_time_ms": 15},
                "redis": {"status": "healthy", "memory_mb": 256},
                "celery": {"status": "healthy", "workers": 4, "queue_length": 2},
                "websocket": {"status": "healthy", "connections": 150},
                "disk": {"status": "healthy", "used_percent": 45},
                "memory": {"status": "healthy", "used_percent": 62},
                "cpu": {"status": "healthy", "load_avg": 2.5}
            },
            "timestamp": "2025-12-27T10:00:00Z"
        }

        Returns:
            Dict with comprehensive health information
        """
        # Try to get cached result
        cached = cache.get(self.CACHE_KEY_DETAILED)
        if cached is not None:
            logger.debug("Using cached detailed health check")
            return cached

        response = {
            "status": "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "components": {}
        }

        # Get readiness checks
        readiness_response, _ = self.get_readiness_response()
        response["components"].update(readiness_response.get("components", {}))

        # Add system metrics
        response["components"]["websocket"] = self.check_websocket()
        response["components"]["cpu"] = self.get_cpu_metrics()
        response["components"]["memory"] = self.get_memory_metrics()
        response["components"]["disk"] = self.get_disk_metrics()

        # Determine overall health status
        has_unhealthy = any(
            component.get("status") == "unhealthy"
            for component in response["components"].values()
        )
        has_degraded = any(
            component.get("status") == "degraded"
            for component in response["components"].values()
        )

        if has_unhealthy:
            response["status"] = "unhealthy"
        elif has_degraded:
            response["status"] = "degraded"
        else:
            response["status"] = "healthy"

        # Cache the result
        try:
            cache.set(self.CACHE_KEY_DETAILED, response, self.CACHE_TIMEOUT)
        except Exception as e:
            logger.warning(f"Failed to cache detailed health check: {str(e)}")

        return response


# Global health checker instance
health_checker = HealthChecker()
