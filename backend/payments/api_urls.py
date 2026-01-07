from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .health_views import health_check

router = DefaultRouter()
router.register(r"payments", views.PaymentViewSet)

urlpatterns = [
    path("initiate/", views.initiate_parent_payment, name="initiate_parent_payment"),
    path("", include(router.urls)),
    path("yookassa-webhook/", views.yookassa_webhook, name="yookassa_webhook"),
    path("check-payment/", views.check_payment_status, name="check_payment_status"),
    path("health/", health_check, name="health_check"),
]
