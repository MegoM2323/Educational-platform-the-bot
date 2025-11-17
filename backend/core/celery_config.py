"""
Конфигурация Celery для периодических задач системы мониторинга
"""
from celery.schedules import crontab

# Расписание периодических задач
CELERY_BEAT_SCHEDULE = {
    # Создание ежедневной резервной копии в 2:00
    'create-daily-backup': {
        'task': 'core.tasks.create_daily_backup',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Очистка старых резервных копий каждые 6 часов
    'cleanup-old-backups': {
        'task': 'core.tasks.cleanup_old_backups',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    
    # Проверка состояния системы каждые 5 минут
    'check-system-health': {
        'task': 'core.tasks.check_system_health_task',
        'schedule': crontab(minute='*/5'),
    },
    
    # Проверка целостности данных каждый час
    'verify-data-integrity': {
        'task': 'core.tasks.verify_data_integrity_task',
        'schedule': crontab(minute=0),
    },
    
    # Логирование метрик каждые 15 минут
    'log-system-metrics': {
        'task': 'core.tasks.log_system_metrics',
        'schedule': crontab(minute='*/15'),
    },
    
    # Обработка рекуррентных платежей каждые 5 минут
    'process-subscription-payments': {
        'task': 'core.tasks.process_subscription_payments',
        'schedule': crontab(minute='*/5'),
    },
}
