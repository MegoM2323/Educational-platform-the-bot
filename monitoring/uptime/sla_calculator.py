"""
SLA Calculator - Расчет метрик соответствия соглашениям об уровне обслуживания

Рассчитывает:
- Процент доступности (99.9% целевой показатель)
- Допустимое время простоя в месяц (43.2 минуты для 99.9%)
- Категоризацию инцидентов по severity (P1-P4)
- Исторические данные SLA (90 дней)
- Оповещения при превышении пороговых значений
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Уровень серьезности инцидентов"""
    P1_CRITICAL = 'P1 Critical'  # Система полностью недоступна
    P2_HIGH = 'P2 High'  # Критическая функция недоступна
    P3_MEDIUM = 'P3 Medium'  # Функция частично недоступна
    P4_LOW = 'P4 Low'  # Минорная проблема


class IncidentStatus(Enum):
    """Статус инцидента"""
    OPEN = 'open'
    INVESTIGATING = 'investigating'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'


@dataclass
class UptimeTier:
    """Уровень uptime и соответствующий сервисный кредит"""
    name: str
    min_uptime: float  # Минимальный процент uptime
    max_uptime: float  # Максимальный процент uptime
    max_downtime_minutes: float  # Макс время простоя в минутах за месяц
    service_credit: int  # Процент возврата платежа


@dataclass
class SLATarget:
    """Целевые показатели SLA"""
    name: str
    metric: str
    target_value: float
    alert_threshold: float
    unit: str


@dataclass
class Incident:
    """Инцидент системы"""
    id: str
    component: str  # 'frontend', 'backend', 'websocket'
    severity: IncidentSeverity
    status: IncidentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: float = 0.0
    description: str = ''
    root_cause: str = ''
    impact: str = ''  # 'users', 'data', 'performance'
    is_scheduled: bool = False  # Плановое обслуживание

    def get_duration(self) -> float:
        """Рассчитывает длительность инцидента в минутах"""
        if self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 60
        return (datetime.utcnow() - self.start_time).total_seconds() / 60


class SLACalculator:
    """
    Калькулятор SLA метрик

    Основывается на SLA_DEFINITIONS.md:
    - Целевой uptime: 99.9% (43.2 минуты простоя/месяц)
    - Измеряемые компоненты: Frontend, Backend API, WebSocket
    - Исключения: Плановое обслуживание, outages третьих сторон
    """

    # SLA уровни из SLA_DEFINITIONS.md
    UPTIME_TIERS = [
        UptimeTier('Excellent', 99.9, 100.0, 43.2, 0),
        UptimeTier('Good', 99.0, 99.89, 432, 10),
        UptimeTier('Acceptable', 95.0, 98.99, 2160, 50),
        UptimeTier('Poor', 0.0, 94.99, 43200, 100),
    ]

    # Целевые показатели SLA из SLA_DEFINITIONS.md
    SLA_TARGETS = [
        # Availability
        SLATarget('Monthly Availability', 'availability', 99.9, 99.89, '%'),
        SLATarget('API Response Time', 'api_response_time', 150, 200, 'ms'),
        SLATarget('p95 Response Time', 'p95_response_time', 1000, 1500, 'ms'),
        SLATarget('Frontend Page Load', 'frontend_page_load', 3000, 4000, 'ms'),
        SLATarget('WebSocket Latency', 'websocket_latency', 100, 200, 'ms'),
        SLATarget('Cache Hit Rate', 'cache_hit_rate', 85, 75, '%'),
    ]

    # Response times для разных компонентов
    RESPONSE_TIME_SLA = {
        'frontend': {'target': 3000, 'alert': 4000},  # ms
        'backend': {'target': 150, 'alert': 200},  # ms
        'websocket': {'target': 100, 'alert': 200},  # ms
    }

    # Пороги severity для различных компонентов
    SEVERITY_THRESHOLDS = {
        'P1_CRITICAL': {
            'duration_minutes': 0,  # Любое время вниз = P1
            'affected_users': 'all',  # Все пользователи
            'components_down': 1,  # Хотя бы один критичный компонент
        },
        'P2_HIGH': {
            'duration_minutes': 0,
            'affected_users': 'multiple',
            'components_down': 0,
        },
        'P3_MEDIUM': {
            'duration_minutes': 0,
            'affected_users': 'few',
            'components_down': 0,
        },
        'P4_LOW': {
            'duration_minutes': 0,
            'affected_users': 'single',
            'components_down': 0,
        },
    }

    def __init__(self):
        """Инициализирует SLA калькулятор"""
        self.incidents: List[Incident] = []

    def add_incident(self,
                     incident_id: str,
                     component: str,
                     severity: IncidentSeverity,
                     start_time: datetime,
                     description: str = '',
                     is_scheduled: bool = False) -> Incident:
        """
        Добавляет новый инцидент

        Args:
            incident_id: Уникальный ID инцидента
            component: Компонент ('frontend', 'backend', 'websocket')
            severity: Уровень серьезности (P1-P4)
            start_time: Время начала инцидента
            description: Описание инцидента
            is_scheduled: Является ли это плановым обслуживанием

        Returns:
            Incident объект
        """
        incident = Incident(
            id=incident_id,
            component=component,
            severity=severity,
            status=IncidentStatus.OPEN,
            start_time=start_time,
            description=description,
            is_scheduled=is_scheduled,
        )
        self.incidents.append(incident)
        logger.info(f"Incident created: {incident_id} ({severity.value})")
        return incident

    def close_incident(self,
                      incident_id: str,
                      end_time: datetime,
                      root_cause: str = '',
                      resolution: str = '') -> Optional[Incident]:
        """
        Закрывает инцидент

        Args:
            incident_id: ID инцидента
            end_time: Время завершения
            root_cause: Причина инцидента
            resolution: Описание разрешения

        Returns:
            Обновленный Incident объект или None если не найден
        """
        incident = next(
            (i for i in self.incidents if i.id == incident_id),
            None
        )

        if not incident:
            logger.warning(f"Incident not found: {incident_id}")
            return None

        incident.end_time = end_time
        incident.duration_minutes = incident.get_duration()
        incident.root_cause = root_cause
        incident.impact = resolution
        incident.status = IncidentStatus.CLOSED

        logger.info(
            f"Incident closed: {incident_id} "
            f"(duration: {incident.duration_minutes:.2f} min)"
        )

        return incident

    def calculate_uptime_percentage(self,
                                   start_date: datetime,
                                   end_date: datetime,
                                   downtime_minutes: float,
                                   exclude_scheduled: bool = True) -> float:
        """
        Рассчитывает процент доступности (uptime) за период

        Args:
            start_date: Начало периода
            end_date: Конец периода
            downtime_minutes: Общее время простоя в минутах
            exclude_scheduled: Исключить плановое обслуживание из расчета

        Returns:
            Процент uptime (0-100)
        """
        # Рассчитываем общее время в периоде (в минутах)
        total_minutes = (end_date - start_date).total_seconds() / 60

        # Если нужно, исключаем плановое обслуживание
        if exclude_scheduled:
            scheduled_maintenance = sum(
                i.get_duration() for i in self.incidents
                if i.is_scheduled and
                start_date <= i.start_time <= end_date
            )
            total_minutes -= scheduled_maintenance

        # Рассчитываем uptime
        uptime = ((total_minutes - downtime_minutes) / total_minutes) * 100
        return round(max(0, min(100, uptime)), 4)

    def calculate_monthly_sla(self, year: int, month: int) -> Dict:
        """
        Рассчитывает SLA метрики за месяц

        Args:
            year: Год
            month: Месяц (1-12)

        Returns:
            Dict с SLA метриками месяца
        """
        # Определяем границы месяца
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Находим инциденты в этом месяце
        month_incidents = [
            i for i in self.incidents
            if start_date <= i.start_time < end_date and not i.is_scheduled
        ]

        # Рассчитываем общее время простоя
        total_downtime = sum(
            i.get_duration() for i in month_incidents
            if i.status == IncidentStatus.CLOSED
        )

        # Рассчитываем uptime %
        uptime_percent = self.calculate_uptime_percentage(
            start_date, end_date, total_downtime
        )

        # Находим соответствующий уровень
        tier = self._get_tier(uptime_percent)

        # Рассчитываем допустимое время простоя
        total_minutes = (end_date - start_date).total_seconds() / 60
        max_allowed_downtime = total_minutes * (1 - 99.9 / 100)

        # Определяем статус SLA
        sla_status = 'met' if uptime_percent >= 99.9 else 'missed'

        return {
            'year': year,
            'month': month,
            'period': f"{start_date.strftime('%Y-%m')}",
            'uptime_percent': uptime_percent,
            'uptime_tier': tier.name,
            'service_credit': tier.service_credit,
            'total_downtime_minutes': round(total_downtime, 2),
            'max_allowed_downtime_minutes': round(max_allowed_downtime, 2),
            'status': sla_status,
            'incidents_count': len(month_incidents),
            'by_severity': self._count_incidents_by_severity(month_incidents),
        }

    def calculate_quarterly_sla(self, year: int, quarter: int) -> Dict:
        """
        Рассчитывает SLA за квартал

        Args:
            year: Год
            quarter: Квартал (1-4)

        Returns:
            Dict с SLA метриками квартала
        """
        months = [quarter * 3 - 2, quarter * 3 - 1, quarter * 3]
        monthly_data = []

        total_downtime = 0
        total_minutes = 0

        for month in months:
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            month_incidents = [
                i for i in self.incidents
                if start_date <= i.start_time < end_date and not i.is_scheduled
            ]

            month_downtime = sum(
                i.get_duration() for i in month_incidents
                if i.status == IncidentStatus.CLOSED
            )

            total_downtime += month_downtime
            total_minutes += (end_date - start_date).total_seconds() / 60
            monthly_data.append(self.calculate_monthly_sla(year, month))

        uptime_percent = self.calculate_uptime_percentage(
            datetime(year, months[0], 1),
            datetime(year, months[-1], 1) + timedelta(days=31),
            total_downtime
        )

        tier = self._get_tier(uptime_percent)

        return {
            'year': year,
            'quarter': quarter,
            'period': f"Q{quarter} {year}",
            'uptime_percent': uptime_percent,
            'uptime_tier': tier.name,
            'service_credit': tier.service_credit,
            'total_downtime_minutes': round(total_downtime, 2),
            'max_allowed_downtime_minutes': round(
                total_minutes * (1 - 99.9 / 100), 2
            ),
            'status': 'met' if uptime_percent >= 99.9 else 'missed',
            'monthly_breakdown': monthly_data,
        }

    def _get_tier(self, uptime_percent: float) -> UptimeTier:
        """
        Определяет уровень uptime по проценту

        Args:
            uptime_percent: Процент uptime

        Returns:
            UptimeTier с соответствующим уровнем
        """
        for tier in self.UPTIME_TIERS:
            if tier.min_uptime <= uptime_percent <= tier.max_uptime:
                return tier
        return self.UPTIME_TIERS[-1]  # Poor уровень по умолчанию

    def _count_incidents_by_severity(self,
                                     incidents: List[Incident]) -> Dict[str, int]:
        """
        Подсчитывает инциденты по severity

        Args:
            incidents: Список инцидентов

        Returns:
            Dict с количеством инцидентов по каждому уровню
        """
        counts = {
            'P1_CRITICAL': 0,
            'P2_HIGH': 0,
            'P3_MEDIUM': 0,
            'P4_LOW': 0,
        }

        for incident in incidents:
            if incident.severity == IncidentSeverity.P1_CRITICAL:
                counts['P1_CRITICAL'] += 1
            elif incident.severity == IncidentSeverity.P2_HIGH:
                counts['P2_HIGH'] += 1
            elif incident.severity == IncidentSeverity.P3_MEDIUM:
                counts['P3_MEDIUM'] += 1
            elif incident.severity == IncidentSeverity.P4_LOW:
                counts['P4_LOW'] += 1

        return counts

    def get_incident_response_time(self,
                                  severity: IncidentSeverity) -> int:
        """
        Получает целевое время отклика на инцидент по severity

        Args:
            severity: Уровень серьезности

        Returns:
            Целевое время отклика в минутах
        """
        response_times = {
            IncidentSeverity.P1_CRITICAL: 15,   # 15 минут
            IncidentSeverity.P2_HIGH: 60,       # 1 час
            IncidentSeverity.P3_MEDIUM: 240,    # 4 часа
            IncidentSeverity.P4_LOW: 1440,      # 1 день
        }
        return response_times.get(severity, 1440)

    def check_sla_breach(self,
                         uptime_percent: float,
                         alert_threshold: float = 99.89) -> Tuple[bool, Dict]:
        """
        Проверяет нарушение SLA и генерирует алерт

        Args:
            uptime_percent: Текущий процент uptime
            alert_threshold: Пороговое значение для алерта

        Returns:
            Tuple[is_breached, alert_data]
        """
        is_breached = uptime_percent < alert_threshold

        alert_data = {
            'breached': is_breached,
            'uptime_percent': uptime_percent,
            'target': 99.9,
            'threshold': alert_threshold,
            'difference': uptime_percent - alert_threshold,
            'tier': self._get_tier(uptime_percent).name,
            'service_credit': self._get_tier(uptime_percent).service_credit,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if is_breached:
            logger.warning(
                f"SLA breach alert: uptime {uptime_percent}% < {alert_threshold}% "
                f"(tier: {alert_data['tier']})"
            )

        return is_breached, alert_data

    def export_incidents(self,
                        days: int = 90,
                        component: Optional[str] = None) -> List[Dict]:
        """
        Экспортирует инциденты за последние N дней

        Args:
            days: Количество дней
            component: Фильтр по компоненту (опционально)

        Returns:
            List[Dict] с информацией об инцидентах
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        incidents = [
            i for i in self.incidents
            if i.start_time >= cutoff_date and
            (component is None or i.component == component)
        ]

        return [
            {
                'id': i.id,
                'component': i.component,
                'severity': i.severity.value,
                'status': i.status.value,
                'start_time': i.start_time.isoformat(),
                'end_time': i.end_time.isoformat() if i.end_time else None,
                'duration_minutes': round(i.get_duration(), 2),
                'description': i.description,
                'root_cause': i.root_cause,
                'is_scheduled': i.is_scheduled,
            }
            for i in incidents
        ]


if __name__ == '__main__':
    # Пример использования
    calc = SLACalculator()

    # Добавляем примеры инцидентов
    incident1 = calc.add_incident(
        'INC-001',
        'backend',
        IncidentSeverity.P1_CRITICAL,
        datetime.utcnow() - timedelta(hours=2),
        'Database connection pool exhausted'
    )

    calc.close_incident(
        'INC-001',
        datetime.utcnow() - timedelta(hours=1, minutes=45),
        'Query optimization applied'
    )

    # Рассчитываем SLA за текущий месяц
    today = datetime.utcnow()
    monthly_sla = calc.calculate_monthly_sla(today.year, today.month)

    print("Monthly SLA Report:")
    print(json.dumps(monthly_sla, indent=2, default=str))
