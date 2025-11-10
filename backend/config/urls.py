from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from payments.views import yookassa_webhook, check_payment_status

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # API endpoints
    path("api/auth/", include('accounts.urls')),
    path("api/auth/tutor/", include('accounts.urls')),
    path("api/tutor/", include('accounts.urls')),  # Tutor endpoints
    path("api/materials/", include('materials.urls')),
    path("api/student/", include('materials.student_urls')),
    path("api/assignments/", include('assignments.urls')),
    path("api/chat/", include('chat.urls')),
    path("api/reports/", include('reports.urls')),
    path("api/notifications/", include('notifications.urls')),
    path("api/payments/", include('payments.api_urls')),
    path("api/applications/", include('applications.urls')),
    path("api/dashboard/", include('materials.urls')),  # Dashboard endpoints
    path("api/teacher/", include('materials.teacher_urls')),
    path("api/system/", include('core.urls')),  # System monitoring and management
    
    # Compatibility aliases (non-API prefixed) used by tests and legacy frontend
    path("auth/", include('accounts.urls')),
    path("materials/", include('materials.urls')),
    path("teacher/", include('materials.teacher_urls')),
    path("student/", include('materials.student_urls')),
    path("chat/", include('chat.urls')),
    path("reports/", include('reports.urls')),
    path("notifications/", include('notifications.urls')),
    path("dashboard/", include('materials.urls')),
    
    # Payment webhook (required for YooKassa)
    path("yookassa-webhook", yookassa_webhook, name="yookassa_webhook"),
    path("api/check-payment/", check_payment_status, name="check_payment_status"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
