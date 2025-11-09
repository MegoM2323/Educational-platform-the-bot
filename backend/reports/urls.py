from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet)
router.register(r'templates', views.ReportTemplateViewSet)
router.register(r'analytics', views.AnalyticsDataViewSet)
router.register(r'schedules', views.ReportScheduleViewSet)
router.register(r'stats', views.ReportStatsViewSet, basename='stats')
router.register(r'student-reports', views.StudentReportViewSet, basename='student-reports')
router.register(r'tutor-weekly-reports', views.TutorWeeklyReportViewSet, basename='tutor-weekly-reports')
router.register(r'teacher-weekly-reports', views.TeacherWeeklyReportViewSet, basename='teacher-weekly-reports')

urlpatterns = [
    path('', include(router.urls)),
]
