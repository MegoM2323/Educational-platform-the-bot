"""
URL patterns для core приложения
"""
from django.urls import path
from . import views
from .monitoring_views import (
    CeleryMonitoringView,
    FailedTaskDetailView,
    TaskExecutionStatsView
)
from .stats_views import (
    dashboard_stats,
    user_stats,
    lesson_stats,
    invoice_stats,
    knowledge_graph_stats
)

app_name = 'core'

urlpatterns = [
    # Мониторинг системы
    path('health/', views.system_health_view, name='system_health'),
    path('metrics/', views.system_metrics_view, name='system_metrics'),
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
    path('integrity/', views.data_integrity_view, name='data_integrity'),
    path('alerts/', views.performance_alerts_view, name='performance_alerts'),

    # Мониторинг Celery задач
    path('monitoring/celery/', CeleryMonitoringView.as_view(), name='celery_monitoring'),
    path('monitoring/failed-tasks/<int:task_id>/', FailedTaskDetailView.as_view(), name='failed_task_detail'),
    path('monitoring/task-stats/', TaskExecutionStatsView.as_view(), name='task_stats'),

    # Управление резервными копиями
    path('backups/', views.backup_list_view, name='backup_list'),
    path('backups/create/', views.create_backup_view, name='create_backup'),
    path('backups/restore/', views.restore_backup_view, name='restore_backup'),

    # Управление транзакциями
    path('transactions/', views.active_transactions_view, name='active_transactions'),

    # Логирование
    path('log-event/', views.log_system_event_view, name='log_event'),

    # Публичная проверка здоровья
    path('health-check/', views.health_check_view, name='health_check'),

    # Статистика для админ-панели (только staff/superuser)
    path('admin/stats/dashboard/', dashboard_stats, name='admin_stats_dashboard'),
    path('admin/stats/users/', user_stats, name='admin_stats_users'),
    path('admin/stats/lessons/', lesson_stats, name='admin_stats_lessons'),
    path('admin/stats/invoices/', invoice_stats, name='admin_stats_invoices'),
    path('admin/stats/knowledge-graph/', knowledge_graph_stats, name='admin_stats_knowledge_graph'),
]
