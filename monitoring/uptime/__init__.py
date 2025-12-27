"""
Uptime SLA Monitoring System

Module for monitoring and tracking Service Level Agreements (SLA).

Components:
- uptime_monitor.py: External uptime monitoring (60-second checks)
- sla_calculator.py: SLA metrics calculation and incident tracking
- status_page_generator.py: JSON data generation for status page
"""

from .uptime_monitor import UptimeMonitor, HealthCheckResult, get_monitor
from .sla_calculator import (
    SLACalculator,
    Incident,
    IncidentSeverity,
    IncidentStatus,
)
from .status_page_generator import (
    StatusPageGenerator,
    ComponentStatus,
)

__all__ = [
    'UptimeMonitor',
    'HealthCheckResult',
    'get_monitor',
    'SLACalculator',
    'Incident',
    'IncidentSeverity',
    'IncidentStatus',
    'StatusPageGenerator',
    'ComponentStatus',
]

__version__ = '1.0.0'
