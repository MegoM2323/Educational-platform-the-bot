"""
API views для мониторинга и управления системой
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .monitoring import system_monitor, check_system_health, log_system_event
from .backup_utils import backup_manager, verify_data_integrity
from .transaction_utils import transaction_manager


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_health_view(request):
    """
    Получает статус здоровья системы
    """
    try:
        health_status = check_system_health()
        return Response(health_status)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения статуса системы: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_metrics_view(request):
    """
    Получает метрики системы
    """
    try:
        metrics = system_monitor.get_system_metrics()
        return Response(metrics)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения метрик: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def analytics_dashboard_view(request):
    """
    Получает аналитические данные для дашборда мониторинга
    """
    try:
        from django.db import connection
        from django.core.cache import cache
        from datetime import datetime, timedelta
        
        # Получаем базовые метрики системы
        system_metrics = system_monitor.get_system_metrics()
        
        # Добавляем информацию о кэше
        try:
            test_key = 'analytics_test'
            cache.set(test_key, 'test', 10)
            cache_stats = {
                'working': True,
                'test_key': cache.get(test_key) is not None
            }
            cache.delete(test_key)
        except Exception as e:
            cache_stats = {'working': False, 'error': str(e)}
        
        # Добавляем дополнительные аналитические данные
        analytics = {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': system_metrics,
            'cache_stats': cache_stats,
        }
        
        return Response(analytics)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения аналитических данных: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def data_integrity_view(request):
    """
    Проверяет целостность данных
    """
    try:
        integrity_status = verify_data_integrity()
        return Response(integrity_status)
    except Exception as e:
        return Response(
            {'error': f'Ошибка проверки целостности данных: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def performance_alerts_view(request):
    """
    Получает предупреждения о производительности
    """
    try:
        alerts = system_monitor.get_performance_alerts()
        return Response({'alerts': alerts})
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения предупреждений: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def backup_list_view(request):
    """
    Получает список резервных копий
    """
    try:
        backup_type = request.GET.get('type')
        backups = backup_manager.list_backups(backup_type)
        return Response({'backups': backups})
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения списка резервных копий: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_backup_view(request):
    """
    Создает резервную копию
    """
    try:
        backup_type = request.data.get('type', 'full')
        description = request.data.get('description', f'Manual {backup_type} backup')
        
        if backup_type == 'database':
            backup_info = backup_manager.create_database_backup(description)
        elif backup_type == 'media':
            backup_info = backup_manager.create_media_backup(description)
        elif backup_type == 'full':
            backup_info = backup_manager.create_full_backup(description)
        else:
            return Response(
                {'error': 'Недопустимый тип резервной копии'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Логируем создание резервной копии
        log_system_event(
            'backup_created',
            f'Backup created: {backup_info["id"]}',
            'info',
            user_id=request.user.id,
            metadata={'backup_id': backup_info['id'], 'type': backup_type}
        )
        
        return Response(backup_info, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        log_system_event(
            'backup_creation_failed',
            f'Failed to create backup: {str(e)}',
            'error',
            user_id=request.user.id
        )
        return Response(
            {'error': f'Ошибка создания резервной копии: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def restore_backup_view(request):
    """
    Восстанавливает из резервной копии
    """
    try:
        backup_id = request.data.get('backup_id')
        if not backup_id:
            return Response(
                {'error': 'Не указан ID резервной копии'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем существование резервной копии
        backup_info = None
        for backup in backup_manager.list_backups():
            if backup['id'] == backup_id:
                backup_info = backup
                break
        
        if not backup_info:
            return Response(
                {'error': 'Резервная копия не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Выполняем восстановление
        success = backup_manager.restore_database_backup(backup_id)
        
        if success:
            log_system_event(
                'backup_restored',
                f'Backup restored: {backup_id}',
                'info',
                user_id=request.user.id,
                metadata={'backup_id': backup_id}
            )
            return Response({'message': 'База данных успешно восстановлена'})
        else:
            return Response(
                {'error': 'Ошибка восстановления базы данных'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        log_system_event(
            'backup_restore_failed',
            f'Failed to restore backup: {str(e)}',
            'error',
            user_id=request.user.id
        )
        return Response(
            {'error': f'Ошибка восстановления: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def active_transactions_view(request):
    """
    Получает список активных транзакций
    """
    try:
        active_transactions = list(transaction_manager.active_transactions.values())
        return Response({'active_transactions': active_transactions})
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения активных транзакций: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def log_system_event_view(request):
    """
    Логирует системное событие
    """
    try:
        event_type = request.data.get('event_type')
        message = request.data.get('message')
        severity = request.data.get('severity', 'info')
        metadata = request.data.get('metadata', {})
        
        if not event_type or not message:
            return Response(
                {'error': 'Не указаны обязательные поля: event_type, message'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        log_system_event(
            event_type,
            message,
            severity,
            user_id=request.user.id,
            metadata=metadata
        )
        
        return Response({'message': 'Событие успешно залогировано'})
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка логирования события: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check_view(request):
    """
    Простая проверка здоровья системы (публичный endpoint)
    """
    try:
        # Базовая проверка доступности базы данных
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=500)
