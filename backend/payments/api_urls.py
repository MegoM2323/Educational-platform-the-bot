from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .health_views import health_check

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health_check, name='health_check'),
]
