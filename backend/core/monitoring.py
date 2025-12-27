"""
Система мониторинга состояния платформы с real-time метриками
"""
import logging
import time
import json
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from threading import Lock
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from django.db import connections
from django.db.utils import OperationalError
import psutil
import requests
from core.json_utils import safe_json_response

logger = logging.getLogger(__name__)


# Decorators for performance tracking
def timing_decorator(func: Callable) -> Callable:
    """
    Декоратор для отслеживания времени выполнения функции

    Отслеживает время выполнения в миллисекундах и сохраняет в метрики
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.time() - start_time) * 1000
            # Для отслеживания в логе (может быть сохранено в метрики)
            logger.debug(f"Function {func.__name__} took {duration_ms:.2f}ms")
    return wrapper


class MetricsCollector:
    """
    Сборщик метрик системы в реальном времени

    Собирает метрики каждую минуту и сохраняет в Redis
    для 7 дней истории (10080 точек данных)
    """

    # Alert thresholds
    ALERT_THRESHOLDS = {
        'cpu': 80,
        'memory': 85,
        'disk': 90,
        'db_latency': 1000,  # ms
        'api_response_time': 2000,  # ms
    }

    # Health status colors
    HEALTH_STATUS = {
        'green': 'healthy',  # All metrics < 70%
        'yellow': 'warning',  # Any metric 70-85%
        'red': 'critical',  # Any metric > 85%
    }

    def __init__(self):
        self.metrics_cache_timeout = 60  # 1 minute
        self.health_check_timeout = 30  # 30 seconds
        self.data_retention_days = 7
        self.data_points_per_day = 1440  # 1 per minute
        self.max_data_points = self.data_retention_days * self.data_points_per_day
        self._lock = Lock()
        self._request_metrics = defaultdict(lambda: deque(maxlen=1440))  # 24h
        self._response_times = deque(maxlen=10000)
        self._error_counts = defaultdict(int)

    @timing_decorator
    def collect_metrics(self) -> Dict[str, Any]:
        """
        Собирает все метрики системы в одну точку данных

        Returns:
            Словарь с полными метриками
        """
        timestamp = timezone.now()
        timestamp_str = timestamp.isoformat()

        try:
            metrics = {
                'timestamp': timestamp_str,
                'cpu': self._get_cpu_metrics(),
                'memory': self._get_memory_metrics(),
                'disk': self._get_disk_metrics(),
                'network': self._get_network_metrics(),
                'database': self._get_database_metrics(),
                'redis': self._get_redis_metrics(),
                'websocket': self._get_websocket_metrics(),
                'requests': self._get_request_metrics(),
                'errors': self._get_error_metrics(),
                'latency': self._get_latency_metrics(),
            }

            # Store in Redis with key: monitoring:metrics:{timestamp}
            self._store_metrics(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            return {
                'timestamp': timestamp_str,
                'error': str(e),
                'status': 'error'
            }

    def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Сохраняет метрики в Redis с TTL 7 дней

        Args:
            metrics: Словарь метрик
        """
        try:
            timestamp = metrics.get('timestamp', '')
            # Extract only timestamp for key
            ts_key = timestamp.split('T')[0] + '_' + timestamp.split('T')[1][:5]

            cache_key = f'monitoring:metrics:{ts_key}'
            cache.set(cache_key, json.dumps(metrics), timeout=7*24*3600)  # 7 days TTL

            # Store in sorted set for easy retrieval of recent metrics
            cache.set('monitoring:latest', json.dumps(metrics), timeout=3600)

        except Exception as e:
            logger.warning(f"Could not store metrics: {e}")

    @timing_decorator
    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """Получает метрики CPU (current, 5-min, 15-min avg)"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            load_avg = psutil.getloadavg()
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()

            return {
                'current_percent': round(cpu_percent, 2),
                'avg_5min_percent': round(load_avg[0] / cpu_count * 100, 2) if cpu_count else 0,
                'avg_15min_percent': round(load_avg[2] / cpu_count * 100, 2) if cpu_count else 0,
                'core_count': cpu_count,
                'frequency_mhz': round(cpu_freq.current, 2) if cpu_freq else None,
                'threshold': self.ALERT_THRESHOLDS['cpu'],
                'status': self._get_status(cpu_percent, 70, 85)
            }
        except Exception as e:
            logger.warning(f"Error getting CPU metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @timing_decorator
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Получает метрики памяти (used, available, percentage)"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            return {
                'total_gb': round(memory.total / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': round(memory.percent, 2),
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_percent': round(swap.percent, 2),
                'threshold': self.ALERT_THRESHOLDS['memory'],
                'status': self._get_status(memory.percent, 70, 85)
            }
        except Exception as e:
            logger.warning(f"Error getting memory metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @timing_decorator
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """Получает метрики всех дисковых партиций"""
        try:
            partitions = []

            # Get metrics for root partition
            disk_usage = psutil.disk_usage('/')
            partitions.append({
                'partition': '/',
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'used_percent': round(disk_usage.percent, 2),
                'status': self._get_status(disk_usage.percent, 70, 85)
            })

            # Try to get other partitions if available
            try:
                for part in psutil.disk_partitions():
                    if part.mountpoint != '/':
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            partitions.append({
                                'partition': part.mountpoint,
                                'total_gb': round(usage.total / (1024**3), 2),
                                'used_gb': round(usage.used / (1024**3), 2),
                                'free_gb': round(usage.free / (1024**3), 2),
                                'used_percent': round(usage.percent, 2),
                                'status': self._get_status(usage.percent, 70, 85)
                            })
                        except (OSError, PermissionError):
                            continue
            except Exception:
                pass

            return {
                'partitions': partitions,
                'threshold': self.ALERT_THRESHOLDS['disk'],
                'status': self._aggregate_status([p['status'] for p in partitions])
            }
        except Exception as e:
            logger.warning(f"Error getting disk metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @timing_decorator
    def _get_network_metrics(self) -> Dict[str, Any]:
        """Получает метрики сетевого ввода-вывода (in/out bytes/sec)"""
        try:
            net_io = psutil.net_io_counters()

            return {
                'bytes_in': net_io.bytes_recv,
                'bytes_out': net_io.bytes_sent,
                'packets_in': net_io.packets_recv,
                'packets_out': net_io.packets_sent,
                'errors_in': net_io.errin,
                'errors_out': net_io.errout,
                'dropped_in': net_io.dropin,
                'dropped_out': net_io.dropout,
                'status': 'healthy'
            }
        except Exception as e:
            logger.warning(f"Error getting network metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @timing_decorator
    def _get_database_metrics(self) -> Dict[str, Any]:
        """Получает метрики пула соединений с БД"""
        try:
            start_time = time.time()

            # Test database connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            response_time_ms = (time.time() - start_time) * 1000

            # Get connection pool status
            db_conn = connections['default']
            pool_size = getattr(db_conn.connection, 'pool_size', 'unknown')

            return {
                'response_time_ms': round(response_time_ms, 2),
                'status': 'healthy' if response_time_ms < 100 else
                         'warning' if response_time_ms < self.ALERT_THRESHOLDS['db_latency']
                         else 'critical',
                'connection_pool_size': pool_size,
                'threshold': self.ALERT_THRESHOLDS['db_latency'],
            }
        except OperationalError as e:
            logger.warning(f"Database connection error: {e}")
            return {'status': 'critical', 'error': str(e)}
        except Exception as e:
            logger.warning(f"Error getting database metrics: {e}")
            return {'status': 'error', 'error': str(e)}

    @timing_decorator
    def _get_redis_metrics(self) -> Dict[str, Any]:
        """Получает метрики соединения с Redis"""
        try:
            start_time = time.time()

            # Test cache/Redis connectivity
            test_key = f'monitoring_test_{int(time.time())}'
            cache.set(test_key, 'test', 10)
            test_value = cache.get(test_key)
            cache.delete(test_key)

            response_time_ms = (time.time() - start_time) * 1000
            is_working = test_value == 'test'

            return {
                'response_time_ms': round(response_time_ms, 2),
                'is_working': is_working,
                'status': 'healthy' if is_working else 'critical',
            }
        except Exception as e:
            logger.warning(f"Error getting Redis metrics: {e}")
            return {'status': 'critical', 'error': str(e)}

    @timing_decorator
    def _get_websocket_metrics(self) -> Dict[str, Any]:
        """Получает метрики активных WebSocket соединений"""
        try:
            # Try to get WebSocket metrics from cache or settings
            ws_count = cache.get('websocket_connections_count', 0)

            return {
                'active_connections': int(ws_count),
                'status': 'healthy',
            }
        except Exception as e:
            logger.warning(f"Error getting WebSocket metrics: {e}")
            return {'status': 'unknown', 'error': str(e)}

    @timing_decorator
    def _get_request_metrics(self) -> Dict[str, Any]:
        """Получает метрики запросов (per second, per minute)"""
        try:
            with self._lock:
                # Get request counts from cache or in-memory tracking
                requests_per_second = cache.get('api_requests_per_second', 0)
                requests_per_minute = cache.get('api_requests_per_minute', 0)

                return {
                    'per_second': int(requests_per_second),
                    'per_minute': int(requests_per_minute),
                    'status': 'healthy',
                }
        except Exception as e:
            logger.warning(f"Error getting request metrics: {e}")
            return {'status': 'unknown', 'error': str(e)}

    @timing_decorator
    def _get_error_metrics(self) -> Dict[str, Any]:
        """Получает метрики ошибок (4xx, 5xx)"""
        try:
            errors_4xx = cache.get('api_errors_4xx_count', 0)
            errors_5xx = cache.get('api_errors_5xx_count', 0)

            return {
                'errors_4xx': int(errors_4xx),
                'errors_5xx': int(errors_5xx),
                'error_rate_percent': round(
                    (int(errors_4xx) + int(errors_5xx)) /
                    max(cache.get('api_total_requests', 1), 1) * 100, 2
                ) if cache.get('api_total_requests', 0) > 0 else 0,
                'status': 'healthy' if int(errors_5xx) == 0 else
                         'warning' if int(errors_5xx) < 10 else 'critical',
            }
        except Exception as e:
            logger.warning(f"Error getting error metrics: {e}")
            return {'status': 'unknown', 'error': str(e)}

    @timing_decorator
    def _get_latency_metrics(self) -> Dict[str, Any]:
        """Получает метрики задержки API (p50, p95, p99)"""
        try:
            response_times = cache.get('api_response_times_list', [])

            if not response_times:
                return {
                    'p50_ms': 0,
                    'p95_ms': 0,
                    'p99_ms': 0,
                    'avg_ms': 0,
                    'status': 'healthy',
                }

            sorted_times = sorted(response_times)
            n = len(sorted_times)

            return {
                'p50_ms': round(sorted_times[int(n * 0.50)], 2) if n > 0 else 0,
                'p95_ms': round(sorted_times[int(n * 0.95)], 2) if n > 0 else 0,
                'p99_ms': round(sorted_times[int(n * 0.99)], 2) if n > 0 else 0,
                'avg_ms': round(sum(response_times) / len(response_times), 2) if response_times else 0,
                'status': 'healthy' if (sorted_times[int(n * 0.95)] if n > 0 else 0) < self.ALERT_THRESHOLDS['api_response_time'] else 'warning',
            }
        except Exception as e:
            logger.warning(f"Error getting latency metrics: {e}")
            return {'status': 'unknown', 'error': str(e)}

    @staticmethod
    def _get_status(value: float, yellow_threshold: float, red_threshold: float) -> str:
        """Определяет статус на основе пороговых значений"""
        if value >= red_threshold:
            return 'critical'
        elif value >= yellow_threshold:
            return 'warning'
        else:
            return 'healthy'

    @staticmethod
    def _aggregate_status(statuses: List[str]) -> str:
        """Агрегирует статусы нескольких компонентов"""
        if 'critical' in statuses:
            return 'critical'
        elif 'warning' in statuses:
            return 'warning'
        else:
            return 'healthy'


class AlertSystem:
    """
    Система оповещений для мониторинга

    Управляет активными алертами с пороговыми значениями и автоматическим
    сбросом при возврате в норму
    """

    def __init__(self):
        self._active_alerts = {}  # key: component, value: alert data
        self._alert_history = deque(maxlen=10000)  # History of all alerts
        self._lock = Lock()

    def check_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Проверяет метрики против пороговых значений и создаёт алерты

        Args:
            metrics: Словарь метрик от MetricsCollector

        Returns:
            Список активных алертов
        """
        alerts = []

        with self._lock:
            # Check CPU
            cpu_data = metrics.get('cpu', {})
            if cpu_data.get('status') == 'critical':
                self._create_alert(
                    'cpu', 'critical',
                    f"CPU usage is {cpu_data.get('current_percent')}%",
                    cpu_data, alerts
                )
            elif cpu_data.get('status') == 'warning':
                self._create_alert(
                    'cpu', 'warning',
                    f"CPU usage is {cpu_data.get('current_percent')}%",
                    cpu_data, alerts
                )
            else:
                self._clear_alert('cpu')

            # Check Memory
            memory_data = metrics.get('memory', {})
            if memory_data.get('status') == 'critical':
                self._create_alert(
                    'memory', 'critical',
                    f"Memory usage is {memory_data.get('used_percent')}%",
                    memory_data, alerts
                )
            elif memory_data.get('status') == 'warning':
                self._create_alert(
                    'memory', 'warning',
                    f"Memory usage is {memory_data.get('used_percent')}%",
                    memory_data, alerts
                )
            else:
                self._clear_alert('memory')

            # Check Disk
            disk_data = metrics.get('disk', {})
            if disk_data.get('status') == 'critical':
                partitions_info = ', '.join([p['partition'] for p in disk_data.get('partitions', [])])
                self._create_alert(
                    'disk', 'critical',
                    f"Disk usage critical on: {partitions_info}",
                    disk_data, alerts
                )
            elif disk_data.get('status') == 'warning':
                partitions_info = ', '.join([p['partition'] for p in disk_data.get('partitions', [])])
                self._create_alert(
                    'disk', 'warning',
                    f"Disk usage warning on: {partitions_info}",
                    disk_data, alerts
                )
            else:
                self._clear_alert('disk')

            # Check Database
            db_data = metrics.get('database', {})
            if db_data.get('status') == 'critical':
                self._create_alert(
                    'database', 'critical',
                    f"Database latency {db_data.get('response_time_ms')}ms",
                    db_data, alerts
                )
            elif db_data.get('status') == 'warning':
                self._create_alert(
                    'database', 'warning',
                    f"Database latency {db_data.get('response_time_ms')}ms",
                    db_data, alerts
                )
            else:
                self._clear_alert('database')

            # Check Redis
            redis_data = metrics.get('redis', {})
            if redis_data.get('status') == 'critical':
                self._create_alert(
                    'redis', 'critical',
                    "Redis connection failed",
                    redis_data, alerts
                )
            else:
                self._clear_alert('redis')

            # Check Error Rate
            errors_data = metrics.get('errors', {})
            if errors_data.get('status') == 'critical':
                self._create_alert(
                    'errors', 'critical',
                    f"High error rate: {errors_data.get('errors_5xx')} 5xx errors",
                    errors_data, alerts
                )
            elif errors_data.get('status') == 'warning':
                self._create_alert(
                    'errors', 'warning',
                    f"Error rate increasing: {errors_data.get('errors_5xx')} 5xx errors",
                    errors_data, alerts
                )
            else:
                self._clear_alert('errors')

        return alerts

    def _create_alert(self, component: str, severity: str, message: str,
                     data: Dict, alerts: List) -> None:
        """Создаёт или обновляет алерт"""
        now = timezone.now()
        alert = {
            'component': component,
            'severity': severity,
            'message': message,
            'timestamp': now.isoformat(),
            'duration_seconds': 0,
            'data': data
        }

        if component in self._active_alerts:
            # Update existing alert
            existing = self._active_alerts[component]
            start_time = datetime.fromisoformat(existing['timestamp'])
            duration = (now - start_time).total_seconds()
            alert['duration_seconds'] = int(duration)
        else:
            # Create new alert
            self._active_alerts[component] = alert
            self._alert_history.append(alert)

        alerts.append(alert)

    def _clear_alert(self, component: str) -> None:
        """Удаляет алерт при возврате в норму"""
        if component in self._active_alerts:
            cleared_alert = self._active_alerts.pop(component)
            cleared_alert['cleared_at'] = timezone.now().isoformat()
            self._alert_history.append(cleared_alert)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Возвращает список активных алертов"""
        with self._lock:
            return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Возвращает историю алертов"""
        with self._lock:
            return list(reversed(list(self._alert_history)))[:limit]

    def get_health_status(self, metrics: Dict[str, Any]) -> str:
        """
        Определяет общий статус системы на основе метрик

        Returns:
            'green', 'yellow', или 'red'
        """
        alerts = self.check_thresholds(metrics)

        if any(a['severity'] == 'critical' for a in alerts):
            return 'red'
        elif any(a['severity'] == 'warning' for a in alerts):
            return 'yellow'
        else:
            return 'green'


class SystemMonitor:
    """Монитор состояния системы (legacy support)"""

    def __init__(self):
        self.metrics_cache_timeout = 60  # 1 минута
        self.health_check_timeout = 30  # 30 секунд
        self.metrics_collector = MetricsCollector()
        self.alert_system = AlertSystem()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Получает метрики системы (использует MetricsCollector)

        Returns:
            Словарь с метриками системы
        """
        return self.metrics_collector.collect_metrics()

    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """Получает метрики CPU (legacy)"""
        return self.metrics_collector._get_cpu_metrics()

    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Получает метрики памяти (legacy)"""
        return self.metrics_collector._get_memory_metrics()

    def _get_disk_metrics(self) -> Dict[str, Any]:
        """Получает метрики диска (legacy)"""
        return self.metrics_collector._get_disk_metrics()

    def _get_database_metrics(self) -> Dict[str, Any]:
        """Получает метрики базы данных (legacy)"""
        return self.metrics_collector._get_database_metrics()

    def _get_cache_metrics(self) -> Dict[str, Any]:
        """Получает метрики кэша (legacy)"""
        return self.metrics_collector._get_redis_metrics()

    def _get_external_services_metrics(self) -> Dict[str, Any]:
        """Получает метрики внешних сервисов"""
        services = {}

        # Проверяем Telegram Bot API
        services['telegram'] = self._check_telegram_service()

        # Проверяем Юкассу API
        services['yookassa'] = self._check_yookassa_service()

        # Проверяем Supabase
        services['supabase'] = self._check_supabase_service()

        return services

    def _check_telegram_service(self) -> Dict[str, Any]:
        """Проверяет доступность Telegram Bot API"""
        try:
            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
            if not bot_token:
                return {'status': 'disabled', 'message': 'Bot token not configured'}

            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=self.health_check_timeout)

            if response.status_code == 200:
                return {'status': 'healthy', 'response_time_ms': response.elapsed.total_seconds() * 1000}
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _check_yookassa_service(self) -> Dict[str, Any]:
        """Проверяет доступность Юкассы API"""
        try:
            shop_id = getattr(settings, 'YOOKASSA_SHOP_ID', None)
            if not shop_id:
                return {'status': 'disabled', 'message': 'Shop ID not configured'}

            url = "https://api.yookassa.ru/v3/me"
            auth = (shop_id, getattr(settings, 'YOOKASSA_SECRET_KEY', ''))

            response = requests.get(url, auth=auth, timeout=self.health_check_timeout)

            if response.status_code == 200:
                return {'status': 'healthy', 'response_time_ms': response.elapsed.total_seconds() * 1000}
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _check_supabase_service(self) -> Dict[str, Any]:
        """Проверяет доступность Supabase"""
        try:
            supabase_url = getattr(settings, 'SUPABASE_URL', None)
            if not supabase_url:
                return {'status': 'disabled', 'message': 'Supabase URL not configured'}

            # Проверяем доступность Supabase через health endpoint
            health_url = f"{supabase_url.rstrip('/')}/rest/v1/"
            response = requests.get(health_url, timeout=self.health_check_timeout)

            if response.status_code in [200, 401]:  # 401 тоже нормально для неавторизованного запроса
                return {'status': 'healthy', 'response_time_ms': response.elapsed.total_seconds() * 1000}
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Получает общий статус здоровья системы
        
        Returns:
            Словарь с общим статусом системы
        """
        metrics = self.get_system_metrics()
        
        # Анализируем статусы компонентов
        critical_components = []
        warning_components = []
        
        for component, data in metrics.items():
            if isinstance(data, dict) and 'status' in data:
                if data['status'] == 'critical':
                    critical_components.append(component)
                elif data['status'] == 'warning':
                    warning_components.append(component)
        
        # Определяем общий статус
        if critical_components:
            overall_status = 'critical'
        elif warning_components:
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': metrics.get('timestamp'),
            'critical_components': critical_components,
            'warning_components': warning_components,
            'metrics': metrics
        }
    
    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """
        Получает предупреждения о производительности
        
        Returns:
            Список предупреждений
        """
        alerts = []
        metrics = self.get_system_metrics()
        
        # Проверяем CPU
        cpu_data = metrics.get('cpu', {})
        if cpu_data.get('usage_percent', 0) > 90:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'critical',
                'message': f"CPU usage is {cpu_data.get('usage_percent')}%",
                'component': 'cpu'
            })
        elif cpu_data.get('usage_percent', 0) > 80:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"CPU usage is {cpu_data.get('usage_percent')}%",
                'component': 'cpu'
            })
        
        # Проверяем память
        memory_data = metrics.get('memory', {})
        if memory_data.get('used_percent', 0) > 90:
            alerts.append({
                'type': 'memory_high',
                'severity': 'critical',
                'message': f"Memory usage is {memory_data.get('used_percent')}%",
                'component': 'memory'
            })
        elif memory_data.get('used_percent', 0) > 80:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"Memory usage is {memory_data.get('used_percent')}%",
                'component': 'memory'
            })
        
        # Проверяем диск
        disk_data = metrics.get('disk', {})
        if disk_data.get('used_percent', 0) > 90:
            alerts.append({
                'type': 'disk_full',
                'severity': 'critical',
                'message': f"Disk usage is {disk_data.get('used_percent')}%",
                'component': 'disk'
            })
        elif disk_data.get('used_percent', 0) > 80:
            alerts.append({
                'type': 'disk_full',
                'severity': 'warning',
                'message': f"Disk usage is {disk_data.get('used_percent')}%",
                'component': 'disk'
            })
        
        # Проверяем базу данных
        db_data = metrics.get('database', {})
        if db_data.get('response_time_ms', 0) > 5000:
            alerts.append({
                'type': 'db_slow',
                'severity': 'critical',
                'message': f"Database response time is {db_data.get('response_time_ms')}ms",
                'component': 'database'
            })
        elif db_data.get('response_time_ms', 0) > 1000:
            alerts.append({
                'type': 'db_slow',
                'severity': 'warning',
                'message': f"Database response time is {db_data.get('response_time_ms')}ms",
                'component': 'database'
            })
        
        return alerts


# Глобальный экземпляр монитора
system_monitor = SystemMonitor()


def log_system_event(event_type: str, 
                    message: str, 
                    severity: str = 'info',
                    user_id: Optional[int] = None,
                    metadata: Optional[Dict] = None):
    """
    Логирует системное событие
    
    Args:
        event_type: Тип события
        message: Сообщение
        severity: Уровень серьезности (info, warning, error, critical)
        user_id: ID пользователя
        metadata: Дополнительные метаданные
    """
    log_data = {
        'event_type': event_type,
        'message': message,
        'severity': severity,
        'user_id': user_id,
        'metadata': metadata or {},
        'timestamp': timezone.now().isoformat()
    }
    
    if severity == 'critical':
        logger.critical(f"System event: {log_data}")
    elif severity == 'error':
        logger.error(f"System event: {log_data}")
    elif severity == 'warning':
        logger.warning(f"System event: {log_data}")
    else:
        logger.info(f"System event: {log_data}")


def check_system_health() -> Dict[str, Any]:
    """
    Проверяет здоровье системы (для health check endpoint)
    
    Returns:
        Словарь с результатами проверки
    """
    try:
        health_status = system_monitor.get_health_status()
        alerts = system_monitor.get_performance_alerts()
        
        return {
            'status': health_status['overall_status'],
            'timestamp': health_status['timestamp'],
            'alerts': alerts,
            'components': {
                'critical': health_status['critical_components'],
                'warning': health_status['warning_components']
            }
        }
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return {
            'status': 'error',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }
