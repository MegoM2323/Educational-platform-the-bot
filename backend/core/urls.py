"""
URL patterns для core приложения
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Мониторинг системы
    path('health/', views.system_health_view, name='system_health'),
    path('metrics/', views.system_metrics_view, name='system_metrics'),
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
    path('integrity/', views.data_integrity_view, name='data_integrity'),
    path('alerts/', views.performance_alerts_view, name='performance_alerts'),
    
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
]
