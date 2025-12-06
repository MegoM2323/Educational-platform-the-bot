"""
Celery задачи для системы мониторинга и резервного копирования
"""
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .backup_utils import backup_manager, create_automatic_backup
from .monitoring import system_monitor, log_system_event
from .transaction_utils import log_critical_operation

logger = logging.getLogger(__name__)


@shared_task
def create_daily_backup():
    """
    Создает ежедневную резервную копию
    """
    try:
        logger.info("Starting daily backup creation")
        
        backup_info = create_automatic_backup()
        
        if backup_info:
            log_system_event(
                'daily_backup_created',
                f'Daily backup created successfully: {backup_info["id"]}',
                'info',
                metadata={'backup_id': backup_info['id']}
            )
            
            logger.info(f"Daily backup created successfully: {backup_info['id']}")
            return {
                'success': True,
                'backup_id': backup_info['id'],
                'message': 'Daily backup created successfully'
            }
        else:
            log_system_event(
                'daily_backup_failed',
                'Failed to create daily backup',
                'error'
            )
            
            logger.error("Failed to create daily backup")
            return {
                'success': False,
                'message': 'Failed to create daily backup'
            }
            
    except Exception as e:
        error_msg = f"Error creating daily backup: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        log_system_event(
            'daily_backup_error',
            error_msg,
            'error',
            metadata={'error': str(e)}
        )
        
        return {
            'success': False,
            'message': error_msg
        }


@shared_task
def cleanup_old_backups():
    """
    Очищает старые резервные копии
    """
    try:
        logger.info("Starting backup cleanup")
        
        backups = backup_manager.list_backups()
        max_backups = backup_manager.max_backups
        
        if len(backups) > max_backups:
            backups_to_delete = backups[max_backups:]
            deleted_count = 0
            
            for backup in backups_to_delete:
                try:
                    # Удаляем файл бэкапа
                    import os
                    if os.path.exists(backup['path']):
                        os.remove(backup['path'])
                    
                    # Удаляем метаданные
                    metadata_path = f"{backup['path']}.meta"
                    if os.path.exists(metadata_path):
                        os.remove(metadata_path)
                    
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {backup['id']}")
                    
                except Exception as e:
                    logger.warning(f"Error deleting backup {backup['id']}: {e}")
            
            log_system_event(
                'backup_cleanup_completed',
                f'Cleaned up {deleted_count} old backups',
                'info',
                metadata={'deleted_count': deleted_count}
            )
            
            logger.info(f"Backup cleanup completed: {deleted_count} backups deleted")
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Cleaned up {deleted_count} old backups'
            }
        else:
            logger.info("No old backups to clean up")
            return {
                'success': True,
                'deleted_count': 0,
                'message': 'No old backups to clean up'
            }
            
    except Exception as e:
        error_msg = f"Error during backup cleanup: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        log_system_event(
            'backup_cleanup_error',
            error_msg,
            'error',
            metadata={'error': str(e)}
        )
        
        return {
            'success': False,
            'message': error_msg
        }


@shared_task
def check_system_health_task():
    """
    Проверяет состояние системы и отправляет предупреждения
    """
    try:
        logger.info("Starting system health check")
        
        # Получаем метрики системы
        metrics = system_monitor.get_system_metrics()
        
        # Получаем предупреждения
        alerts = system_monitor.get_performance_alerts()
        
        # Логируем критические предупреждения
        critical_alerts = [alert for alert in alerts if alert['severity'] == 'critical']
        warning_alerts = [alert for alert in alerts if alert['severity'] == 'warning']
        
        if critical_alerts:
            for alert in critical_alerts:
                log_system_event(
                    'system_critical_alert',
                    f"Critical system alert: {alert['message']}",
                    'critical',
                    metadata={
                        'alert_type': alert['type'],
                        'component': alert['component'],
                        'message': alert['message']
                    }
                )
        
        if warning_alerts:
            for alert in warning_alerts:
                log_system_event(
                    'system_warning_alert',
                    f"System warning: {alert['message']}",
                    'warning',
                    metadata={
                        'alert_type': alert['type'],
                        'component': alert['component'],
                        'message': alert['message']
                    }
                )
        
        logger.info(f"System health check completed: {len(critical_alerts)} critical, {len(warning_alerts)} warnings")
        
        return {
            'success': True,
            'critical_alerts': len(critical_alerts),
            'warning_alerts': len(warning_alerts),
            'total_alerts': len(alerts),
            'message': f'Health check completed: {len(critical_alerts)} critical, {len(warning_alerts)} warnings'
        }
        
    except Exception as e:
        error_msg = f"Error during system health check: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        log_system_event(
            'system_health_check_error',
            error_msg,
            'error',
            metadata={'error': str(e)}
        )
        
        return {
            'success': False,
            'message': error_msg
        }


@shared_task
def verify_data_integrity_task():
    """
    Проверяет целостность данных
    """
    try:
        logger.info("Starting data integrity verification")
        
        from .backup_utils import verify_data_integrity
        integrity_status = verify_data_integrity()
        
        if integrity_status['overall_status'] == 'healthy':
            log_system_event(
                'data_integrity_healthy',
                'Data integrity check passed',
                'info',
                metadata=integrity_status
            )
        else:
            log_system_event(
                'data_integrity_issues',
                f"Data integrity issues found: {integrity_status['overall_status']}",
                'warning',
                metadata=integrity_status
            )
        
        logger.info(f"Data integrity verification completed: {integrity_status['overall_status']}")
        
        return {
            'success': True,
            'integrity_status': integrity_status['overall_status'],
            'issues_found': integrity_status['overall_status'] != 'healthy',
            'message': f'Data integrity check completed: {integrity_status["overall_status"]}'
        }
        
    except Exception as e:
        error_msg = f"Error during data integrity verification: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        log_system_event(
            'data_integrity_error',
            error_msg,
            'error',
            metadata={'error': str(e)}
        )
        
        return {
            'success': False,
            'message': error_msg
        }


@shared_task
def log_system_metrics():
    """
    Логирует системные метрики для мониторинга
    """
    try:
        metrics = system_monitor.get_system_metrics()
        
        # Логируем основные метрики
        cpu_usage = metrics.get('cpu', {}).get('usage_percent', 0)
        memory_usage = metrics.get('memory', {}).get('used_percent', 0)
        disk_usage = metrics.get('disk', {}).get('used_percent', 0)
        db_response_time = metrics.get('database', {}).get('response_time_ms', 0)
        
        log_system_event(
            'system_metrics',
            f'System metrics: CPU {cpu_usage}%, Memory {memory_usage}%, Disk {disk_usage}%, DB {db_response_time}ms',
            'info',
            metadata={
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'db_response_time': db_response_time
            }
        )
        
        logger.info(f"System metrics logged: CPU {cpu_usage}%, Memory {memory_usage}%, Disk {disk_usage}%")
        
        return {
            'success': True,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'db_response_time': db_response_time
        }
        
    except Exception as e:
        error_msg = f"Error logging system metrics: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'message': error_msg
        }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 60 секунд между попытками
    autoretry_for=(Exception,),  # Автоматический retry для всех исключений
    retry_backoff=True,  # Экспоненциальная задержка
    retry_backoff_max=600,  # Максимум 10 минут
    retry_jitter=True  # Добавляем случайную задержку для избежания thundering herd
)
def process_subscription_payments(self):
    """
    Обрабатывает регулярные платежи по активным подпискам

    Retry Strategy:
    - Transient failures (network, API down): retry 3 times with exponential backoff
    - Permanent failures (invalid data, missing parent): log and skip
    - Dead letter: после 3 неудачных попыток задача помечается как failed
    """
    task_id = self.request.id
    retry_count = self.request.retries

    logger.info(
        f"[CELERY] Starting subscription payments processing "
        f"(task_id={task_id}, retry={retry_count}/{self.max_retries})"
    )

    try:
        from django.core.management import call_command
        from io import StringIO

        # Захватываем вывод команды
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)
        output = out.getvalue()

        logger.info(
            f"[CELERY] Subscription payments processing completed successfully "
            f"(task_id={task_id}, retry={retry_count})"
        )

        log_system_event(
            'subscription_payments_processed',
            f'Subscription payments processing completed (task_id={task_id})',
            'info',
            metadata={
                'task_id': task_id,
                'retry_count': retry_count,
                'output': output
            }
        )

        return {
            'success': True,
            'task_id': task_id,
            'retry_count': retry_count,
            'message': 'Subscription payments processing completed',
            'output': output
        }

    except Exception as e:
        error_msg = f"Error processing subscription payments: {str(e)}"
        logger.error(
            f"[CELERY] {error_msg} (task_id={task_id}, retry={retry_count}/{self.max_retries})",
            exc_info=True
        )

        # Проверяем тип ошибки для решения о retry
        is_transient = _is_transient_error(e)

        if is_transient and retry_count < self.max_retries:
            # Transient error - будет автоматический retry
            logger.warning(
                f"[CELERY] Transient error detected, will retry "
                f"(attempt {retry_count + 1}/{self.max_retries + 1}): {error_msg}"
            )

            log_system_event(
                'subscription_payments_retry',
                f'Retrying subscription payments after transient error (attempt {retry_count + 1})',
                'warning',
                metadata={
                    'task_id': task_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'retry_count': retry_count,
                    'max_retries': self.max_retries,
                    'is_transient': True
                }
            )

            # Raise для автоматического retry
            raise
        else:
            # Permanent error или исчерпаны попытки - отправляем в dead letter
            severity = 'critical' if retry_count >= self.max_retries else 'error'
            logger.error(
                f"[CELERY] {'Max retries exceeded' if retry_count >= self.max_retries else 'Permanent error'}, "
                f"sending to dead letter queue (task_id={task_id}): {error_msg}"
            )

            log_system_event(
                'subscription_payments_dead_letter',
                f'Subscription payments task failed permanently (task_id={task_id})',
                severity,
                metadata={
                    'task_id': task_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'retry_count': retry_count,
                    'max_retries': self.max_retries,
                    'is_transient': is_transient,
                    'reason': 'max_retries_exceeded' if retry_count >= self.max_retries else 'permanent_error'
                }
            )

            # Отправляем в мертвую очередь (dead letter queue)
            _send_to_dead_letter_queue(task_id, self.name, error_msg, e, retry_count)

            return {
                'success': False,
                'task_id': task_id,
                'retry_count': retry_count,
                'message': error_msg,
                'dead_letter': True
            }


def _is_transient_error(error):
    """
    Определяет, является ли ошибка временной (transient) или постоянной (permanent)

    Transient errors (подлежат retry):
    - ConnectionError, Timeout - проблемы с сетью
    - YooKassa API errors (5xx)
    - Database connection errors

    Permanent errors (не retry, пропускаем):
    - ValidationError - неверные данные
    - DoesNotExist - отсутствующие записи
    - YooKassa client errors (4xx, кроме 429)
    """
    import requests
    from django.core.exceptions import ValidationError
    from django.db import OperationalError, InterfaceError

    # Network/connection errors - transient
    if isinstance(error, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
        OperationalError,
        InterfaceError
    )):
        return True

    # HTTP 5xx и 429 (rate limit) - transient
    if isinstance(error, requests.exceptions.HTTPError):
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code
            if status_code >= 500 or status_code == 429:
                return True

    # Validation/data errors - permanent
    if isinstance(error, (ValidationError, ValueError, KeyError)):
        return False

    # По умолчанию считаем ошибку временной (safer to retry)
    return True


def _send_to_dead_letter_queue(task_id, task_name, error_msg, exception, retry_count):
    """
    Отправляет информацию о неудачной задаче в dead letter queue

    Сохраняет в БД для последующего анализа и мониторинга
    """
    import traceback

    # Получаем полный traceback
    tb_str = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))

    dead_letter_entry = {
        'task_id': task_id,
        'task_name': task_name,
        'error_message': error_msg,
        'error_type': type(exception).__name__,
        'retry_count': retry_count,
        'timestamp': timezone.now().isoformat(),
        'traceback': tb_str
    }

    # Логируем в файл
    logger.critical(
        f"[DEAD_LETTER_QUEUE] Task permanently failed: {task_name} (id={task_id})\n"
        f"Error: {error_msg}\n"
        f"Type: {type(exception).__name__}\n"
        f"Retries: {retry_count}\n"
        f"Traceback:\n{tb_str}"
    )

    # Сохраняем в БД для последующего анализа
    try:
        from core.models import FailedTask

        is_transient = _is_transient_error(exception)

        FailedTask.objects.create(
            task_id=task_id,
            task_name=task_name,
            error_message=error_msg,
            error_type=type(exception).__name__,
            traceback=tb_str,
            retry_count=retry_count,
            is_transient=is_transient,
            metadata=dead_letter_entry
        )

        logger.info(f"[DEAD_LETTER_QUEUE] Saved to database: {task_id}")

    except Exception as db_error:
        logger.error(
            f"[DEAD_LETTER_QUEUE] Failed to save to database: {db_error}",
            exc_info=True
        )

    # TODO: В production добавить:
    # - Отправку уведомления в Telegram/Email администратору
    # - Интеграцию с Sentry/Rollbar для мониторинга
    # - Автоматическое создание issue в системе мониторинга

    return dead_letter_entry
