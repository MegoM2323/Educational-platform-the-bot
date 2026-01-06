from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .tutor_views import TutorStudentsViewSet, list_teachers
from .staff_views import (
    list_staff,
    create_staff,
    list_students,
    get_student_detail,
    update_teacher_subjects,
    update_user,
    update_student_profile,
    update_teacher_profile,
    update_tutor_profile,
    update_parent_profile,
    reset_password,
    delete_user,
    create_user_with_profile,
    create_student,
    create_parent,
    assign_parent_to_students,
    assign_students_to_teacher,
    list_parents,
    reactivate_user,
    UserManagementView,
)
from .profile_views import (
    StudentProfileView,
    TeacherProfileView,
    TutorProfileView,
    ParentProfileView,
    AdminTeacherProfileEditView,
    AdminTutorProfileEditView,
    AdminUserProfileView,
    AdminUserFullInfoView,
    NotificationSettingsView,
)
from .admin_stats_views import AdminUserStatsView
from .bulk_views import BulkUserOperationsViewSet
from .telegram_link_views import (
    GenerateTelegramLinkView,
    ConfirmTelegramLinkView,
    UnlinkTelegramView,
    TelegramStatusView,
)
from .telegram_webhook_views import TelegramWebhookView

# Router for ViewSets
router = DefaultRouter()
# Tutor-specific endpoints через роутер (будет доступен как /api/accounts/my-students/ и /api/accounts/students/)
router.register(r"students", TutorStudentsViewSet, basename="tutor-students")
router.register(r"my-students", TutorStudentsViewSet, basename="tutor-my-students")
# Bulk operations endpoints
router.register(r"bulk-operations", BulkUserOperationsViewSet, basename="bulk-operations")

urlpatterns = [
    # Основные API endpoints для аутентификации (должны быть ПЕРЕД роутером)
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("refresh/", views.refresh_token_view, name="refresh_token"),
    path("session-status/", views.session_status, name="session_status"),  # Debug endpoint
    # Профиль пользователя (общий endpoint)
    path(
        "me/", views.CurrentUserProfileView.as_view(), name="current_user_me"
    ),  # Алиас для фронтенда
    path("profile/", views.CurrentUserProfileView.as_view(), name="current_user_profile"),
    path("profile/update/", views.update_profile, name="update_profile"),
    path("change-password/", views.change_password, name="change_password"),
    # Profile endpoints по ролям (NEW - для фронтенда)
    path("profile/student/", StudentProfileView.as_view(), name="student_profile_api"),
    path("profile/teacher/", TeacherProfileView.as_view(), name="teacher_profile_api"),
    path("profile/tutor/", TutorProfileView.as_view(), name="tutor_profile_api"),
    path("profile/parent/", ParentProfileView.as_view(), name="parent_profile_api"),
    # Notification settings endpoint
    path(
        "notification-settings/",
        NotificationSettingsView.as_view(),
        name="notification_settings_api",
    ),
    # Список пользователей + создание (для тьюторов и администраторов)
    path(
        "users/", UserManagementView.as_view(), name="user_management"
    ),  # GET: список, POST: создание
    # Deprecated: POST /api/accounts/users/create/ использует старый endpoint, используйте POST /api/accounts/users/ вместо
    path("users/create/", create_user_with_profile, name="admin_create_user_deprecated"),
    # Admin-only staff management
    path("staff/", list_staff, name="staff_list"),  # ?role=teacher|tutor
    path("staff/create/", create_staff, name="staff_create"),
    path(
        "staff/teachers/<int:teacher_id>/subjects/",
        update_teacher_subjects,
        name="update_teacher_subjects",
    ),
    # Router URLs (ViewSet endpoints) - ПРИОРИТЕТ перед static paths
    path("", include(router.urls)),
    # Admin-only student management (должны быть ПОСЛЕ router чтобы router.students был приоритетом)
    path("students/", list_students, name="admin_list_students"),  # GET - список студентов
    path(
        "students/create/", create_student, name="admin_create_student"
    ),  # POST - создание студента (legacy)
    path("students/<int:student_id>/", get_student_detail, name="admin_student_detail"),
    # Admin-only parent management
    path("parents/", list_parents, name="admin_list_parents"),  # GET - список родителей
    path(
        "parents/create/", create_parent, name="admin_create_parent"
    ),  # POST - создание родителя (legacy)
    path(
        "assign-parent/", assign_parent_to_students, name="admin_assign_parent"
    ),  # POST - назначение родителя
    path(
        "teachers/<int:teacher_id>/assign-students/",
        assign_students_to_teacher,
        name="admin_assign_students_to_teacher",
    ),  # POST - назначение студентов учителю
    # Admin-only user management (CRUD)
    path("users/<int:user_id>/", update_user, name="admin_update_user"),
    path(
        "users/<int:user_id>/reset-password/",
        reset_password,
        name="admin_reset_password",
    ),
    path("users/<int:user_id>/delete/", delete_user, name="admin_delete_user"),
    path("users/<int:user_id>/reactivate/", reactivate_user, name="admin_reactivate_user"),
    # Admin-only profile management
    path(
        "students/<int:student_id>/profile/",
        update_student_profile,
        name="admin_update_student_profile",
    ),
    path(
        "teachers/<int:teacher_id>/profile/",
        update_teacher_profile,
        name="admin_update_teacher_profile",
    ),
    path(
        "tutors/<int:tutor_id>/profile/",
        update_tutor_profile,
        name="admin_update_tutor_profile",
    ),
    path(
        "parents/<int:parent_id>/profile/",
        update_parent_profile,
        name="admin_update_parent_profile",
    ),
    # Admin-only profile editing endpoints (via admin API)
    path(
        "teachers/<int:teacher_id>/",
        AdminTeacherProfileEditView.as_view(),
        name="admin_edit_teacher_profile",
    ),
    path(
        "tutors/<int:tutor_id>/",
        AdminTutorProfileEditView.as_view(),
        name="admin_edit_tutor_profile",
    ),
    # Teachers list endpoint (public endpoint)
    path("teachers/", list_teachers, name="list_teachers"),
    # Tutor-specific endpoints
    path("tutor/teachers/", list_teachers, name="tutor_list_teachers"),
    # Admin statistics
    path("stats/users/", AdminUserStatsView.as_view(), name="admin_user_stats"),
    # Admin user profile viewing (new endpoints for T016)
    path(
        "admin/users/<int:user_id>/profile/",
        AdminUserProfileView.as_view(),
        name="admin_user_profile",
    ),
    path(
        "admin/users/<int:user_id>/full-info/",
        AdminUserFullInfoView.as_view(),
        name="admin_user_full_info",
    ),
    # GDPR Data Export endpoints
    path("export/", views.export_user_data, name="export_user_data"),
    path("export/status/<str:job_id>/", views.export_status, name="export_status"),
    path("export/download/<str:token>/", views.download_export, name="download_export"),
    # Telegram binding endpoints
    path(
        "profile/telegram/generate-link/",
        GenerateTelegramLinkView.as_view(),
        name="telegram_generate_link",
    ),
    path(
        "profile/telegram/confirm/",
        ConfirmTelegramLinkView.as_view(),
        name="telegram_confirm_link",
    ),
    path("profile/telegram/unlink/", UnlinkTelegramView.as_view(), name="telegram_unlink"),
    path("profile/telegram/status/", TelegramStatusView.as_view(), name="telegram_status"),
    # Telegram webhook endpoint
    path(
        "telegram/webhook/<str:secret>/",
        TelegramWebhookView.as_view(),
        name="telegram_webhook",
    ),
]
