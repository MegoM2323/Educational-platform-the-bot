"""
API views для мониторинга и управления системой
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from .monitoring import system_monitor, check_system_health, log_system_event
from .backup_utils import backup_manager, verify_data_integrity
from .transaction_utils import transaction_manager
from .health import health_checker
from .models import AuditLog
from .audit import AuditLogViewSetHelper
from rest_framework import serializers


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


# Kubernetes-ready health check endpoints

@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Kubernetes liveness probe endpoint.

    Used by Kubernetes to check if pod should be restarted.
    No heavy checks - just verify process is running.

    Returns:
        200 OK: Service is alive
    """
    response = health_checker.get_liveness_response()
    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Kubernetes readiness probe endpoint.

    Checks if service is ready to handle requests:
    - Database connectivity (SELECT 1)
    - Redis connectivity (PING)
    - Celery task queue status

    Returns:
        200 OK: Service is ready
        503 Service Unavailable: Service not ready
    """
    response, http_status = health_checker.get_readiness_response()
    return Response(response, status=http_status)


@api_view(['GET'])
@permission_classes([AllowAny])
def detailed_health_check(request):
    """
    Detailed health check endpoint with system metrics.

    Includes all readiness checks plus:
    - CPU usage (%)
    - Memory usage (%)
    - Disk space (%)
    - WebSocket status

    Response format:
    {
        "status": "healthy|degraded|unhealthy",
        "timestamp": "ISO8601",
        "components": {
            "database": {"status": "healthy|unhealthy", "response_time_ms": 5},
            "redis": {"status": "healthy|unhealthy", "response_time_ms": 2, "memory_mb": 256},
            "celery": {"status": "healthy|unhealthy", "workers": 4, "queue_length": 2},
            "websocket": {"status": "healthy|unhealthy", "connections": 150},
            "cpu": {"status": "healthy|degraded|unhealthy", "used_percent": 25, "load_average": 1.5},
            "memory": {"status": "healthy|degraded|unhealthy", "used_percent": 60, ...},
            "disk": {"status": "healthy|degraded|unhealthy", "used_percent": 40, ...}
        }
    }

    Returns:
        200 OK: Detailed health information
    """
    response = health_checker.get_detailed_response()
    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def startup_health_check(request):
    """
    Startup health check endpoint (Kubernetes startup probe).

    Checks only critical components required at startup:
    - Database connectivity
    - Redis connectivity

    This endpoint is used by Kubernetes startupProbe to determine if the pod
    can be considered as started. If this fails, the pod will restart.

    Response format:
    {
        "status": "healthy|startup_failed",
        "timestamp": "ISO8601",
        "checks": {
            "database": {"status": "healthy|unhealthy", "response_time_ms": 15},
            "redis": {"status": "healthy|unhealthy", "memory_mb": 256}
        }
    }

    Returns:
        200 OK: Service started successfully
        503 Service Unavailable: Startup checks failed
    """
    response, http_status = health_checker.get_startup_response()
    return Response(response, status=http_status)


# AuditLog Serializer and ViewSet
class AuditLogSerializer(ModelSerializer):
    """
    Serializer for AuditLog model

    Provides read-only access to audit log entries with user information
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(
        source='user.get_full_name',
        read_only=True
    )
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'action',
            'action_display',
            'user',
            'user_email',
            'user_full_name',
            'target_type',
            'target_id',
            'target_description',
            'ip_address',
            'user_agent',
            'metadata',
            'timestamp',
        ]
        read_only_fields = fields


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API ViewSet for audit log access.

    Provides admin-only read-only access to audit logs with filtering
    capabilities by user, action, date range, and IP address.

    Endpoints:
    - GET /api/core/audit-log/ - List audit logs with filters
    - GET /api/core/audit-log/{id}/ - View specific audit log entry
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    queryset = AuditLog.objects.select_related('user').order_by('-timestamp')

    def get_queryset(self):
        """
        Filter audit logs based on query parameters.

        Query Parameters:
        - user_id: Filter by user ID
        - action: Filter by action type
        - target_type: Filter by target type
        - ip_address: Filter by IP address
        - date_from: Filter by start date (ISO format)
        - date_to: Filter by end date (ISO format)
        """
        queryset = AuditLogViewSetHelper.get_optimized_queryset()

        # Extract filter parameters
        user_id = self.request.query_params.get('user_id')
        action = self.request.query_params.get('action')
        target_type = self.request.query_params.get('target_type')
        ip_address = self.request.query_params.get('ip_address')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        # Apply filters
        queryset = AuditLogViewSetHelper.apply_filters(
            queryset,
            user_id=user_id,
            action=action,
            target_type=target_type,
            ip_address=ip_address,
            date_from=date_from,
            date_to=date_to
        )

        return queryset
