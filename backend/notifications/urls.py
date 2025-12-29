from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .broadcast_views import BroadcastViewSet

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet)
router.register(r'templates', views.NotificationTemplateViewSet)
router.register(r'settings', views.NotificationSettingsViewSet)
router.register(r'queue', views.NotificationQueueViewSet)
router.register(r'broadcasts', BroadcastViewSet, basename='broadcast')
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/metrics/', views.AnalyticsViewSet.as_view({'get': 'metrics'}), name='analytics-metrics'),
    path('analytics/performance/', views.AnalyticsViewSet.as_view({'get': 'performance'}), name='analytics-performance'),
    path('analytics/top-types/', views.AnalyticsViewSet.as_view({'get': 'top_types'}), name='analytics-top-types'),
    path('analytics/track-click/', views.AnalyticsViewSet.as_view({'post': 'track_click'}), name='analytics-track-click'),
    path('unsubscribe/<str:token>/', views.UnsubscribeView.as_view(), name='unsubscribe'),
]
