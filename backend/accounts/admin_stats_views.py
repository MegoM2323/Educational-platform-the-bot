"""
Админские API endpoints для статистики пользователей.
Предоставляет агрегированную статистику по пользователям системы.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
import logging

from .models import User
from .permissions import IsAdminUser

logger = logging.getLogger(__name__)


class AdminUserStatsView(APIView):
    """
    GET /api/admin/stats/users/ - Статистика пользователей (admin only)

    Возвращает агрегированную статистику по всем пользователям системы:
    - Общее количество пользователей
    - Количество по ролям (student, teacher, tutor, parent)
    - Количество активных пользователей (is_active=True)
    - Количество активных сегодня (date_joined = today)

    Permissions:
        - IsAdminUser (только staff/superuser)

    Response:
        200 OK:
            {
                "success": true,
                "data": {
                    "total_users": 150,
                    "total_students": 80,
                    "total_teachers": 25,
                    "total_tutors": 10,
                    "total_parents": 35,
                    "active_users": 145,
                    "active_today": 5
                }
            }
        403 Forbidden: Если не admin
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить статистику по пользователям"""
        try:
            # Общее количество пользователей
            total_users = User.objects.count()

            # Количество по ролям
            total_students = User.objects.filter(role=User.Role.STUDENT).count()
            total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
            total_tutors = User.objects.filter(role=User.Role.TUTOR).count()
            total_parents = User.objects.filter(role=User.Role.PARENT).count()

            # Активные пользователи (is_active=True)
            active_users = User.objects.filter(is_active=True).count()

            # Активные сегодня (date_joined = today)
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            active_today = User.objects.filter(
                date_joined__gte=today_start
            ).count()

            logger.info(
                f"[AdminUserStatsView] Stats: total={total_users}, "
                f"students={total_students}, teachers={total_teachers}, "
                f"tutors={total_tutors}, parents={total_parents}, "
                f"active={active_users}, active_today={active_today}"
            )

            return Response(
                {
                    'success': True,
                    'data': {
                        'total_users': total_users,
                        'total_students': total_students,
                        'total_teachers': total_teachers,
                        'total_tutors': total_tutors,
                        'total_parents': total_parents,
                        'active_users': active_users,
                        'active_today': active_today,
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"[AdminUserStatsView] Error: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Ошибка при получении статистики'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
