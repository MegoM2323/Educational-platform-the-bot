"""
URL routing для broadcast endpoints (используется в admin панели)
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import broadcast_views

# Используем ViewSet с router
router = DefaultRouter()
router.register(r'', broadcast_views.BroadcastViewSet, basename='broadcast')

urlpatterns = router.urls
