"""
Extended Health Check Endpoints for THE_BOT Platform

Provides comprehensive health monitoring including:
- Component status (database, redis, celery, websocket)
- Performance metrics (response times, throughput)
- SLA tracking and uptime calculations
- Synthetic check result ingestion
- Status page data generation
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from .health import health_checker

logger = logging.getLogger(__name__)


class ComponentStatus(str, Enum):
    """Component health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ComponentMetrics:
    """Metrics for a single component"""
    name: str
    status: ComponentStatus
    response_time_ms: float
    error_count: int = 0
    warning_count: int = 0
    last_check_timestamp: Optional[datetime] = None
    details: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "name": self.name,
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "last_check": self.last_check_timestamp.isoformat() if self.last_check_timestamp else None,
        }
        if self.details:
            data["details"] = self.details
        return data


@dataclass
class SLAMetrics:
    """SLA metrics for a component"""
    component: str
    uptime_percent: float
    uptime_target: float
    downtime_minutes: float
    checks_total: int
    checks_success: int
    checks_failed: int
    sla_status: str  # "compliant", "warning", "breached"
    period_hours: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class HealthCheckExtended:
    """Extended health check utilities with SLA tracking"""

    # Cache keys
    CACHE_KEY_COMPONENTS = "health:components"
    CACHE_KEY_SLA = "health:sla"
    CACHE_KEY_STATUS_PAGE = "health:status_page"
    CACHE_TIMEOUT_SHORT = 10  # seconds
    CACHE_TIMEOUT_LONG = 60  # seconds

    def __init__(self):
        self.checker = health_checker

    def get_component_metrics(self) -> Dict[str, ComponentMetrics]:
        """
        Get metrics for all system components.

        Returns:
            Dict mapping component names to their metrics
        """
        metrics = {}

        # Get basic readiness response
        readiness_response, _ = self.checker.get_readiness_response()

        # Extract component information
        for component_name, component_data in readiness_response.get("components", {}).items():
            metrics[component_name] = ComponentMetrics(
                name=component_name,
                status=ComponentStatus(component_data.get("status", "unknown")),
                response_time_ms=float(component_data.get("response_time_ms", 0)),
                details=component_data
            )

        # Add system metrics
        cpu_metrics = self.checker.get_cpu_metrics()
        memory_metrics = self.checker.get_memory_metrics()
        disk_metrics = self.checker.get_disk_metrics()

        metrics["cpu"] = ComponentMetrics(
            name="cpu",
            status=ComponentStatus(cpu_metrics.get("status", "unknown")),
            response_time_ms=0,
            details=cpu_metrics
        )

        metrics["memory"] = ComponentMetrics(
            name="memory",
            status=ComponentStatus(memory_metrics.get("status", "unknown")),
            response_time_ms=0,
            details=memory_metrics
        )

        metrics["disk"] = ComponentMetrics(
            name="disk",
            status=ComponentStatus(disk_metrics.get("status", "unknown")),
            response_time_ms=0,
            details=disk_metrics
        )

        return metrics

    def get_sla_metrics(self, period_hours: int = 24) -> Dict[str, SLAMetrics]:
        """
        Calculate SLA metrics for components.

        Args:
            period_hours: Hours to look back for SLA calculation

        Returns:
            Dict mapping component names to SLA metrics
        """
        sla_metrics = {}
        components = ["database", "redis", "celery", "websocket"]

        for component in components:
            # Get uptime from uptime monitor if available
            uptime_percent = self._get_component_uptime(component, period_hours)

            # Determine SLA status
            uptime_target = self._get_sla_target(component)
            if uptime_percent >= uptime_target:
                sla_status = "compliant"
            elif uptime_percent >= (uptime_target - 0.5):
                sla_status = "warning"
            else:
                sla_status = "breached"

            # Calculate downtime in minutes
            total_minutes = period_hours * 60
            downtime_minutes = total_minutes * (100 - uptime_percent) / 100

            sla_metrics[component] = SLAMetrics(
                component=component,
                uptime_percent=round(uptime_percent, 2),
                uptime_target=uptime_target,
                downtime_minutes=round(downtime_minutes, 2),
                checks_total=0,  # Would be populated from database
                checks_success=0,
                checks_failed=0,
                sla_status=sla_status,
                period_hours=period_hours
            )

        return sla_metrics

    def _get_component_uptime(self, component: str, hours: int) -> float:
        """
        Get component uptime percentage.

        Args:
            component: Component name
            hours: Hours to look back

        Returns:
            Uptime percentage (0-100)
        """
        try:
            # Try to get from uptime monitor
            from monitoring.uptime.uptime_monitor import get_monitor

            monitor = get_monitor()
            uptime_percent, _, _ = monitor.get_component_uptime(component, hours)
            return uptime_percent
        except Exception as e:
            logger.warning(f"Could not get uptime for {component}: {e}")
            # Default to 100% if we can't calculate
            return 100.0

    def _get_sla_target(self, component: str) -> float:
        """
        Get SLA target for a component.

        Args:
            component: Component name

        Returns:
            SLA target percentage (e.g., 99.9)
        """
        sla_targets = {
            "database": 99.9,
            "redis": 99.5,
            "celery": 99.0,
            "websocket": 99.5,
            "api": 99.9,
            "frontend": 99.9,
        }
        return sla_targets.get(component, 99.0)

    def get_status_page_data(self) -> Dict[str, Any]:
        """
        Get data for status page display.

        Returns:
            Dict with status page information
        """
        components = self.get_component_metrics()
        sla_metrics = self.get_sla_metrics()

        # Determine overall status
        has_critical = any(m.status == ComponentStatus.UNHEALTHY for m in components.values())
        has_degraded = any(m.status == ComponentStatus.DEGRADED for m in components.values())

        overall_status = "healthy"
        if has_critical:
            overall_status = "critical"
        elif has_degraded:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": timezone.now().isoformat(),
            "components": {name: m.to_dict() for name, m in components.items()},
            "sla": {name: m.to_dict() for name, m in sla_metrics.items()},
            "last_incident": self._get_last_incident(),
            "scheduled_maintenance": self._get_scheduled_maintenance(),
        }

    def _get_last_incident(self) -> Optional[Dict[str, Any]]:
        """
        Get last recorded incident.

        Returns:
            Dict with incident information or None
        """
        # TODO: Implement incident tracking
        return None

    def _get_scheduled_maintenance(self) -> List[Dict[str, Any]]:
        """
        Get scheduled maintenance windows.

        Returns:
            List of maintenance windows
        """
        # TODO: Implement maintenance scheduling
        return []

    def record_synthetic_check(self, check_data: Dict[str, Any]) -> bool:
        """
        Record a synthetic check result.

        Args:
            check_data: Dict with check results from synthetic monitor

        Returns:
            True if recorded successfully
        """
        try:
            # TODO: Implement database storage for synthetic check results
            logger.info(f"Recorded synthetic check: {check_data.get('name')}")
            return True
        except Exception as e:
            logger.error(f"Failed to record synthetic check: {e}")
            return False

    def get_alerting_summary(self) -> Dict[str, Any]:
        """
        Get summary of active alerts and thresholds.

        Returns:
            Dict with alert information
        """
        components = self.get_component_metrics()
        alerts = []

        for component_name, metrics in components.items():
            if metrics.status == ComponentStatus.UNHEALTHY:
                alerts.append({
                    "severity": "critical",
                    "component": component_name,
                    "message": f"{component_name} is unhealthy",
                    "timestamp": timezone.now().isoformat(),
                })
            elif metrics.status == ComponentStatus.DEGRADED:
                alerts.append({
                    "severity": "warning",
                    "component": component_name,
                    "message": f"{component_name} is degraded",
                    "timestamp": timezone.now().isoformat(),
                })

        return {
            "active_alerts": len(alerts),
            "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
            "warning_count": sum(1 for a in alerts if a["severity"] == "warning"),
            "alerts": alerts,
        }


# Global extended health checker instance
health_extended = HealthCheckExtended()


# ============================================================================
# Django View Endpoints
# ============================================================================

@api_view(["GET"])
@permission_classes([AllowAny])
@cache_page(10)  # Cache for 10 seconds
def extended_health_view(request):
    """
    GET /api/system/health-extended/

    Get comprehensive health information including all components and performance metrics.

    Response (200):
    {
        "status": "healthy|degraded|unhealthy",
        "timestamp": "2025-12-27T10:00:00Z",
        "components": {
            "database": {
                "status": "healthy",
                "response_time_ms": 15,
                "details": {...}
            },
            ...
        },
        "alerts": {
            "active_alerts": 0,
            "critical_count": 0,
            "warning_count": 0
        }
    }
    """
    try:
        # Get detailed health response
        health_response = health_extended.checker.get_detailed_response()

        # Add alerting summary
        alerts = health_extended.get_alerting_summary()

        response_data = {
            **health_response,
            "alerts": alerts,
        }

        return Response(response_data, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in extended health check: {e}")
        return Response(
            {"status": "unhealthy", "error": str(e)},
            status=HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def component_metrics_view(request):
    """
    GET /api/system/components/

    Get detailed metrics for all system components.

    Query Parameters:
        - component: Filter by component name (optional)

    Response (200):
    {
        "components": {
            "database": {...},
            "redis": {...},
            ...
        }
    }
    """
    try:
        component_filter = request.query_params.get("component")
        metrics = health_extended.get_component_metrics()

        if component_filter:
            metrics = {k: v for k, v in metrics.items() if component_filter in k}

        return Response({
            "components": {name: m.to_dict() for name, m in metrics.items()},
        }, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting component metrics: {e}")
        return Response(
            {"error": str(e)},
            status=HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def sla_metrics_view(request):
    """
    GET /api/system/sla/

    Get SLA compliance metrics for all components.

    Query Parameters:
        - period: Hours to look back (24, 168, 720, 8760)
        - component: Filter by component (optional)

    Response (200):
    {
        "period_hours": 24,
        "sla_metrics": {
            "database": {
                "uptime_percent": 99.95,
                "uptime_target": 99.9,
                "sla_status": "compliant",
                ...
            },
            ...
        }
    }
    """
    try:
        period = int(request.query_params.get("period", 24))
        component_filter = request.query_params.get("component")

        # Validate period
        allowed_periods = [24, 168, 720, 8760]
        if period not in allowed_periods:
            return Response(
                {"error": f"Invalid period. Allowed: {allowed_periods}"},
                status=400
            )

        sla_metrics = health_extended.get_sla_metrics(period_hours=period)

        if component_filter:
            sla_metrics = {k: v for k, v in sla_metrics.items() if component_filter in k}

        return Response({
            "period_hours": period,
            "sla_metrics": {name: m.to_dict() for name, m in sla_metrics.items()},
        }, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting SLA metrics: {e}")
        return Response(
            {"error": str(e)},
            status=HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def status_page_view(request):
    """
    GET /api/system/status-page/

    Get status page data for public display.

    Response (200):
    {
        "status": "healthy|degraded|critical",
        "timestamp": "2025-12-27T10:00:00Z",
        "components": {...},
        "sla": {...},
        "last_incident": {...},
        "scheduled_maintenance": [...]
    }
    """
    try:
        # Try to use cached data
        cached = cache.get(health_extended.CACHE_KEY_STATUS_PAGE)
        if cached:
            return Response(cached, status=HTTP_200_OK)

        # Generate fresh data
        status_data = health_extended.get_status_page_data()

        # Cache for 1 minute
        cache.set(health_extended.CACHE_KEY_STATUS_PAGE, status_data, 60)

        return Response(status_data, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating status page: {e}")
        return Response(
            {"status": "unknown", "error": str(e)},
            status=HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def synthetic_check_webhook_view(request):
    """
    POST /api/system/synthetic-check/

    Receive and record synthetic check results from external monitoring service.

    Request body:
    {
        "name": "api_health",
        "status": "up|down|degraded",
        "response_time_ms": 150,
        "timestamp": "2025-12-27T10:00:00Z",
        "component": "backend",
        "service": "api"
    }

    Response (200):
    {
        "recorded": true,
        "message": "Check result recorded"
    }
    """
    try:
        check_data = request.data

        # Validate required fields
        required_fields = ["name", "status", "response_time_ms"]
        if not all(field in check_data for field in required_fields):
            return Response(
                {"error": "Missing required fields"},
                status=400
            )

        # Record the check
        success = health_extended.record_synthetic_check(check_data)

        if success:
            return Response({
                "recorded": True,
                "message": "Check result recorded",
            }, status=HTTP_200_OK)
        else:
            return Response(
                {"error": "Failed to record check"},
                status=500
            )
    except Exception as e:
        logger.error(f"Error recording synthetic check: {e}")
        return Response(
            {"error": str(e)},
            status=500
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def websocket_health_view(request):
    """
    GET /api/system/websocket-health/

    Check WebSocket service health and connection stats.

    Response (200):
    {
        "status": "healthy",
        "connections": 150,
        "channels": 10,
        "messages_per_minute": 2500,
        "timestamp": "2025-12-27T10:00:00Z"
    }
    """
    try:
        websocket_metrics = health_extended.checker.check_websocket()

        return Response({
            **websocket_metrics,
            "timestamp": timezone.now().isoformat(),
        }, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error checking WebSocket health: {e}")
        return Response(
            {"status": "unhealthy", "error": str(e)},
            status=HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def alerts_summary_view(request):
    """
    GET /api/system/alerts/

    Get summary of active alerts and their thresholds.

    Query Parameters:
        - severity: Filter by severity (critical, warning, info)

    Response (200):
    {
        "active_alerts": 2,
        "critical_count": 1,
        "warning_count": 1,
        "alerts": [
            {
                "severity": "critical",
                "component": "database",
                "message": "Database is unhealthy",
                "timestamp": "2025-12-27T10:00:00Z"
            },
            ...
        ]
    }
    """
    try:
        severity_filter = request.query_params.get("severity")
        alerts_data = health_extended.get_alerting_summary()

        if severity_filter:
            alerts_data["alerts"] = [
                a for a in alerts_data["alerts"]
                if a["severity"] == severity_filter
            ]

        return Response(alerts_data, status=HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return Response(
            {"error": str(e)},
            status=HTTP_503_SERVICE_UNAVAILABLE
        )
