"""
Profile-specific URL patterns.
These are mounted at /api/profile/ for frontend compatibility.
"""

from django.urls import path
from .profile_views import (
    StudentProfileView, TeacherProfileView, TutorProfileView, CurrentUserProfileView,
    ProfileReactivationView
)

urlpatterns = [
    # Universal endpoint - returns current user profile based on their role
    path('me/', CurrentUserProfileView.as_view(), name='profile_me_api'),

    # Profile endpoints by role - these are the NEW endpoints for frontend
    path('student/', StudentProfileView.as_view(), name='profile_student_api'),
    path('teacher/', TeacherProfileView.as_view(), name='profile_teacher_api'),
    path('tutor/', TutorProfileView.as_view(), name='profile_tutor_api'),

    # Profile reactivation endpoint
    path('reactivate/', ProfileReactivationView.as_view(), name='profile_reactivate'),
]