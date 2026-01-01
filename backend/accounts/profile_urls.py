"""
Profile-specific URL patterns.
These are mounted at /api/profile/ for frontend compatibility.
"""

from django.urls import path
from .profile_views import (
    StudentProfileView,
    TeacherProfileView,
    TutorProfileView,
    ParentProfileView,
    CurrentUserProfileView,
    ProfileReactivationView,
    NotificationSettingsView,
    TeacherListView,
    TeacherDetailView,
)
from .telegram_link_views import (
    GenerateTelegramLinkView,
    ConfirmTelegramLinkView,
    UnlinkTelegramView,
    TelegramStatusView,
)
from .telegram_webhook_views import TelegramWebhookView

urlpatterns = [
    # Universal endpoint - returns current user profile based on their role
    path("me/", CurrentUserProfileView.as_view(), name="profile_me_api"),
    # Profile endpoints by role - these are the NEW endpoints for frontend
    path("student/", StudentProfileView.as_view(), name="profile_student_api"),
    path("teacher/", TeacherProfileView.as_view(), name="profile_teacher_api"),
    path("tutor/", TutorProfileView.as_view(), name="profile_tutor_api"),
    path("parent/", ParentProfileView.as_view(), name="profile_parent_api"),
    # Notification settings endpoint
    path(
        "notification-settings/",
        NotificationSettingsView.as_view(),
        name="notification_settings_api",
    ),
    # Profile reactivation endpoint
    path("reactivate/", ProfileReactivationView.as_view(), name="profile_reactivate"),
    # Teachers list endpoints (M1: Teachers list endpoint)
    path("teachers/", TeacherListView.as_view(), name="teachers_list"),
    path("teachers/<int:teacher_id>/", TeacherDetailView.as_view(), name="teacher_detail"),
    # Telegram linking endpoints
    path(
        "telegram/generate-link/",
        GenerateTelegramLinkView.as_view(),
        name="telegram-generate-link",
    ),
    path("telegram/confirm/", ConfirmTelegramLinkView.as_view(), name="telegram-confirm"),
    path("telegram/unlink/", UnlinkTelegramView.as_view(), name="telegram-unlink"),
    path("telegram/status/", TelegramStatusView.as_view(), name="telegram-status"),
    # Telegram webhook (alternative to polling)
    path(
        "telegram/webhook/<str:secret>/",
        TelegramWebhookView.as_view(),
        name="telegram-webhook",
    ),
]
