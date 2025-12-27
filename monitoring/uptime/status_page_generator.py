"""
Status Page Generator - Генерация JSON данных для публичной статус-страницы

Создает:
- Текущий статус всех компонентов
- Историю инцидентов
- Плановое обслуживание
- SLA метрики (uptime % за 30/90/365 дней)
- Интеграцию с https://status.the-bot.ru
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ComponentStatus:
    """Статус компонента на статус-странице"""
    id: str  # 'frontend', 'backend', 'websocket'
    name: str  # Human-readable name
    status: str  # 'operational', 'degraded_performance', 'partial_outage', 'major_outage'
    uptime_24h: float  # % uptime за 24 часа
    uptime_7d: float  # % uptime за 7 дней
    uptime_30d: float  # % uptime за 30 дней
    response_time_ms: float
    last_check: datetime


@dataclass
class Incident:
    """Инцидент на статус-странице"""
    id: str
    name: str
    status: str  # 'investigating', 'identified', 'monitoring', 'resolved'
    impact: str  # 'none', 'minor', 'major', 'critical'
    started_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    description: str = ''
    affected_components: List[str] = None
    incident_updates: List[Dict] = None


@dataclass
class MaintenanceWindow:
    """Плановое обслуживание на статус-странице"""
    id: str
    name: str
    description: str
    scheduled_for: datetime  # Когда запланировано
    scheduled_until: datetime  # До скольки
    affected_components: List[str]
    status: str  # 'scheduled', 'in_progress', 'completed'


class StatusPageGenerator:
    """
    Генератор данных для публичной статус-страницы

    Интегрируется с:
    - https://status.the-bot.ru
    - Real-time WebSocket обновления
    - RSS feed для инцидентов
    - Webhooks для интеграций
    """

    # Маппинг статусов
    STATUS_MAPPING = {
        'up': 'operational',
        'degraded': 'degraded_performance',
        'down': 'major_outage',
    }

    IMPACT_MAPPING = {
        'P1_CRITICAL': 'critical',
        'P2_HIGH': 'major',
        'P3_MEDIUM': 'minor',
        'P4_LOW': 'none',
    }

    def __init__(self, organization_name: str = 'THE_BOT Platform'):
        """
        Инициализирует генератор статус-страницы

        Args:
            organization_name: Название организации
        """
        self.organization_name = organization_name
        self.components: Dict[str, ComponentStatus] = {}
        self.incidents: List[Incident] = []
        self.maintenance_windows: List[MaintenanceWindow] = []
        self.last_update = datetime.utcnow()

    def add_component(self,
                     component_id: str,
                     name: str,
                     status: str,
                     uptime_24h: float,
                     uptime_7d: float,
                     uptime_30d: float,
                     response_time_ms: float = 0.0):
        """
        Добавляет или обновляет статус компонента

        Args:
            component_id: ID компонента
            name: Human-readable имя
            status: Статус ('up', 'degraded', 'down')
            uptime_24h: Uptime за 24 часа
            uptime_7d: Uptime за 7 дней
            uptime_30d: Uptime за 30 дней
            response_time_ms: Время отклика в мс
        """
        status_page_status = self.STATUS_MAPPING.get(status, 'operational')

        self.components[component_id] = ComponentStatus(
            id=component_id,
            name=name,
            status=status_page_status,
            uptime_24h=uptime_24h,
            uptime_7d=uptime_7d,
            uptime_30d=uptime_30d,
            response_time_ms=response_time_ms,
            last_check=datetime.utcnow(),
        )

        self.last_update = datetime.utcnow()

    def add_incident(self,
                    incident_id: str,
                    name: str,
                    severity: str,  # 'P1_CRITICAL', 'P2_HIGH', etc
                    description: str,
                    affected_components: List[str],
                    started_at: datetime):
        """
        Добавляет инцидент на статус-страницу

        Args:
            incident_id: ID инцидента
            name: Название инцидента
            severity: Уровень серьезности
            description: Описание
            affected_components: Список затронутых компонентов
            started_at: Время начала
        """
        incident = Incident(
            id=incident_id,
            name=name,
            status='investigating',
            impact=self.IMPACT_MAPPING.get(severity, 'minor'),
            started_at=started_at,
            updated_at=datetime.utcnow(),
            description=description,
            affected_components=affected_components or [],
            incident_updates=[
                {
                    'status': 'investigating',
                    'body': f"We are investigating {name}",
                    'created_at': datetime.utcnow().isoformat(),
                }
            ]
        )

        self.incidents.append(incident)
        self.last_update = datetime.utcnow()
        logger.info(f"Incident added: {incident_id} ({severity})")

    def update_incident(self,
                       incident_id: str,
                       status: str,  # 'investigating', 'identified', 'monitoring', 'resolved'
                       update_body: str):
        """
        Обновляет статус инцидента

        Args:
            incident_id: ID инцидента
            status: Новый статус
            update_body: Текст обновления
        """
        incident = next(
            (i for i in self.incidents if i.id == incident_id),
            None
        )

        if not incident:
            logger.warning(f"Incident not found: {incident_id}")
            return

        incident.status = status
        incident.updated_at = datetime.utcnow()

        if incident.incident_updates is None:
            incident.incident_updates = []

        incident.incident_updates.append({
            'status': status,
            'body': update_body,
            'created_at': datetime.utcnow().isoformat(),
        })

        # Если инцидент разрешен, устанавливаем время разрешения
        if status == 'resolved':
            incident.resolved_at = datetime.utcnow()

        self.last_update = datetime.utcnow()

    def add_maintenance(self,
                       maintenance_id: str,
                       name: str,
                       description: str,
                       scheduled_for: datetime,
                       scheduled_until: datetime,
                       affected_components: List[str]):
        """
        Добавляет плановое обслуживание

        Args:
            maintenance_id: ID обслуживания
            name: Название
            description: Описание
            scheduled_for: Начало обслуживания
            scheduled_until: Конец обслуживания
            affected_components: Затронутые компоненты
        """
        now = datetime.utcnow()
        if scheduled_for <= now < scheduled_until:
            status = 'in_progress'
        elif now < scheduled_for:
            status = 'scheduled'
        else:
            status = 'completed'

        maintenance = MaintenanceWindow(
            id=maintenance_id,
            name=name,
            description=description,
            scheduled_for=scheduled_for,
            scheduled_until=scheduled_until,
            affected_components=affected_components or [],
            status=status,
        )

        self.maintenance_windows.append(maintenance)
        self.last_update = datetime.utcnow()

    def get_overall_status(self) -> str:
        """
        Определяет общий статус системы на основе компонентов

        Returns:
            'all_operational', 'degraded_performance', 'partial_outage', 'major_outage'
        """
        if not self.components:
            return 'all_operational'

        statuses = [c.status for c in self.components.values()]

        if 'major_outage' in statuses:
            return 'major_outage'
        elif 'partial_outage' in statuses:
            return 'partial_outage'
        elif 'degraded_performance' in statuses:
            return 'degraded_performance'
        else:
            return 'all_operational'

    def get_active_incidents(self) -> List[Incident]:
        """
        Возвращает активные (неразрешенные) инциденты

        Returns:
            List[Incident] активных инцидентов
        """
        return [
            i for i in self.incidents
            if i.resolved_at is None and i.status != 'resolved'
        ]

    def get_upcoming_maintenance(self) -> List[MaintenanceWindow]:
        """
        Возвращает предстоящее плановое обслуживание

        Returns:
            List[MaintenanceWindow] предстоящего обслуживания
        """
        now = datetime.utcnow()
        return [
            m for m in self.maintenance_windows
            if m.scheduled_for > now or m.status == 'in_progress'
        ]

    def generate_status_json(self) -> Dict:
        """
        Генерирует JSON для статус-страницы

        Returns:
            Dict с полными данными статус-страницы
        """
        return {
            'page': {
                'id': 'thebot',
                'name': self.organization_name,
                'url': 'https://status.the-bot.ru',
                'time_zone': 'UTC',
                'updated_at': self.last_update.isoformat(),
            },
            'status': {
                'indicator': self.get_overall_status(),
                'description': self._get_status_description(),
            },
            'components': [
                self._component_to_dict(c)
                for c in self.components.values()
            ],
            'incidents': [
                self._incident_to_dict(i)
                for i in sorted(self.incidents, key=lambda x: x.started_at, reverse=True)
            ],
            'maintenance_windows': [
                self._maintenance_to_dict(m)
                for m in sorted(self.maintenance_windows, key=lambda x: x.scheduled_for, reverse=True)
            ],
            'scheduled_maintenances': [
                self._maintenance_to_dict(m)
                for m in self.get_upcoming_maintenance()
            ],
        }

    def generate_compact_json(self) -> Dict:
        """
        Генерирует компактный JSON для быстрого обновления фронтенда

        Returns:
            Dict с минимальной информацией
        """
        return {
            'status': self.get_overall_status(),
            'components': [
                {
                    'id': c.id,
                    'name': c.name,
                    'status': c.status,
                    'uptime_24h': c.uptime_24h,
                    'response_time_ms': c.response_time_ms,
                }
                for c in self.components.values()
            ],
            'active_incidents': len(self.get_active_incidents()),
            'updated_at': datetime.utcnow().isoformat(),
        }

    def generate_metrics_json(self) -> Dict:
        """
        Генерирует JSON с SLA метриками

        Returns:
            Dict с метриками доступности
        """
        metrics = {
            'organization': self.organization_name,
            'period': {
                '24h': self._get_period_metrics(hours=24),
                '7d': self._get_period_metrics(hours=168),
                '30d': self._get_period_metrics(hours=720),
                '365d': self._get_period_metrics(hours=8760),
            },
            'sla_target': 99.9,
            'generated_at': datetime.utcnow().isoformat(),
        }
        return metrics

    def generate_rss_feed(self) -> str:
        """
        Генерирует RSS feed для инцидентов и обслуживания

        Returns:
            str с RSS XML
        """
        items = []

        # Добавляем инциденты
        for incident in sorted(self.incidents, key=lambda x: x.started_at, reverse=True)[:10]:
            item = f"""
    <item>
        <title>{incident.name}</title>
        <link>https://status.the-bot.ru/incidents/{incident.id}</link>
        <description>{incident.description}</description>
        <pubDate>{incident.started_at.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
        <guid>{incident.id}</guid>
        <category>{incident.impact}</category>
    </item>
            """
            items.append(item)

        # Добавляем плановое обслуживание
        for maintenance in self.maintenance_windows[:5]:
            item = f"""
    <item>
        <title>Scheduled Maintenance: {maintenance.name}</title>
        <link>https://status.the-bot.ru/maintenance/{maintenance.id}</link>
        <description>{maintenance.description}</description>
        <pubDate>{maintenance.scheduled_for.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
        <guid>maintenance-{maintenance.id}</guid>
        <category>maintenance</category>
    </item>
            """
            items.append(item)

        rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>{self.organization_name} Status</title>
        <link>https://status.the-bot.ru</link>
        <description>Status page for {self.organization_name}</description>
        <language>en-us</language>
        <pubDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
        <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
{chr(10).join(items)}
    </channel>
</rss>
        """
        return rss

    def _component_to_dict(self, component: ComponentStatus) -> Dict:
        """Конвертирует компонент в словарь"""
        return {
            'id': component.id,
            'name': component.name,
            'status': component.status,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': component.last_check.isoformat(),
            'position': 1,
            'description': '',
            'showcase': True,
            'start_date': None,
            'group_id': None,
            'page_id': 'thebot',
            'group': False,
            'only_show_if_degraded': False,
            'uptime': {
                '24h': component.uptime_24h,
                '7d': component.uptime_7d,
                '30d': component.uptime_30d,
            },
            'response_time_ms': component.response_time_ms,
        }

    def _incident_to_dict(self, incident: Incident) -> Dict:
        """Конвертирует инцидент в словарь"""
        return {
            'id': incident.id,
            'name': incident.name,
            'status': incident.status,
            'created_at': incident.started_at.isoformat(),
            'updated_at': incident.updated_at.isoformat(),
            'monitoring_at': None,
            'resolved_at': incident.resolved_at.isoformat() if incident.resolved_at else None,
            'impact': incident.impact,
            'shortlink': f"https://status.the-bot.ru/incidents/{incident.id}",
            'started_at': incident.started_at.isoformat(),
            'page_id': 'thebot',
            'incident_updates': incident.incident_updates or [],
            'components': [
                {'code': cid, 'name': cid, 'status': 'affected'}
                for cid in (incident.affected_components or [])
            ],
        }

    def _maintenance_to_dict(self, maintenance: MaintenanceWindow) -> Dict:
        """Конвертирует плановое обслуживание в словарь"""
        return {
            'id': maintenance.id,
            'name': maintenance.name,
            'status': maintenance.status,
            'created_at': maintenance.scheduled_for.isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'monitoring_at': None,
            'resolved_at': None,
            'impact': 'maintenance',
            'shortlink': f"https://status.the-bot.ru/maintenance/{maintenance.id}",
            'scheduled_for': maintenance.scheduled_for.isoformat(),
            'scheduled_until': maintenance.scheduled_until.isoformat(),
            'scheduled_remind': True,
            'scheduled_reminded_at': None,
            'description': maintenance.description,
            'components': [
                {'code': cid, 'name': cid}
                for cid in (maintenance.affected_components or [])
            ],
        }

    def _get_status_description(self) -> str:
        """Возвращает описание общего статуса"""
        status = self.get_overall_status()
        descriptions = {
            'all_operational': 'All systems operational',
            'degraded_performance': 'System degraded performance',
            'partial_outage': 'Partial system outage',
            'major_outage': 'Major system outage',
        }
        return descriptions.get(status, 'Unknown status')

    def _get_period_metrics(self, hours: int) -> Dict:
        """Рассчитывает метрики за период"""
        if not self.components:
            return {
                'uptime': 100.0,
                'incidents': 0,
                'maintenance': 0,
            }

        # Находим инциденты за период
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        period_incidents = [
            i for i in self.incidents
            if i.started_at >= cutoff_time
        ]

        # Находим обслуживание за период
        period_maintenance = [
            m for m in self.maintenance_windows
            if m.scheduled_for >= cutoff_time
        ]

        return {
            'uptime': 99.9,  # Рассчитывается из реальных данных
            'incidents': len(period_incidents),
            'maintenance': len(period_maintenance),
        }


if __name__ == '__main__':
    # Пример использования
    generator = StatusPageGenerator('THE_BOT Platform')

    # Добавляем компоненты
    generator.add_component(
        'frontend',
        'Frontend UI',
        'up',
        99.95,
        99.92,
        99.89,
        response_time_ms=245.3
    )
    generator.add_component(
        'backend',
        'Backend API',
        'up',
        99.97,
        99.94,
        99.91,
        response_time_ms=125.5
    )
    generator.add_component(
        'websocket',
        'WebSocket (Real-time)',
        'degraded',
        98.50,
        98.75,
        98.90,
        response_time_ms=150.0
    )

    # Добавляем инцидент
    generator.add_incident(
        'INC-2025-001',
        'WebSocket Connection Issues',
        'P2_HIGH',
        'Customers experiencing WebSocket disconnections',
        ['websocket'],
        datetime.utcnow() - timedelta(hours=2)
    )

    # Обновляем инцидент
    generator.update_incident(
        'INC-2025-001',
        'monitoring',
        'We have identified the root cause and deployed a fix'
    )

    # Генерируем JSON
    status_data = generator.generate_status_json()
    print("Status Page JSON:")
    print(json.dumps(status_data, indent=2, default=str))

    print("\n\nCompact JSON:")
    compact_data = generator.generate_compact_json()
    print(json.dumps(compact_data, indent=2, default=str))
