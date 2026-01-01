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

    # Process scheduled notifications every minute
    'process-scheduled-notifications': {
        'task': 'notifications.tasks.process_scheduled_notifications',
        'schedule': crontab(minute='*'),
    },

    # Retry failed notifications every 5 minutes
    'retry-failed-notifications': {
        'task': 'notifications.tasks.retry_failed_notifications',
        'schedule': crontab(minute='*/5'),
    },

    # Cleanup old cancelled notifications daily at 3:00
    'cleanup-cancelled-notifications': {
        'task': 'notifications.tasks.cleanup_cancelled_notifications',
        'schedule': crontab(hour=3, minute=0),
    },

    # Archive old notifications (>30 days) daily at 2:00
    'archive-old-notifications': {
        'task': 'notifications.tasks.archive_old_notifications',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'days': 30},
    },

    # Cleanup very old archived notifications (>90 days) weekly on Sunday at 3:30
    'cleanup-old-archived-notifications': {
        'task': 'notifications.tasks.cleanup_old_archived',
        'schedule': crontab(hour=3, minute=30, day_of_week=0),
        'kwargs': {'days': 90},
    },

    # Execute scheduled reports every hour (reports check their own timing internally)
    'execute-scheduled-reports': {
        'task': 'reports.tasks.execute_scheduled_reports',
        'schedule': crontab(minute=0),  # Every hour
    },

    # Refresh materialized views daily at 2:00 AM
    'refresh-materialized-views': {
        'task': 'reports.tasks.refresh_materialized_views',
        'schedule': crontab(hour=2, minute=0),
    },

    # Warm analytics cache daily at 7:00 AM before business hours
    'warm-analytics-cache': {
        'task': 'reports.tasks.warm_analytics_cache',
        'schedule': crontab(hour=7, minute=0),
    },

    # Warm caches hourly (every hour) to maintain hit rate
    'warm-popular-caches': {
        'task': 'core.tasks.warm_cache_task',
        'schedule': crontab(minute=0),  # Run at the top of every hour
    },

    # Monitor cache hit rate every 15 minutes
    'monitor-cache-hit-rate': {
        'task': 'core.tasks.monitor_cache_hit_rate',
        'schedule': crontab(minute='*/15'),
    },

    # Clear expired caches daily at 6:00 AM
    'clear-expired-caches': {
        'task': 'core.tasks.clear_expired_caches',
        'schedule': crontab(hour=6, minute=0),
    },

    # Cleanup expired Telegram link tokens hourly
    'cleanup-expired-telegram-tokens': {
        'task': 'accounts.tasks.cleanup_expired_telegram_tokens',
        'schedule': crontab(minute=0),  # Every hour
    },
}
