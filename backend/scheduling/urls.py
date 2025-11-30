"""
URL configuration for scheduling app.

Provides routing for all lesson management endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from scheduling.views import LessonViewSet

# Create router for viewsets
router = DefaultRouter()
router.register('lessons', LessonViewSet, basename='lesson')

# Include router URLs
urlpatterns = [
    path('', include(router.urls)),
]
