"""
URL configuration for scheduling app.

Provides routing for all lesson management endpoints.

API структура:
- /api/scheduling/lessons/ - CRUD для уроков (LessonViewSet)
- /api/scheduling/tutor/... - Эндпоинты для тьюторов
- /api/scheduling/parent/... - Эндпоинты для родителей

Примечание: Admin-эндпоинты расписания находятся в admin_urls.py
и подключаются отдельно на /api/admin/schedule/
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from scheduling.views import LessonViewSet
from scheduling.tutor_views import (
    get_student_schedule,
    get_all_student_schedules
)
from scheduling.parent_views import (
    get_child_schedule,
    get_all_children_schedules
)

# Router для ViewSet уроков
router = DefaultRouter()
router.register('lessons', LessonViewSet, basename='lesson')

urlpatterns = [
    # Lessons CRUD - /api/scheduling/lessons/
    path('', include(router.urls)),

    # Tutor endpoints - /api/scheduling/tutor/...
    path('tutor/students/<int:student_id>/schedule/', get_student_schedule, name='tutor-student-schedule'),
    path('tutor/schedule/', get_all_student_schedules, name='tutor-all-schedules'),

    # Parent endpoints - /api/scheduling/parent/...
    path('parent/children/<int:child_id>/schedule/', get_child_schedule, name='parent-child-schedule'),
    path('parent/schedule/', get_all_children_schedules, name='parent-all-schedules'),
]
