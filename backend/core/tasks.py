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
