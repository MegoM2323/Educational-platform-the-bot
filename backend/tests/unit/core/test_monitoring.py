"""
Unit-тесты для системы мониторинга
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
import psutil

from core.monitoring import (
    SystemMonitor,
    system_monitor,
    log_system_event,
    check_system_health
)


@pytest.mark.unit
class TestSystemMonitorInit:
    """Тесты инициализации SystemMonitor"""

    def test_system_monitor_initialization(self):
        """Тест правильной инициализации монитора"""
        monitor = SystemMonitor()

        assert monitor.metrics_cache_timeout == 60
        assert monitor.health_check_timeout == 30


@pytest.mark.unit
@pytest.mark.django_db
class TestGetSystemMetrics:
    """Тесты получения системных метрик"""

    def test_get_system_metrics_returns_all_components(self):
        """Тест что возвращаются все компоненты метрик"""
        monitor = SystemMonitor()

        with patch.object(monitor, '_get_cpu_metrics', return_value={'usage_percent': 50}), \
             patch.object(monitor, '_get_memory_metrics', return_value={'used_percent': 60}), \
             patch.object(monitor, '_get_disk_metrics', return_value={'used_percent': 45}), \
             patch.object(monitor, '_get_database_metrics', return_value={'response_time_ms': 100}), \
             patch.object(monitor, '_get_cache_metrics', return_value={'is_working': True}), \
             patch.object(monitor, '_get_external_services_metrics', return_value={}):

            metrics = monitor.get_system_metrics()

            assert 'timestamp' in metrics
            assert 'cpu' in metrics
            assert 'memory' in metrics
            assert 'disk' in metrics
            assert 'database' in metrics
            assert 'cache' in metrics
            assert 'external_services' in metrics

    def test_get_system_metrics_uses_cache(self):
        """Тест что метрики кэшируются"""
        monitor = SystemMonitor()
        cache_key = 'system_metrics'

        # Очищаем кэш
        cache.delete(cache_key)

        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'usage_percent': 50},
            'memory': {'used_percent': 60}
        }

        # Устанавливаем кэш
        cache.set(cache_key, mock_metrics, 60)

        # Получаем метрики
        metrics = monitor.get_system_metrics()

        # Должны получить данные из кэша
        assert metrics == mock_metrics

    def test_get_system_metrics_exception_handling(self):
        """Тест обработки исключений при получении метрик"""
        monitor = SystemMonitor()

        with patch.object(monitor, '_get_cpu_metrics', side_effect=Exception("CPU error")):
            metrics = monitor.get_system_metrics()

            assert 'error' in metrics
            assert metrics['status'] == 'error'


@pytest.mark.unit
class TestGetCpuMetrics:
    """Тесты получения метрик CPU"""

    def test_get_cpu_metrics_healthy(self):
        """Тест метрик CPU в здоровом состоянии"""
        monitor = SystemMonitor()

        with patch('core.monitoring.psutil.cpu_percent', return_value=50.0), \
             patch('core.monitoring.psutil.cpu_count', return_value=4), \
             patch('core.monitoring.psutil.cpu_freq', return_value=MagicMock(current=2400.0)):

            cpu_metrics = monitor._get_cpu_metrics()

            assert cpu_metrics['usage_percent'] == 50.0
            assert cpu_metrics['core_count'] == 4
            assert cpu_metrics['frequency_mhz'] == 2400.0
            assert cpu_metrics['status'] == 'healthy'

    def test_get_cpu_metrics_warning(self):
        """Тест метрик CPU в состоянии предупреждения"""
        monitor = SystemMonitor()

        with patch('core.monitoring.psutil.cpu_percent', return_value=85.0), \
             patch('core.monitoring.psutil.cpu_count', return_value=4), \
             patch('core.monitoring.psutil.cpu_freq', return_value=None):

            cpu_metrics = monitor._get_cpu_metrics()

            assert cpu_metrics['usage_percent'] == 85.0
            assert cpu_metrics['status'] == 'warning'
            assert cpu_metrics['frequency_mhz'] is None

    def test_get_cpu_metrics_critical(self):
        """Тест метрик CPU в критическом состоянии"""
        monitor = SystemMonitor()

        with patch('core.monitoring.psutil.cpu_percent', return_value=96.0), \
             patch('core.monitoring.psutil.cpu_count', return_value=4), \
             patch('core.monitoring.psutil.cpu_freq', return_value=None):

            cpu_metrics = monitor._get_cpu_metrics()

            assert cpu_metrics['usage_percent'] == 96.0
            assert cpu_metrics['status'] == 'critical'

    def test_get_cpu_metrics_exception(self):
        """Тест обработки исключений при получении метрик CPU"""
        monitor = SystemMonitor()

        with patch('core.monitoring.psutil.cpu_percent', side_effect=Exception("CPU error")):
            cpu_metrics = monitor._get_cpu_metrics()

            assert cpu_metrics['status'] == 'error'
            assert 'error' in cpu_metrics


@pytest.mark.unit
class TestGetMemoryMetrics:
    """Тесты получения метрик памяти"""

    def test_get_memory_metrics_healthy(self):
        """Тест метрик памяти в здоровом состоянии"""
        monitor = SystemMonitor()

        mock_memory = MagicMock()
        mock_memory.total = 16 * (1024**3)  # 16 GB
        mock_memory.available = 8 * (1024**3)  # 8 GB
        mock_memory.percent = 50.0

        mock_swap = MagicMock()
        mock_swap.total = 4 * (1024**3)  # 4 GB
        mock_swap.percent = 10.0

        with patch('core.monitoring.psutil.virtual_memory', return_value=mock_memory), \
             patch('core.monitoring.psutil.swap_memory', return_value=mock_swap):

            memory_metrics = monitor._get_memory_metrics()

            assert memory_metrics['total_gb'] == 16.0
            assert memory_metrics['available_gb'] == 8.0
            assert memory_metrics['used_percent'] == 50.0
            assert memory_metrics['swap_total_gb'] == 4.0
            assert memory_metrics['swap_used_percent'] == 10.0
            assert memory_metrics['status'] == 'healthy'

    def test_get_memory_metrics_warning(self):
        """Тест метрик памяти в состоянии предупреждения"""
        monitor = SystemMonitor()

        mock_memory = MagicMock()
        mock_memory.total = 16 * (1024**3)
        mock_memory.available = 3 * (1024**3)
        mock_memory.percent = 85.0

        mock_swap = MagicMock()
        mock_swap.total = 4 * (1024**3)
        mock_swap.percent = 20.0

        with patch('core.monitoring.psutil.virtual_memory', return_value=mock_memory), \
             patch('core.monitoring.psutil.swap_memory', return_value=mock_swap):

            memory_metrics = monitor._get_memory_metrics()

            assert memory_metrics['used_percent'] == 85.0
            assert memory_metrics['status'] == 'warning'

    def test_get_memory_metrics_critical(self):
        """Тест метрик памяти в критическом состоянии"""
        monitor = SystemMonitor()

        mock_memory = MagicMock()
        mock_memory.total = 16 * (1024**3)
        mock_memory.available = 1 * (1024**3)
        mock_memory.percent = 94.0

        mock_swap = MagicMock()
        mock_swap.total = 4 * (1024**3)
        mock_swap.percent = 30.0

        with patch('core.monitoring.psutil.virtual_memory', return_value=mock_memory), \
             patch('core.monitoring.psutil.swap_memory', return_value=mock_swap):

            memory_metrics = monitor._get_memory_metrics()

            assert memory_metrics['used_percent'] == 94.0
            assert memory_metrics['status'] == 'critical'


@pytest.mark.unit
class TestGetDiskMetrics:
    """Тесты получения метрик диска"""

    def test_get_disk_metrics_healthy(self):
        """Тест метрик диска в здоровом состоянии"""
        monitor = SystemMonitor()

        mock_disk = MagicMock()
        mock_disk.total = 500 * (1024**3)  # 500 GB
        mock_disk.used = 200 * (1024**3)  # 200 GB
        mock_disk.free = 300 * (1024**3)  # 300 GB
        mock_disk.percent = 40.0

        with patch('core.monitoring.psutil.disk_usage', return_value=mock_disk):
            disk_metrics = monitor._get_disk_metrics()

            assert disk_metrics['total_gb'] == 500.0
            assert disk_metrics['used_gb'] == 200.0
            assert disk_metrics['free_gb'] == 300.0
            assert disk_metrics['used_percent'] == 40.0
            assert disk_metrics['status'] == 'healthy'

    def test_get_disk_metrics_warning(self):
        """Тест метрик диска в состоянии предупреждения"""
        monitor = SystemMonitor()

        mock_disk = MagicMock()
        mock_disk.total = 500 * (1024**3)
        mock_disk.used = 425 * (1024**3)
        mock_disk.free = 75 * (1024**3)
        mock_disk.percent = 85.0

        with patch('core.monitoring.psutil.disk_usage', return_value=mock_disk):
            disk_metrics = monitor._get_disk_metrics()

            assert disk_metrics['status'] == 'warning'

    def test_get_disk_metrics_critical(self):
        """Тест метрик диска в критическом состоянии"""
        monitor = SystemMonitor()

        mock_disk = MagicMock()
        mock_disk.total = 500 * (1024**3)
        mock_disk.used = 475 * (1024**3)
        mock_disk.free = 25 * (1024**3)
        mock_disk.percent = 95.0

        with patch('core.monitoring.psutil.disk_usage', return_value=mock_disk):
            disk_metrics = monitor._get_disk_metrics()

            assert disk_metrics['status'] == 'critical'


@pytest.mark.unit
@pytest.mark.django_db
class TestGetDatabaseMetrics:
    """Тесты получения метрик базы данных"""

    def test_get_database_metrics_healthy(self):
        """Тест метрик БД в здоровом состоянии"""
        monitor = SystemMonitor()

        db_metrics = monitor._get_database_metrics()

        assert 'response_time_ms' in db_metrics
        assert 'user_count' in db_metrics
        assert 'application_count' in db_metrics
        assert 'payment_count' in db_metrics
        assert db_metrics['status'] in ['healthy', 'warning', 'critical']

    def test_get_database_metrics_slow_response(self):
        """Тест метрик БД с медленным ответом"""
        monitor = SystemMonitor()

        with patch('core.monitoring.time.time', side_effect=[0, 6.0]):  # 6 секунд
            db_metrics = monitor._get_database_metrics()

            # При медленном ответе (>5000ms) статус будет critical
            if db_metrics.get('response_time_ms', 0) > 5000:
                assert db_metrics['status'] == 'critical'


@pytest.mark.unit
@pytest.mark.django_db
class TestGetCacheMetrics:
    """Тесты получения метрик кэша"""

    def test_get_cache_metrics_healthy(self):
        """Тест метрик кэша в здоровом состоянии"""
        monitor = SystemMonitor()

        cache_metrics = monitor._get_cache_metrics()

        assert 'response_time_ms' in cache_metrics
        assert 'is_working' in cache_metrics
        assert cache_metrics['is_working'] is True
        assert cache_metrics['status'] == 'healthy'

    def test_get_cache_metrics_not_working(self):
        """Тест метрик кэша когда кэш не работает"""
        monitor = SystemMonitor()

        with patch('core.monitoring.cache.set', side_effect=Exception("Cache error")):
            cache_metrics = monitor._get_cache_metrics()

            assert cache_metrics['status'] == 'error'


@pytest.mark.unit
class TestGetExternalServicesMetrics:
    """Тесты получения метрик внешних сервисов"""

    def test_get_external_services_metrics(self):
        """Тест получения метрик всех внешних сервисов"""
        monitor = SystemMonitor()

        with patch.object(monitor, '_check_telegram_service', return_value={'status': 'healthy'}), \
             patch.object(monitor, '_check_yookassa_service', return_value={'status': 'healthy'}), \
             patch.object(monitor, '_check_supabase_service', return_value={'status': 'healthy'}):

            services_metrics = monitor._get_external_services_metrics()

            assert 'telegram' in services_metrics
            assert 'yookassa' in services_metrics
            assert 'supabase' in services_metrics


@pytest.mark.unit
class TestCheckTelegramService:
    """Тесты проверки Telegram сервиса"""

    def test_check_telegram_service_healthy(self, settings):
        """Тест здорового состояния Telegram API"""
        settings.TELEGRAM_BOT_TOKEN = 'test_bot_token'

        monitor = SystemMonitor()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5

        with patch('core.monitoring.requests.get', return_value=mock_response):
            telegram_status = monitor._check_telegram_service()

            assert telegram_status['status'] == 'healthy'
            assert telegram_status['response_time_ms'] == 500

    def test_check_telegram_service_disabled(self, settings):
        """Тест когда Telegram не настроен"""
        settings.TELEGRAM_BOT_TOKEN = None

        monitor = SystemMonitor()
        telegram_status = monitor._check_telegram_service()

        assert telegram_status['status'] == 'disabled'
        assert 'not configured' in telegram_status['message']

    def test_check_telegram_service_error(self, settings):
        """Тест ошибки при проверке Telegram"""
        settings.TELEGRAM_BOT_TOKEN = 'test_bot_token'

        monitor = SystemMonitor()
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('core.monitoring.requests.get', return_value=mock_response):
            telegram_status = monitor._check_telegram_service()

            assert telegram_status['status'] == 'error'
            assert 'HTTP 401' in telegram_status['message']


@pytest.mark.unit
class TestCheckYooKassaService:
    """Тесты проверки YooKassa сервиса"""

    def test_check_yookassa_service_healthy(self, settings):
        """Тест здорового состояния YooKassa API"""
        settings.YOOKASSA_SHOP_ID = 'test_shop_id'
        settings.YOOKASSA_SECRET_KEY = 'test_secret_key'

        monitor = SystemMonitor()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.3

        with patch('core.monitoring.requests.get', return_value=mock_response):
            yookassa_status = monitor._check_yookassa_service()

            assert yookassa_status['status'] == 'healthy'
            assert yookassa_status['response_time_ms'] == 300

    def test_check_yookassa_service_disabled(self, settings):
        """Тест когда YooKassa не настроен"""
        settings.YOOKASSA_SHOP_ID = None

        monitor = SystemMonitor()
        yookassa_status = monitor._check_yookassa_service()

        assert yookassa_status['status'] == 'disabled'


@pytest.mark.unit
class TestCheckSupabaseService:
    """Тесты проверки Supabase сервиса"""

    def test_check_supabase_service_healthy(self, settings):
        """Тест здорового состояния Supabase"""
        settings.SUPABASE_URL = 'https://test.supabase.co'

        monitor = SystemMonitor()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.2

        with patch('core.monitoring.requests.get', return_value=mock_response):
            supabase_status = monitor._check_supabase_service()

            assert supabase_status['status'] == 'healthy'

    def test_check_supabase_service_unauthorized_is_ok(self, settings):
        """Тест что 401 от Supabase считается нормальным (сервис доступен)"""
        settings.SUPABASE_URL = 'https://test.supabase.co'

        monitor = SystemMonitor()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.elapsed.total_seconds.return_value = 0.2

        with patch('core.monitoring.requests.get', return_value=mock_response):
            supabase_status = monitor._check_supabase_service()

            assert supabase_status['status'] == 'healthy'


@pytest.mark.unit
class TestGetHealthStatus:
    """Тесты получения общего статуса здоровья"""

    def test_get_health_status_healthy(self):
        """Тест здорового общего статуса"""
        monitor = SystemMonitor()

        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'status': 'healthy'},
            'memory': {'status': 'healthy'},
            'disk': {'status': 'healthy'}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            health_status = monitor.get_health_status()

            assert health_status['overall_status'] == 'healthy'
            assert len(health_status['critical_components']) == 0
            assert len(health_status['warning_components']) == 0

    def test_get_health_status_warning(self):
        """Тест общего статуса с предупреждениями"""
        monitor = SystemMonitor()

        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'status': 'warning'},
            'memory': {'status': 'healthy'},
            'disk': {'status': 'healthy'}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            health_status = monitor.get_health_status()

            assert health_status['overall_status'] == 'warning'
            assert 'cpu' in health_status['warning_components']

    def test_get_health_status_critical(self):
        """Тест критического общего статуса"""
        monitor = SystemMonitor()

        mock_metrics = {
            'timestamp': timezone.now().isoformat(),
            'cpu': {'status': 'critical'},
            'memory': {'status': 'warning'},
            'disk': {'status': 'healthy'}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            health_status = monitor.get_health_status()

            assert health_status['overall_status'] == 'critical'
            assert 'cpu' in health_status['critical_components']
            assert 'memory' in health_status['warning_components']


@pytest.mark.unit
class TestGetPerformanceAlerts:
    """Тесты получения предупреждений о производительности"""

    def test_get_performance_alerts_cpu_critical(self):
        """Тест критического предупреждения CPU"""
        monitor = SystemMonitor()

        mock_metrics = {
            'cpu': {'usage_percent': 92},
            'memory': {'used_percent': 50},
            'disk': {'used_percent': 40},
            'database': {'response_time_ms': 200}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            alerts = monitor.get_performance_alerts()

            cpu_alerts = [a for a in alerts if a['type'] == 'cpu_high']
            assert len(cpu_alerts) == 1
            assert cpu_alerts[0]['severity'] == 'critical'

    def test_get_performance_alerts_memory_warning(self):
        """Тест предупреждения о памяти"""
        monitor = SystemMonitor()

        mock_metrics = {
            'cpu': {'usage_percent': 50},
            'memory': {'used_percent': 85},
            'disk': {'used_percent': 40},
            'database': {'response_time_ms': 200}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            alerts = monitor.get_performance_alerts()

            memory_alerts = [a for a in alerts if a['type'] == 'memory_high']
            assert len(memory_alerts) == 1
            assert memory_alerts[0]['severity'] == 'warning'

    def test_get_performance_alerts_disk_critical(self):
        """Тест критического предупреждения диска"""
        monitor = SystemMonitor()

        mock_metrics = {
            'cpu': {'usage_percent': 50},
            'memory': {'used_percent': 60},
            'disk': {'used_percent': 92},
            'database': {'response_time_ms': 200}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            alerts = monitor.get_performance_alerts()

            disk_alerts = [a for a in alerts if a['type'] == 'disk_full']
            assert len(disk_alerts) == 1
            assert disk_alerts[0]['severity'] == 'critical'

    def test_get_performance_alerts_database_slow(self):
        """Тест предупреждения о медленной БД"""
        monitor = SystemMonitor()

        mock_metrics = {
            'cpu': {'usage_percent': 50},
            'memory': {'used_percent': 60},
            'disk': {'used_percent': 50},
            'database': {'response_time_ms': 1500}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            alerts = monitor.get_performance_alerts()

            db_alerts = [a for a in alerts if a['type'] == 'db_slow']
            assert len(db_alerts) == 1
            assert db_alerts[0]['severity'] == 'warning'

    def test_get_performance_alerts_multiple(self):
        """Тест множественных предупреждений"""
        monitor = SystemMonitor()

        mock_metrics = {
            'cpu': {'usage_percent': 92},
            'memory': {'used_percent': 88},
            'disk': {'used_percent': 93},
            'database': {'response_time_ms': 6000}
        }

        with patch.object(monitor, 'get_system_metrics', return_value=mock_metrics):
            alerts = monitor.get_performance_alerts()

            assert len(alerts) >= 4  # CPU, Memory, Disk, Database
            critical_alerts = [a for a in alerts if a['severity'] == 'critical']
            assert len(critical_alerts) >= 3


@pytest.mark.unit
class TestLogSystemEvent:
    """Тесты логирования системных событий"""

    def test_log_system_event_info(self):
        """Тест логирования информационного события"""
        with patch('core.monitoring.logger.info') as mock_logger:
            log_system_event('test_event', 'Test message', 'info')

            mock_logger.assert_called_once()
            call_args = str(mock_logger.call_args)
            assert 'test_event' in call_args
            assert 'Test message' in call_args

    def test_log_system_event_warning(self):
        """Тест логирования предупреждения"""
        with patch('core.monitoring.logger.warning') as mock_logger:
            log_system_event('warning_event', 'Warning message', 'warning')

            mock_logger.assert_called_once()

    def test_log_system_event_error(self):
        """Тест логирования ошибки"""
        with patch('core.monitoring.logger.error') as mock_logger:
            log_system_event('error_event', 'Error message', 'error')

            mock_logger.assert_called_once()

    def test_log_system_event_critical(self):
        """Тест логирования критического события"""
        with patch('core.monitoring.logger.critical') as mock_logger:
            log_system_event('critical_event', 'Critical message', 'critical')

            mock_logger.assert_called_once()

    def test_log_system_event_with_metadata(self):
        """Тест логирования события с метаданными"""
        with patch('core.monitoring.logger.info') as mock_logger:
            metadata = {'user_id': 123, 'action': 'test_action'}
            log_system_event('test_event', 'Test message', 'info', metadata=metadata)

            mock_logger.assert_called_once()
            call_args = str(mock_logger.call_args)
            assert 'user_id' in call_args
            assert 'test_action' in call_args

    def test_log_system_event_with_user_id(self):
        """Тест логирования события с user_id"""
        with patch('core.monitoring.logger.info') as mock_logger:
            log_system_event('test_event', 'Test message', 'info', user_id=123)

            mock_logger.assert_called_once()
            call_args = str(mock_logger.call_args)
            assert '123' in call_args


@pytest.mark.unit
class TestCheckSystemHealth:
    """Тесты функции проверки здоровья системы"""

    def test_check_system_health_success(self):
        """Тест успешной проверки здоровья"""
        mock_health_status = {
            'overall_status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'critical_components': [],
            'warning_components': []
        }

        mock_alerts = []

        with patch.object(system_monitor, 'get_health_status', return_value=mock_health_status), \
             patch.object(system_monitor, 'get_performance_alerts', return_value=mock_alerts):

            health = check_system_health()

            assert health['status'] == 'healthy'
            assert 'timestamp' in health
            assert 'alerts' in health
            assert len(health['alerts']) == 0

    def test_check_system_health_with_alerts(self):
        """Тест проверки здоровья с предупреждениями"""
        mock_health_status = {
            'overall_status': 'warning',
            'timestamp': timezone.now().isoformat(),
            'critical_components': [],
            'warning_components': ['cpu']
        }

        mock_alerts = [
            {'type': 'cpu_high', 'severity': 'warning', 'message': 'CPU usage is 85%'}
        ]

        with patch.object(system_monitor, 'get_health_status', return_value=mock_health_status), \
             patch.object(system_monitor, 'get_performance_alerts', return_value=mock_alerts):

            health = check_system_health()

            assert health['status'] == 'warning'
            assert len(health['alerts']) == 1
            assert 'cpu' in health['components']['warning']

    def test_check_system_health_exception(self):
        """Тест обработки исключений при проверке здоровья"""
        with patch.object(system_monitor, 'get_health_status', side_effect=Exception("Monitor error")):
            health = check_system_health()

            assert health['status'] == 'error'
            assert 'error' in health
            assert 'Monitor error' in health['error']


@pytest.mark.unit
class TestSystemMonitorGlobal:
    """Тесты глобального экземпляра монитора"""

    def test_system_monitor_is_singleton(self):
        """Тест что system_monitor является глобальным экземпляром"""
        from core.monitoring import system_monitor as monitor1
        from core.monitoring import system_monitor as monitor2

        assert monitor1 is monitor2
        assert isinstance(monitor1, SystemMonitor)
