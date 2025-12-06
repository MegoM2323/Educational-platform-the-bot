"""
API endpoints для мониторинга Celery задач
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from datetime import timedelta

from .models import FailedTask, TaskExecutionLog


class CeleryMonitoringView(APIView):
    """
    Обзорная информация о состоянии Celery задач

    GET /api/core/monitoring/celery/
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Статистика неудачных задач
        failed_tasks_count = FailedTask.objects.filter(status=FailedTask.Status.FAILED).count()
        investigating_count = FailedTask.objects.filter(status=FailedTask.Status.INVESTIGATING).count()
        resolved_count = FailedTask.objects.filter(status=FailedTask.Status.RESOLVED).count()

        # Последние неудачные задачи
        recent_failed = FailedTask.objects.filter(
            status=FailedTask.Status.FAILED
        ).order_by('-failed_at')[:10]

        # Статистика выполнения за последние 24 часа
        since = timezone.now() - timedelta(hours=24)
        executions_24h = TaskExecutionLog.objects.filter(started_at__gte=since)
        success_count = executions_24h.filter(status=TaskExecutionLog.Status.SUCCESS).count()
        failed_count = executions_24h.filter(status=TaskExecutionLog.Status.FAILED).count()

        # Средняя длительность выполнения
        avg_duration = executions_24h.filter(
            duration_seconds__isnull=False
        ).aggregate(avg=timezone.models.Avg('duration_seconds'))['avg']

        # Последние выполнения
        recent_executions = TaskExecutionLog.objects.order_by('-started_at')[:20]

        return Response({
            'success': True,
            'data': {
                'failed_tasks': {
                    'total': failed_tasks_count + investigating_count,
                    'failed': failed_tasks_count,
                    'investigating': investigating_count,
                    'resolved_last_24h': FailedTask.objects.filter(
                        status=FailedTask.Status.RESOLVED,
                        resolved_at__gte=since
                    ).count(),
                    'recent': [
                        {
                            'id': task.id,
                            'task_name': task.task_name,
                            'error_type': task.error_type,
                            'error_message': task.error_message[:200],
                            'retry_count': task.retry_count,
                            'is_transient': task.is_transient,
                            'failed_at': task.failed_at.isoformat(),
                        }
                        for task in recent_failed
                    ]
                },
                'executions_24h': {
                    'total': executions_24h.count(),
                    'success': success_count,
                    'failed': failed_count,
                    'success_rate': round(success_count / executions_24h.count() * 100, 2) if executions_24h.count() > 0 else 0,
                    'avg_duration_seconds': round(avg_duration, 2) if avg_duration else 0,
                },
                'recent_executions': [
                    {
                        'id': log.id,
                        'task_name': log.task_name,
                        'status': log.status,
                        'started_at': log.started_at.isoformat(),
                        'duration_seconds': log.duration_seconds,
                        'retry_count': log.retry_count,
                    }
                    for log in recent_executions
                ],
                'health_status': 'healthy' if failed_tasks_count == 0 and success_count > failed_count else 'warning' if failed_tasks_count < 5 else 'critical'
            }
        })


class FailedTaskDetailView(APIView):
    """
    Детали неудачной задачи

    GET /api/core/monitoring/failed-tasks/<id>/
    PATCH /api/core/monitoring/failed-tasks/<id>/ - обновить статус
    """
    permission_classes = [IsAdminUser]

    def get(self, request, task_id):
        try:
            task = FailedTask.objects.get(id=task_id)

            return Response({
                'success': True,
                'data': {
                    'id': task.id,
                    'task_id': task.task_id,
                    'task_name': task.task_name,
                    'status': task.status,
                    'error_type': task.error_type,
                    'error_message': task.error_message,
                    'traceback': task.traceback,
                    'retry_count': task.retry_count,
                    'is_transient': task.is_transient,
                    'metadata': task.metadata,
                    'failed_at': task.failed_at.isoformat(),
                    'investigated_at': task.investigated_at.isoformat() if task.investigated_at else None,
                    'resolved_at': task.resolved_at.isoformat() if task.resolved_at else None,
                    'investigation_notes': task.investigation_notes,
                    'resolution_notes': task.resolution_notes,
                }
            })

        except FailedTask.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, task_id):
        """Обновить статус задачи"""
        try:
            task = FailedTask.objects.get(id=task_id)

            new_status = request.data.get('status')
            notes = request.data.get('notes', '')

            if new_status == 'investigating':
                task.mark_investigating(notes)
            elif new_status == 'resolved':
                task.mark_resolved(notes)
            elif new_status == 'ignored':
                task.mark_ignored(notes)
            else:
                return Response(
                    {'success': False, 'error': 'Invalid status'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'success': True,
                'message': f'Task status updated to {new_status}'
            })

        except FailedTask.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class TaskExecutionStatsView(APIView):
    """
    Статистика выполнения задач по типам

    GET /api/core/monitoring/task-stats/?hours=24
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)

        # Группируем по имени задачи
        from django.db.models import Count, Avg, Max, Min

        stats_by_task = {}

        task_names = TaskExecutionLog.objects.filter(
            started_at__gte=since
        ).values_list('task_name', flat=True).distinct()

        for task_name in task_names:
            logs = TaskExecutionLog.objects.filter(
                task_name=task_name,
                started_at__gte=since
            )

            success = logs.filter(status=TaskExecutionLog.Status.SUCCESS).count()
            failed = logs.filter(status=TaskExecutionLog.Status.FAILED).count()
            total = logs.count()

            duration_stats = logs.filter(duration_seconds__isnull=False).aggregate(
                avg=Avg('duration_seconds'),
                max=Max('duration_seconds'),
                min=Min('duration_seconds')
            )

            stats_by_task[task_name] = {
                'total_executions': total,
                'success': success,
                'failed': failed,
                'success_rate': round(success / total * 100, 2) if total > 0 else 0,
                'avg_duration': round(duration_stats['avg'], 2) if duration_stats['avg'] else 0,
                'max_duration': round(duration_stats['max'], 2) if duration_stats['max'] else 0,
                'min_duration': round(duration_stats['min'], 2) if duration_stats['min'] else 0,
            }

        return Response({
            'success': True,
            'data': {
                'period_hours': hours,
                'stats_by_task': stats_by_task
            }
        })
