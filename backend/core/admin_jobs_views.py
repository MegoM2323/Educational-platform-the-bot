"""
API endpoints для Admin Jobs Monitoring Dashboard

Мониторинг background заданий (Jobs Monitor) в админ кабинете.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.utils import timezone
from django.core.cache import cache
from django.http import JsonResponse


class AdminJobsStatusView(APIView):
    """
    GET /api/admin/jobs/status/ - Список активных заданий

    Возвращает список всех активных background заданий с их статусом и прогрессом.

    Response:
    {
        "success": true,
        "data": [
            {
                "job_id": "job_export_001",
                "name": "Export Users",
                "status": "running|pending|completed|failed",
                "progress": 45,
                "started_at": "2026-01-07T12:34:56+00:00",
                "estimated_completion": "2026-01-07T12:39:56+00:00"
            }
        ]
    }
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить список активных заданий"""
        try:
            # Try to get jobs from cache
            jobs = cache.get('admin_jobs_list', [])

            return Response({
                'success': True,
                'data': jobs
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminJobsDetailView(APIView):
    """
    GET /api/admin/jobs/{job_id}/ - Детали конкретного задания

    Возвращает полную информацию о конкретном задании, включая результаты.

    Response:
    {
        "success": true,
        "data": {
            "job_id": "job_export_001",
            "name": "Export Users",
            "status": "completed",
            "progress": 100,
            "started_at": "2026-01-07T12:34:56+00:00",
            "completed_at": "2026-01-07T12:39:56+00:00",
            "estimated_completion": "2026-01-07T12:39:56+00:00",
            "result": {
                "file_url": "/media/exports/users_export_001.csv",
                "file_size_mb": 12.5,
                "record_count": 1500
            }
        }
    }
    """
    permission_classes = [IsAdminUser]

    def get(self, request, job_id):
        """Получить детали конкретного задания"""
        try:
            # Validate job_id format (basic validation)
            if not job_id or not isinstance(job_id, str) or len(job_id) > 255:
                return Response({
                    'success': False,
                    'error': 'Invalid job_id format'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Try to get job details from cache
            job = cache.get(f'admin_job_detail:{job_id}')

            if not job:
                return Response({
                    'success': False,
                    'error': 'Job not found'
                }, status=status.HTTP_404_NOT_FOUND)

            return Response({
                'success': True,
                'data': job
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminJobsStatsView(APIView):
    """
    GET /api/admin/jobs/stats/ - Статистика заданий

    Возвращает общую статистику по всем заданиям.

    Response:
    {
        "success": true,
        "data": {
            "total_jobs": 127,
            "pending_count": 5,
            "running_count": 3,
            "completed_count": 115,
            "failed_count": 4,
            "average_completion_time": 342.5,
            "success_rate": 96.5
        }
    }
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить статистику заданий"""
        try:
            # Try to get stats from cache
            stats = cache.get('admin_jobs_stats')

            if not stats:
                # Default empty stats
                stats = {
                    'total_jobs': 0,
                    'pending_count': 0,
                    'running_count': 0,
                    'completed_count': 0,
                    'failed_count': 0,
                    'average_completion_time': 0,
                    'success_rate': 0
                }

            return Response({
                'success': True,
                'data': stats
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
