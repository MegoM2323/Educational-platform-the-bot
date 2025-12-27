"""
API views для статистики админ-панели.

Все endpoints защищены IsAdminUser permission (только staff/superuser).
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import IsAdminUser
from .admin_stats import (
    get_dashboard_stats,
    get_user_stats,
    get_lesson_stats,
    get_invoice_stats,
    get_knowledge_graph_stats
)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def dashboard_stats(request):
    """
    Главная статистика для админ-панели.

    GET /api/admin/stats/dashboard/

    Returns:
        {
            "users": {
                "total": 150,
                "students": 80,
                "teachers": 20,
                "tutors": 10,
                "parents": 40
            },
            "activity": {
                "online_now": 25,
                "active_today": 85,
                "lessons_today": 12,
                "invoices_unpaid": 5
            },
            "performance": {
                "avg_student_progress": 65.5,
                "lessons_completed_this_week": 34,
                "revenue_this_month": 150000
            }
        }
    """
    try:
        stats = get_dashboard_stats()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения статистики: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_stats(request):
    """
    Статистика по пользователям.

    GET /api/admin/stats/users/?role=student

    Query Parameters:
        role (optional): Фильтр по роли (student, teacher, tutor, parent)

    Returns:
        {
            "role": "student",
            "total": 80,
            "active": 75,
            "inactive": 5,
            "by_grade": {
                "9A": 10,
                "9B": 12,
                ...
            },
            "created_today": 3,
            "created_this_week": 15
        }
    """
    role = request.query_params.get('role')

    # Валидация роли
    if role and role not in ['student', 'teacher', 'tutor', 'parent']:
        return Response(
            {'error': 'Недопустимое значение role. Допустимые: student, teacher, tutor, parent'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        stats = get_user_stats(role)
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения статистики пользователей: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def lesson_stats(request):
    """
    Статистика по урокам.

    GET /api/admin/stats/lessons/

    Returns:
        {
            "total_lessons": 250,
            "lessons_today": 12,
            "lessons_this_week": 45,
            "by_status": {
                "pending": 5,
                "confirmed": 35,
                "completed": 210
            },
            "avg_duration_minutes": 45
        }
    """
    try:
        stats = get_lesson_stats()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения статистики уроков: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def invoice_stats(request):
    """
    Статистика по счетам.

    GET /api/admin/stats/invoices/

    Returns:
        {
            "total_invoices": 120,
            "unpaid": 5,
            "paid": 115,
            "total_revenue": 250000,
            "paid_revenue": 245000,
            "unpaid_amount": 5000,
            "avg_invoice_amount": 2083,
            "overdue_count": 2
        }
    """
    try:
        stats = get_invoice_stats()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения статистики счетов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def knowledge_graph_stats(request):
    """
    Статистика по графу знаний.

    GET /api/admin/stats/knowledge-graph/

    Returns:
        {
            "total_lessons": 45,
            "total_elements": 200,
            "students_with_progress": 30,
            "avg_completion_rate": 45.5,
            "most_difficult_lesson": "Интегралы"
        }
    """
    try:
        stats = get_knowledge_graph_stats()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения статистики графа знаний: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
