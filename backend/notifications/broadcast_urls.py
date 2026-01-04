"""
URL routing для broadcast endpoints (используется в admin панели)
"""
try:
    from django.urls import path
    from rest_framework.routers import DefaultRouter
    from . import broadcast_views

    router = DefaultRouter()
    router.register(r'', broadcast_views.BroadcastViewSet, basename='broadcast')
    urlpatterns = router.urls
except (ImportError, ModuleNotFoundError):
    # During migrations, models aren't ready yet - return empty patterns
    urlpatterns = []
