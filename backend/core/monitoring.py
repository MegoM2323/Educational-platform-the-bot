"""
Система мониторинга состояния платформы
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import psutil
import requests
from core.json_utils import safe_json_response

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Монитор состояния системы"""
    
    def __init__(self):
        self.metrics_cache_timeout = 60  # 1 минута
        self.health_check_timeout = 30  # 30 секунд
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Получает метрики системы
        
        Returns:
            Словарь с метриками системы
        """
        cache_key = 'system_metrics'
        cached_metrics = cache.get(cache_key)
        
        if cached_metrics:
            return cached_metrics
        
        try:
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'cpu': self._get_cpu_metrics(),
                'memory': self._get_memory_metrics(),
                'disk': self._get_disk_metrics(),
                'database': self._get_database_metrics(),
                'cache': self._get_cache_metrics(),
                'external_services': self._get_external_services_metrics()
            }
            
            # Кэшируем метрики
            cache.set(cache_key, metrics, self.metrics_cache_timeout)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                'timestamp': timezone.now().isoformat(),
                'error': str(e),
                'status': 'error'
            }
    
    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """Получает метрики CPU"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            return {
                'usage_percent': cpu_percent,
                'core_count': cpu_count,
                'frequency_mhz': cpu_freq.current if cpu_freq else None,
                'status': 'healthy' if cpu_percent < 80 else 'warning' if cpu_percent < 95 else 'critical'
            }
        except Exception as e:
            logger.warning(f"Error getting CPU metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Получает метрики памяти"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent,
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_percent': swap.percent,
                'status': 'healthy' if memory.percent < 80 else 'warning' if memory.percent < 95 else 'critical'
            }
        except Exception as e:
            logger.warning(f"Error getting memory metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """Получает метрики диска"""
        try:
            disk_usage = psutil.disk_usage('/')
            
            return {
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'used_percent': round((disk_usage.used / disk_usage.total) * 100, 2),
                'status': 'healthy' if disk_usage.percent < 80 else 'warning' if disk_usage.percent < 95 else 'critical'
            }
        except Exception as e:
            logger.warning(f"Error getting disk metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_database_metrics(self) -> Dict[str, Any]:
        """Получает метрики базы данных"""
        try:
            start_time = time.time()
            
            with connection.cursor() as cursor:
                # Проверяем соединение
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
                # Получаем количество записей в основных таблицах
                cursor.execute("SELECT COUNT(*) FROM accounts_user")
                user_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM applications_application")
                application_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM payments_payment")
                payment_count = cursor.fetchone()[0]
            
            response_time = (time.time() - start_time) * 1000  # в миллисекундах
            
            return {
                'response_time_ms': round(response_time, 2),
                'user_count': user_count,
                'application_count': application_count,
                'payment_count': payment_count,
                'status': 'healthy' if response_time < 1000 else 'warning' if response_time < 5000 else 'critical'
            }
        except Exception as e:
            logger.warning(f"Error getting database metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_cache_metrics(self) -> Dict[str, Any]:
        """Получает метрики кэша"""
        try:
            # Проверяем доступность кэша
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            start_time = time.time()
            cache.set(test_key, test_value, 10)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            response_time = (time.time() - start_time) * 1000
            
            is_working = cached_value == test_value
            
            return {
                'response_time_ms': round(response_time, 2),
                'is_working': is_working,
                'status': 'healthy' if is_working and response_time < 100 else 'error'
            }
        except Exception as e:
            logger.warning(f"Error getting cache metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
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
