from django.contrib import admin
from django.urls import path, include
from payments.views import pay_page, yookassa_webhook, pay_success, pay_fail, check_payment_status

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # API endpoints
    path("api/auth/", include('accounts.urls')),
    path("api/materials/", include('materials.urls')),
    path("api/assignments/", include('assignments.urls')),
    path("api/chat/", include('chat.urls')),
    path("api/reports/", include('reports.urls')),
    path("api/notifications/", include('notifications.urls')),
    path("api/payments/", include('payments.api_urls')),
    path("api/applications/", include('applications.urls')),
    
    # Legacy payment endpoints
    path("", pay_page, name="pay_page"),
    path("yookassa-webhook", yookassa_webhook, name="yookassa_webhook"),
    path("payments/success/", pay_success, name="payments_success"),
    path("payments/fail/", pay_fail, name="payments_fail"),
    path("api/check-payment/", check_payment_status, name="check_payment_status"),
]
