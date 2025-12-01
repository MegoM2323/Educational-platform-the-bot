from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .tutor_views import TutorStudentsViewSet, list_teachers
from .staff_views import (
    list_staff, create_staff, list_students, get_student_detail,
    update_teacher_subjects, update_user, update_student_profile,
    update_teacher_profile, update_tutor_profile, update_parent_profile,
    reset_password, delete_user, create_user_with_profile, create_student,
    create_parent, assign_parent_to_students, list_parents, reactivate_user
)
from .profile_views import (
    StudentProfileView, TeacherProfileView, TutorProfileView, ParentProfileView,
    AdminTeacherProfileEditView, AdminTutorProfileEditView
)

# Router for ViewSets
router = DefaultRouter()
# Tutor-specific endpoints через роутер
router.register(r'tutor/students', TutorStudentsViewSet, basename='tutor-students')

urlpatterns = [
    # Основные API endpoints для аутентификации (должны быть ПЕРЕД роутером)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', views.refresh_token_view, name='refresh_token'),

    # Профиль пользователя (общий endpoint)
    path('profile/', views.CurrentUserProfileView.as_view(), name='current_user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),

    # Profile endpoints по ролям (NEW - для фронтенда)
    path('profile/student/', StudentProfileView.as_view(), name='student_profile_api'),
    path('profile/teacher/', TeacherProfileView.as_view(), name='teacher_profile_api'),
    path('profile/tutor/', TutorProfileView.as_view(), name='tutor_profile_api'),
    path('profile/parent/', ParentProfileView.as_view(), name='parent_profile_api'),

    # Список пользователей (для тьюторов и администраторов)
    path('users/', views.list_users, name='list_users'),  # ?role=teacher|tutor|student|parent

    # Профили по ролям
    path('student-profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('teacher-profile/', views.TeacherProfileView.as_view(), name='teacher_profile'),
    path('tutor-profile/', views.TutorProfileView.as_view(), name='tutor_profile'),
    path('parent-profile/', views.ParentProfileView.as_view(), name='parent_profile'),

    # Admin-only staff management
    path('staff/', list_staff, name='staff_list'),  # ?role=teacher|tutor
    path('staff/create/', create_staff, name='staff_create'),
    path('staff/teachers/<int:teacher_id>/subjects/', update_teacher_subjects, name='update_teacher_subjects'),

    # Admin-only student management (ВАЖНО: должны быть ПЕРЕД роутером)
    path('students/', list_students, name='admin_list_students'),  # GET - список студентов
    path('students/create/', create_student, name='admin_create_student'),  # POST - создание студента (legacy)
    path('students/<int:student_id>/', get_student_detail, name='admin_student_detail'),

    # Admin-only parent management
    path('parents/', list_parents, name='admin_list_parents'),  # GET - список родителей
    path('parents/create/', create_parent, name='admin_create_parent'),  # POST - создание родителя (legacy)
    path('assign-parent/', assign_parent_to_students, name='admin_assign_parent'),  # POST - назначение родителя

    # Router URLs должны быть ПОСЛЕ специфичных URL
    path('', include(router.urls)),

    # Admin-only user management (CRUD)
    path('users/<int:user_id>/', update_user, name='admin_update_user'),
    path('users/<int:user_id>/reset-password/', reset_password, name='admin_reset_password'),
    path('users/<int:user_id>/delete/', delete_user, name='admin_delete_user'),
    path('users/<int:user_id>/reactivate/', reactivate_user, name='admin_reactivate_user'),
    path('users/create/', create_user_with_profile, name='admin_create_user'),

    # Admin-only profile management
    path('students/<int:student_id>/profile/', update_student_profile, name='admin_update_student_profile'),
    path('teachers/<int:teacher_id>/profile/', update_teacher_profile, name='admin_update_teacher_profile'),
    path('tutors/<int:tutor_id>/profile/', update_tutor_profile, name='admin_update_tutor_profile'),
    path('parents/<int:parent_id>/profile/', update_parent_profile, name='admin_update_parent_profile'),

    # Admin-only profile editing endpoints (via admin API)
    path('teachers/<int:teacher_id>/', AdminTeacherProfileEditView.as_view(), name='admin_edit_teacher_profile'),
    path('tutors/<int:tutor_id>/', AdminTutorProfileEditView.as_view(), name='admin_edit_tutor_profile'),

    # Tutor-specific endpoints
    path('tutor/teachers/', list_teachers, name='tutor_list_teachers'),
]
