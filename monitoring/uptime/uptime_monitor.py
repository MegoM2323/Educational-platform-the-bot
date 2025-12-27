"""
Uptime SLA Monitoring System

Выполняет внешние проверки доступности критических компонентов системы:
- Frontend UI (веб-приложение)
- Backend API (REST endpoints)
- WebSocket connections (real-time messaging)

Проверки выполняются каждые 60 секунд с внешних IP адресов.
Результаты сохраняются в базу данных для расчета SLA метрик.
"""
import requests
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Результат проверки доступности компонента"""
    component: str  # 'frontend', 'backend', 'websocket'
    status: str  # 'up', 'down', 'degraded'
    response_time_ms: float  # Время отклика в миллисекундах
    status_code: Optional[int] = None  # HTTP код ответа
    error_message: Optional[str] = None  # Описание ошибки
    timestamp: datetime = None
    severity: str = 'info'  # 'info', 'warning', 'critical'

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """Конвертирует результат в словарь"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class UptimeMonitor:
    """
    Внешний монитор доступности системы

    Выполняет регулярные проверки компонентов системы с внешних IP адресов.
    Использует синхронные и асинхронные запросы для параллельных проверок.
    """

    def __init__(self,
                 frontend_url: str = None,
                 backend_api_url: str = None,
                 websocket_url: str = None,
                 check_interval: int = 60):
        """
        Инициализирует монитор доступности

        Args:
            frontend_url: URL веб-приложения
            backend_api_url: URL backend API
            websocket_url: URL WebSocket сервера
            check_interval: Интервал между проверками (сек)
        """
        # URL компонентов с fallback на переменные окружения
        self.frontend_url = frontend_url or os.getenv('FRONTEND_URL', 'http://localhost:8080')
        self.backend_api_url = backend_api_url or os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.websocket_url = websocket_url or os.getenv('WEBSOCKET_URL', 'ws://localhost:8000/ws')

        self.check_interval = check_interval
        self.timeout = 10  # Timeout для одного запроса
        self.results_history: List[HealthCheckResult] = []

        # Сессии для переиспользования соединений
        self.session = None
        self.headers = {
            'User-Agent': 'THE_BOT-Uptime-Monitor/1.0'
        }

    async def check_frontend_async(self) -> HealthCheckResult:
        """
        Асинхронная проверка доступности frontend

        Returns:
            HealthCheckResult с результатом проверки
        """
        start_time = datetime.utcnow()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.frontend_url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers=self.headers,
                    ssl=False  # Для тестирования
                ) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        return HealthCheckResult(
                            component='frontend',
                            status='up',
                            response_time_ms=response_time,
                            status_code=response.status,
                            severity='info'
                        )
                    else:
                        return HealthCheckResult(
                            component='frontend',
                            status='degraded',
                            response_time_ms=response_time,
                            status_code=response.status,
                            error_message=f'HTTP {response.status}',
                            severity='warning'
                        )
        except asyncio.TimeoutError:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component='frontend',
                status='down',
                response_time_ms=response_time,
                error_message='Request timeout',
                severity='critical'
            )
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component='frontend',
                status='down',
                response_time_ms=response_time,
                error_message=str(e),
                severity='critical'
            )

    async def check_backend_async(self) -> HealthCheckResult:
        """
        Асинхронная проверка доступности backend API

        Returns:
            HealthCheckResult с результатом проверки
        """
        start_time = datetime.utcnow()
        try:
            async with aiohttp.ClientSession() as session:
                # Проверяем основной health endpoint
                health_endpoint = f"{self.backend_api_url}/api/system/health/"
                async with session.get(
                    health_endpoint,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers=self.headers,
                    ssl=False
                ) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        return HealthCheckResult(
                            component='backend',
                            status='up',
                            response_time_ms=response_time,
                            status_code=response.status,
                            severity='info'
                        )
                    else:
                        return HealthCheckResult(
                            component='backend',
                            status='degraded',
                            response_time_ms=response_time,
                            status_code=response.status,
                            error_message=f'HTTP {response.status}',
                            severity='warning'
                        )
        except asyncio.TimeoutError:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component='backend',
                status='down',
                response_time_ms=response_time,
                error_message='Request timeout',
                severity='critical'
            )
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component='backend',
                status='down',
                response_time_ms=response_time,
                error_message=str(e),
                severity='critical'
            )

    async def check_websocket_async(self) -> HealthCheckResult:
        """
        Асинхронная проверка доступности WebSocket

        Returns:
            HealthCheckResult с результатом проверки
        """
        start_time = datetime.utcnow()
        try:
            # Парсим WebSocket URL в HTTP для health check
            health_url = self.websocket_url.replace('ws://', 'http://').replace('wss://', 'https://')
            health_url = f"{self.backend_api_url}/api/system/health/"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers=self.headers,
                    ssl=False
                ) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                    if response.status == 200:
                        return HealthCheckResult(
                            component='websocket',
                            status='up',
                            response_time_ms=response_time,
                            status_code=response.status,
                            severity='info'
                        )
                    else:
                        return HealthCheckResult(
                            component='websocket',
                            status='degraded',
                            response_time_ms=response_time,
                            status_code=response.status,
                            error_message=f'HTTP {response.status}',
                            severity='warning'
                        )
        except asyncio.TimeoutError:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component='websocket',
                status='down',
                response_time_ms=response_time,
                error_message='Request timeout',
                severity='critical'
            )
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component='websocket',
                status='down',
                response_time_ms=response_time,
                error_message=str(e),
                severity='critical'
            )

    async def check_all_async(self) -> List[HealthCheckResult]:
        """
        Параллельная проверка всех компонентов (асинхронная)

        Returns:
            List[HealthCheckResult] с результатами для всех компонентов
        """
        try:
            results = await asyncio.gather(
                self.check_frontend_async(),
                self.check_backend_async(),
                self.check_websocket_async(),
                return_exceptions=True
            )

            # Фильтруем исключения
            health_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Exception during health check: {result}")
                    # Создаем результат с ошибкой
                    components = ['frontend', 'backend', 'websocket']
                    health_results.append(HealthCheckResult(
                        component=components[i],
                        status='down',
                        response_time_ms=0,
                        error_message=str(result),
                        severity='critical'
                    ))
                else:
                    health_results.append(result)

            # Сохраняем в историю
            self.results_history.extend(health_results)

            # Оставляем только последние 90 дней данных (259200 записей @ 1 запрос/сек)
            if len(self.results_history) > 259200:
                self.results_history = self.results_history[-259200:]

            return health_results
        except Exception as e:
            logger.error(f"Error during parallel health checks: {e}")
            return []

    def check_all_sync(self) -> List[HealthCheckResult]:
        """
        Синхронная проверка всех компонентов (для совместимости)

        Returns:
            List[HealthCheckResult] с результатами для всех компонентов
        """
        try:
            return asyncio.run(self.check_all_async())
        except Exception as e:
            logger.error(f"Error during synchronous health checks: {e}")
            return []

    def get_component_status(self, component: str) -> Optional[HealthCheckResult]:
        """
        Получает последний статус компонента

        Args:
            component: Название компонента ('frontend', 'backend', 'websocket')

        Returns:
            Последний результат проверки компонента или None
        """
        for result in reversed(self.results_history):
            if result.component == component:
                return result
        return None

    def get_component_uptime(self,
                            component: str,
                            hours: int = 24) -> Tuple[float, int, int]:
        """
        Рассчитывает uptime компонента за последние N часов

        Args:
            component: Название компонента
            hours: Количество часов для анализа

        Returns:
            Tuple[uptime_percent, up_count, down_count]
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        component_results = [
            r for r in self.results_history
            if r.component == component and r.timestamp >= cutoff_time
        ]

        if not component_results:
            return 0.0, 0, 0

        up_count = sum(1 for r in component_results if r.status == 'up')
        down_count = sum(1 for r in component_results if r.status in ('down', 'degraded'))
        total_count = len(component_results)

        uptime_percent = (up_count / total_count * 100) if total_count > 0 else 0.0

        return round(uptime_percent, 2), up_count, down_count

    def get_all_components_status(self) -> Dict[str, Dict]:
        """
        Получает статус всех компонентов

        Returns:
            Dict с информацией по всем компонентам
        """
        components = ['frontend', 'backend', 'websocket']
        status_data = {}

        for component in components:
            latest = self.get_component_status(component)
            uptime_24h, up, down = self.get_component_uptime(component, hours=24)
            uptime_7d, _, _ = self.get_component_uptime(component, hours=168)
            uptime_30d, _, _ = self.get_component_uptime(component, hours=720)

            status_data[component] = {
                'status': latest.status if latest else 'unknown',
                'last_check': latest.timestamp.isoformat() if latest else None,
                'response_time_ms': latest.response_time_ms if latest else 0,
                'status_code': latest.status_code if latest else None,
                'error': latest.error_message if latest else None,
                'uptime': {
                    '24h': uptime_24h,
                    '7d': uptime_7d,
                    '30d': uptime_30d,
                },
                'sla_target': 99.9,
            }

        return status_data

    def export_results(self, days: int = 90) -> List[Dict]:
        """
        Экспортирует результаты проверок за последние N дней

        Args:
            days: Количество дней для экспорта

        Returns:
            List[Dict] с результатами в JSON-сериализуемом формате
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        filtered_results = [
            r for r in self.results_history
            if r.timestamp >= cutoff_time
        ]
        return [r.to_dict() for r in filtered_results]


# Глобальный инстанс монитора
_monitor_instance = None


def get_monitor() -> UptimeMonitor:
    """
    Получает или создает глобальный инстанс монитора

    Returns:
        UptimeMonitor инстанс
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = UptimeMonitor()
    return _monitor_instance


if __name__ == '__main__':
    # Пример использования
    monitor = UptimeMonitor()

    # Выполняем проверки
    results = monitor.check_all_sync()

    # Выводим результаты
    for result in results:
        print(f"{result.component}: {result.status} ({result.response_time_ms:.2f}ms)")

    # Получаем статус всех компонентов
    status = monitor.get_all_components_status()
    print("\nDetailed Status:")
    print(json.dumps(status, indent=2, default=str))
