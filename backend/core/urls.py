"""
URL patterns для core приложения
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .config_views import ConfigurationViewSet
from .monitoring_views import (
    CeleryMonitoringView,
    FailedTaskDetailView,
    TaskExecutionStatsView
)
from .admin_monitoring_views import (
    admin_system_metrics_view,
    admin_system_health_view,
    AdminSystemAlertsView,
    AdminSystemHistoryView
)
from .admin_database_views import (
    DatabaseStatusView,
    DatabaseTablesViewSet,
    DatabaseQueriesView,
    BackupManagementViewSet,
    BackupDetailView,
    BackupDeleteView,
    MaintenanceTaskView,
    MaintenanceStatusView,
    KillQueryView,
)
from .stats_views import (
    dashboard_stats,
    user_stats,
    lesson_stats,
    invoice_stats,
    knowledge_graph_stats
)
from .cache_stats_views import (
    cache_stats_view,
    cache_clear_view,
    cache_reset_stats_view,
    cache_health_view
)

# Router for ViewSets
router = DefaultRouter()
router.register(r'audit-log', views.AuditLogViewSet, basename='audit-log')
router.register(r'admin/config', ConfigurationViewSet, basename='configuration')
router.register(r'admin/system/database/tables', DatabaseTablesViewSet, basename='database-tables')
router.register(r'admin/system/database/backups', BackupManagementViewSet, basename='database-backups')

app_name = 'core'

urlpatterns = [
    # API ViewSets (audit log, etc.)
    path('', include(router.urls)),

    # Kubernetes-ready health check endpoints
    path('health/live/', views.liveness_check, name='liveness_check'),
    path('health/ready/', views.readiness_check, name='readiness_check'),
    path('health/startup/', views.startup_health_check, name='startup_health_check'),
    path('health/detailed/', views.detailed_health_check, name='detailed_health_check'),

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

    # Кэширование и управление кэшем
    path('cache-stats/', cache_stats_view, name='cache_stats'),
    path('cache-clear/', cache_clear_view, name='cache_clear'),
    path('cache-reset-stats/', cache_reset_stats_view, name='cache_reset_stats'),
    path('cache-health/', cache_health_view, name='cache_health'),

    # Admin System Monitoring Dashboard (для админ-панели)
    path('admin/system/metrics/', admin_system_metrics_view, name='admin_system_metrics'),
    path('admin/system/health/', admin_system_health_view, name='admin_system_health'),
    path('admin/system/alerts/', AdminSystemAlertsView.as_view(), name='admin_system_alerts'),
    path('admin/system/history/', AdminSystemHistoryView.as_view(), name='admin_system_history'),

    # Database Admin API endpoints (для админ-панели)
    path('admin/system/database/', DatabaseStatusView.as_view(), name='database_status'),
    path('admin/system/database/queries/', DatabaseQueriesView.as_view(), name='database_queries'),
    path('admin/database/backup/<str:backup_id>/restore/', BackupDetailView.as_view(), name='backup_restore'),
    path('admin/database/backup/<str:backup_id>/', BackupDeleteView.as_view(), name='backup_delete'),
    path('admin/database/maintenance/', MaintenanceTaskView.as_view(), name='maintenance_task'),
    path('admin/database/maintenance/<str:task_id>/', MaintenanceStatusView.as_view(), name='maintenance_status'),
    path('admin/database/kill-query/', KillQueryView.as_view(), name='kill_query'),
]
