"""
Admin-only URL configuration for scheduling.

Provides routing for admin schedule management endpoints.
All endpoints require IsAdminUser permission.
"""

from django.urls import path

from scheduling.admin_views import (
    admin_schedule_view,
    admin_schedule_stats_view,
    admin_schedule_filters_view
)

urlpatterns = [
    # GET /api/admin/schedule/lessons/ - List all lessons with filtering
    path('lessons/', admin_schedule_view, name='admin-schedule-lessons'),

    # GET /api/admin/schedule/stats/ - Schedule statistics
    path('stats/', admin_schedule_stats_view, name='admin-schedule-stats'),

    # GET /api/admin/schedule/filters/ - Filter options (teachers, subjects)
    path('filters/', admin_schedule_filters_view, name='admin-schedule-filters'),
]
