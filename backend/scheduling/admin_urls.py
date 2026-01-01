"""
Admin-only URL configuration for scheduling.

Provides routing for admin schedule management endpoints.
All endpoints require IsAdminUser permission.

Подключается в config/urls.py на /api/admin/schedule/

API структура:
- GET /api/admin/schedule/lessons/ - Список всех уроков с фильтрацией
- POST /api/admin/schedule/lessons/create/ - Создание урока администратором
- GET /api/admin/schedule/stats/ - Статистика расписания
- GET /api/admin/schedule/filters/ - Опции фильтров (преподаватели, предметы)
"""

from django.urls import path

from scheduling.admin_views import (
    admin_schedule_view,
    admin_schedule_stats_view,
    admin_schedule_filters_view,
    admin_create_lesson_view,
)

urlpatterns = [
    # Список всех уроков с фильтрацией
    path('lessons/', admin_schedule_view, name='admin-schedule-lessons'),

    # Создание урока администратором
    path('lessons/create/', admin_create_lesson_view, name='admin-schedule-create-lesson'),

    # Статистика расписания (количество уроков, часов и т.д.)
    path('stats/', admin_schedule_stats_view, name='admin-schedule-stats'),

    # Опции для фильтров (список преподавателей, предметов)
    path('filters/', admin_schedule_filters_view, name='admin-schedule-filters'),
]
