from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .tutor_views import TutorStudentsViewSet, list_teachers
from .staff_views import list_staff, create_staff

# Router for tutor endpoints - должен быть первым, чтобы избежать конфликтов
router = DefaultRouter()
router.register(r'students', TutorStudentsViewSet, basename='tutor-students')

urlpatterns = [
    # Router URLs должны быть первыми
    path('', include(router.urls)),
    
    # Основные API endpoints для аутентификации
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh/', views.refresh_token_view, name='refresh_token'),

    # Профиль пользователя
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
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
    
    # Tutor-specific endpoints
    path('tutor/teachers/', list_teachers, name='tutor_list_teachers'),
]
