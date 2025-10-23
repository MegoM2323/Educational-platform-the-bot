from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация (Django)
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Аутентификация (Supabase)
    path('supabase/register/', views.supabase_register, name='supabase_register'),
    path('supabase/login/', views.supabase_login, name='supabase_login'),
    path('supabase/logout/', views.supabase_logout, name='supabase_logout'),
    path('supabase/profile/', views.supabase_profile, name='supabase_profile'),
    path('supabase/profile/update/', views.supabase_update_profile, name='supabase_update_profile'),
    
    # Профиль пользователя (Django)
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Профили по ролям
    path('student-profile/', views.StudentProfileView.as_view(), name='student_profile'),
    path('teacher-profile/', views.TeacherProfileView.as_view(), name='teacher_profile'),
    path('tutor-profile/', views.TutorProfileView.as_view(), name='tutor_profile'),
    path('parent-profile/', views.ParentProfileView.as_view(), name='parent_profile'),
]
