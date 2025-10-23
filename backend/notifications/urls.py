from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet)
router.register(r'templates', views.NotificationTemplateViewSet)
router.register(r'settings', views.NotificationSettingsViewSet)
router.register(r'queue', views.NotificationQueueViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
