from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from payments.views import yookassa_webhook, check_payment_status
from core.media_views import serve_media_file, serve_media_file_download

urlpatterns = [
    path("admin/", admin.site.urls),

    # API endpoints
    path("api/auth/", include('accounts.urls')),
    path("api/profile/", include('accounts.profile_urls')),  # Profile endpoints (NEW - for frontend compatibility)
    path("api/admin/", include('accounts.urls')),  # Admin endpoints (profile management)
    path("api/admin/schedule/", include('scheduling.admin_urls')),  # Admin schedule management
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
    path("api/scheduling/", include('scheduling.urls')),  # Scheduling system

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
    path("yookassa-webhook/", yookassa_webhook, name="yookassa_webhook"),
    path("api/check-payment/", check_payment_status, name="check_payment_status"),

    # Media files serving (works in both development and production)
    # Все медиа файлы требуют авторизации
    re_path(r'^media/(?P<file_path>.*)$', serve_media_file, name='serve_media_file'),
    re_path(r'^api/media/download/(?P<file_path>.*)$', serve_media_file_download, name='serve_media_file_download'),
]
