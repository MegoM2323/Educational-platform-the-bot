from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .tutor_views import TutorStudentsViewSet

urlpatterns = [
    # Основные API endpoints для аутентификации
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Профиль пользователя
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Профили по ролям
    path('student-profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('teacher-profile/', views.TeacherProfileView.as_view(), name='teacher_profile'),
    path('tutor-profile/', views.TutorProfileView.as_view(), name='tutor_profile'),
    path('parent-profile/', views.ParentProfileView.as_view(), name='parent_profile'),
]

# Router for tutor endpoints
router = DefaultRouter()
router.register(r'tutor/students', TutorStudentsViewSet, basename='tutor-students')

urlpatterns += [
    path('', include(router.urls)),
]
