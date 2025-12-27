"""
URL configuration for scheduling app.

Provides routing for all lesson management endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from scheduling.views import LessonViewSet
from scheduling.admin_views import (
    admin_schedule_view,
    admin_schedule_stats_view,
    admin_schedule_filters_view
)
from scheduling.tutor_views import (
    get_student_schedule,
    get_all_student_schedules
)

# Create router for viewsets
router = DefaultRouter()
router.register('lessons', LessonViewSet, basename='lesson')

# Include router URLs
urlpatterns = [
    path('', include(router.urls)),
    # Admin endpoints
    path('admin/schedule/', admin_schedule_view, name='admin-schedule'),
    path('admin/schedule/stats/', admin_schedule_stats_view, name='admin-schedule-stats'),
    path('admin/schedule/filters/', admin_schedule_filters_view, name='admin-schedule-filters'),
    # Tutor endpoints
    path('tutor/students/<int:student_id>/schedule/', get_student_schedule, name='tutor-student-schedule'),
    path('tutor/schedule/', get_all_student_schedules, name='tutor-all-schedules'),
]
