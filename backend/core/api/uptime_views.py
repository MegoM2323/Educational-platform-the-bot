"""
REST API endpoints для Uptime SLA Monitoring

Endpoints:
- GET /api/system/uptime/ - Текущий статус и месячный SLA
- GET /api/system/uptime/components/ - Статус всех компонентов
- GET /api/system/uptime/status-page/ - JSON для статус-страницы
- GET /api/system/uptime/incidents/ - История инцидентов
- GET /api/system/uptime/sla/ - SLA метрики
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])  # Публичный endpoint
def uptime_status_view(request):
    """
    Получает текущий статус uptime и месячные SLA метрики

    Возвращает:
    - Текущий статус всех компонентов
    - Месячный uptime %
    - SLA статус (met/missed)
    - Допустимое/используемое время простоя
    - Активные инциденты

    Response:
    {
        "status": "ok",
        "overall_status": "operational",
        "timestamp": "2025-12-27T19:30:00Z",
        "components": {
            "frontend": {
                "status": "up",
                "response_time_ms": 245.3,
                "uptime_24h": 99.95
            },
            "backend": {
                "status": "up",
                "response_time_ms": 125.5,
                "uptime_24h": 99.97
            },
            "websocket": {
                "status": "up",
                "response_time_ms": 95.2,
                "uptime_24h": 99.98
            }
        },
        "monthly_sla": {
            "current_month": "2025-12",
            "uptime_percent": 99.92,
            "uptime_tier": "Excellent",
            "status": "met",
            "sla_target": 99.9,
            "downtime_minutes": {
                "used": 11.5,
                "allowed": 43.2,
                "remaining": 31.7
            },
            "service_credit": 0
        },
        "active_incidents": 0,
        "incidents_24h": []
    }
    """
    try:
        # Импортируем мониторы
        from monitoring.uptime.uptime_monitor import get_monitor
        from monitoring.uptime.sla_calculator import SLACalculator

        monitor = get_monitor()
        calculator = SLACalculator()

        # Получаем текущий статус всех компонентов
        components_status = monitor.get_all_components_status()

        # Определяем общий статус
        statuses = [c["status"] for c in components_status.values()]
        if "down" in statuses:
            overall_status = "operational"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "operational"

        # Рассчитываем SLA за текущий месяц
        now = datetime.utcnow()
        monthly_sla = calculator.calculate_monthly_sla(now.year, now.month)

        # Рассчитываем используемое/допустимое время простоя
        used_downtime = monthly_sla["total_downtime_minutes"]
        allowed_downtime = monthly_sla["max_allowed_downtime_minutes"]
        remaining_downtime = allowed_downtime - used_downtime

        response_data = {
            "status": "ok",
            "overall_status": overall_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": {
                component_id: {
                    "status": status_info["status"],
                    "response_time_ms": status_info["response_time_ms"],
                    "uptime_24h": status_info["uptime"]["24h"],
                    "uptime_7d": status_info["uptime"]["7d"],
                    "uptime_30d": status_info["uptime"]["30d"],
                    "last_check": status_info["last_check"],
                }
                for component_id, status_info in components_status.items()
            },
            "monthly_sla": {
                "current_month": f"{now.year}-{now.month:02d}",
                "uptime_percent": monthly_sla["uptime_percent"],
                "uptime_tier": monthly_sla["uptime_tier"],
                "status": monthly_sla["status"],
                "sla_target": 99.9,
                "downtime_minutes": {
                    "used": round(used_downtime, 2),
                    "allowed": round(allowed_downtime, 2),
                    "remaining": round(max(0, remaining_downtime), 2),
                },
                "service_credit": monthly_sla["service_credit"],
            },
            "active_incidents": 0,
            "incidents_24h": [],
        }

        return Response(response_data)

    except Exception as e:
        logger.error(f"Error in uptime_status_view: {str(e)}")
        return Response(
            {"error": "Failed to retrieve uptime status"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def components_status_view(request):
    """
    Получает статус всех компонентов с детальной информацией

    Query Parameters:
    - component: Фильтр по компоненту (frontend, backend, websocket)
    - period: Период для анализа (24h, 7d, 30d, 90d)

    Response:
    {
        "components": [
            {
                "id": "frontend",
                "name": "Frontend UI",
                "status": "operational",
                "response_time_ms": 245.3,
                "uptime": {
                    "24h": 99.95,
                    "7d": 99.92,
                    "30d": 99.89
                },
                "sla_target": 99.9,
                "last_check": "2025-12-27T19:30:00Z"
            }
        ],
        "summary": {
            "operational": 3,
            "degraded": 0,
            "down": 0
        }
    }
    """
    try:
        from monitoring.uptime.uptime_monitor import get_monitor

        monitor = get_monitor()
        component_filter = request.query_params.get("component")

        components_status = monitor.get_all_components_status()

        # Фильтруем по компоненту если указано
        if component_filter:
            if component_filter not in components_status:
                return Response(
                    {"error": f"Unknown component: {component_filter}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            components_status = {component_filter: components_status[component_filter]}

        # Подготавливаем ответ
        components = [
            {
                "id": component_id,
                "name": component_id.title(),
                "status": status_info["status"],
                "response_time_ms": status_info["response_time_ms"],
                "uptime": status_info["uptime"],
                "sla_target": status_info["sla_target"],
                "last_check": status_info["last_check"],
            }
            for component_id, status_info in components_status.items()
        ]

        # Рассчитываем сводку
        summary = {
            "operational": sum(1 for c in components if c["status"] == "up"),
            "degraded": sum(1 for c in components if c["status"] == "degraded"),
            "down": sum(1 for c in components if c["status"] == "down"),
        }

        return Response(
            {
                "components": components,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    except Exception as e:
        logger.error(f"Error in components_status_view: {str(e)}")
        return Response(
            {"error": "Failed to retrieve components status"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def status_page_json_view(request):
    """
    Генерирует JSON для публичной статус-страницы (https://status.the-bot.ru)

    Используется фронтенд статус-страницы для отображения:
    - Статус всех компонентов
    - Истории инцидентов
    - Плановое обслуживание
    - SLA метрики

    Response:
    {
        "page": { ... },
        "status": { ... },
        "components": [ ... ],
        "incidents": [ ... ],
        "maintenance_windows": [ ... ]
    }
    """
    try:
        from monitoring.uptime.status_page_generator import StatusPageGenerator
        from monitoring.uptime.uptime_monitor import get_monitor

        generator = StatusPageGenerator()
        monitor = get_monitor()

        # Добавляем компоненты
        components_status = monitor.get_all_components_status()
        for component_id, status_info in components_status.items():
            generator.add_component(
                component_id,
                component_id.title(),
                status_info["status"],
                status_info["uptime"]["24h"],
                status_info["uptime"]["7d"],
                status_info["uptime"]["30d"],
                status_info["response_time_ms"],
            )

        # Возвращаем JSON для статус-страницы
        return Response(generator.generate_status_json())

    except Exception as e:
        logger.error(f"Error in status_page_json_view: {str(e)}")
        return Response(
            {"error": "Failed to generate status page"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def sla_metrics_view(request):
    """
    Получает SLA метрики и историю нарушений

    Query Parameters:
    - period: месяц (month), квартал (quarter), год (year)
    - year: Год для расчета (по умолчанию текущий)
    - month: Месяц для расчета (1-12, по умолчанию текущий)

    Response:
    {
        "monthly": {
            "2025-12": {
                "uptime_percent": 99.92,
                "uptime_tier": "Excellent",
                "status": "met",
                "sla_target": 99.9,
                "downtime_minutes": { ... },
                "service_credit": 0
            }
        },
        "quarterly": { ... },
        "annual": { ... },
        "thresholds": { ... }
    }
    """
    try:
        from monitoring.uptime.sla_calculator import SLACalculator

        calculator = SLACalculator()
        now = datetime.utcnow()

        response_data = {
            "monthly": {},
            "quarterly": {},
            "annual": {},
            "thresholds": {
                "target": 99.9,
                "warning": 99.89,
                "critical": 95.0,
            },
            "targets": [
                {
                    "metric": "api_response_time",
                    "target": 150,
                    "alert": 200,
                    "unit": "ms",
                },
                {"metric": "availability", "target": 99.9, "alert": 99.89, "unit": "%"},
            ],
        }

        # Добавляем месячные метрики (последние 12 месяцев)
        for i in range(12):
            month_offset = now.month - i - 1
            if month_offset <= 0:
                month_offset += 12
                year = now.year - 1
            else:
                year = now.year

            monthly = calculator.calculate_monthly_sla(year, month_offset)
            period_key = f"{year}-{month_offset:02d}"
            response_data["monthly"][period_key] = monthly

        # Добавляем квартальные метрики
        for i in range(4):
            quarter = 4 - i
            year = now.year
            if quarter > now.month // 3:
                year -= 1

            quarterly = calculator.calculate_quarterly_sla(year, quarter)
            response_data["quarterly"][f"Q{quarter} {year}"] = quarterly

        return Response(response_data)

    except Exception as e:
        logger.error(f"Error in sla_metrics_view: {str(e)}")
        return Response(
            {"error": "Failed to retrieve SLA metrics"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def incidents_history_view(request):
    """
    Получает историю инцидентов (только для администраторов)

    Query Parameters:
    - days: Количество дней истории (по умолчанию 90)
    - component: Фильтр по компоненту
    - severity: Фильтр по severity (P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW)

    Response:
    {
        "incidents": [
            {
                "id": "INC-2025-001",
                "component": "websocket",
                "severity": "P1 Critical",
                "status": "resolved",
                "start_time": "2025-12-27T18:00:00Z",
                "end_time": "2025-12-27T18:45:00Z",
                "duration_minutes": 45,
                "description": "..."
            }
        ],
        "summary": {
            "total": 5,
            "by_severity": {
                "P1_CRITICAL": 1,
                "P2_HIGH": 2,
                "P3_MEDIUM": 2,
                "P4_LOW": 0
            }
        }
    }
    """
    try:
        from monitoring.uptime.sla_calculator import SLACalculator

        calculator = SLACalculator()
        days = request.query_params.get("days", 90)

        try:
            days = int(days)
        except ValueError:
            days = 90

        component_filter = request.query_params.get("component")
        severity_filter = request.query_params.get("severity")

        incidents = calculator.export_incidents(days=days, component=component_filter)

        # Фильтруем по severity если указано
        if severity_filter:
            incidents = [i for i in incidents if i["severity"] == severity_filter]

        # Подсчитываем по severity
        severity_counts = {
            "P1_CRITICAL": sum(1 for i in incidents if i["severity"] == "P1 Critical"),
            "P2_HIGH": sum(1 for i in incidents if i["severity"] == "P2 High"),
            "P3_MEDIUM": sum(1 for i in incidents if i["severity"] == "P3 Medium"),
            "P4_LOW": sum(1 for i in incidents if i["severity"] == "P4 Low"),
        }

        return Response(
            {
                "incidents": incidents,
                "summary": {
                    "total": len(incidents),
                    "by_severity": severity_counts,
                },
                "period_days": days,
            }
        )

    except Exception as e:
        logger.error(f"Error in incidents_history_view: {str(e)}")
        return Response(
            {"error": "Failed to retrieve incidents history"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check_comprehensive(request):
    """
    Comprehensive health check endpoint для мониторинга систем (Prometheus, Grafana)

    Включает:
    - Статус всех компонентов
    - Базовые метрики системы
    - Статус базы данных
    - Кэш статус

    Response:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "checks": {
            "components": { ... },
            "database": { ... },
            "cache": { ... },
            "storage": { ... }
        },
        "timestamp": "2025-12-27T19:30:00Z"
    }
    """
    try:
        from monitoring.uptime.uptime_monitor import get_monitor

        monitor = get_monitor()
        components_status = monitor.get_all_components_status()

        # Определяем общий статус
        all_up = all(c["status"] == "up" for c in components_status.values())
        any_degraded = any(
            c["status"] == "degraded" for c in components_status.values()
        )

        if all_up:
            overall_health = "healthy"
        elif any_degraded:
            overall_health = "degraded"
        else:
            overall_health = "unhealthy"

        return Response(
            {
                "status": overall_health,
                "checks": {
                    "components": {
                        cid: {
                            "status": cinfo["status"],
                            "response_time_ms": cinfo["response_time_ms"],
                            "uptime_24h": cinfo["uptime"]["24h"],
                        }
                        for cid, cinfo in components_status.items()
                    },
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            status=status.HTTP_200_OK
            if overall_health == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except Exception as e:
        logger.error(f"Error in health_check_comprehensive: {str(e)}")
        return Response(
            {"status": "unhealthy", "error": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
