from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .custom_report_views import CustomReportViewSet, ReportTemplateViewSet as CustomReportTemplateViewSet
from reports.api import analytics as analytics_api

router = DefaultRouter()
router.register(r'reports', views.ReportViewSet)
router.register(r'templates', views.ReportTemplateViewSet)
router.register(r'custom-reports', CustomReportViewSet, basename='custom-reports')
router.register(r'custom-templates', CustomReportTemplateViewSet, basename='custom-templates')
router.register(r'analytics-data', views.AnalyticsDataViewSet)  # Renamed from 'analytics'
router.register(r'schedules', views.ReportScheduleViewSet)
router.register(r'stats', views.ReportStatsViewSet, basename='stats')
router.register(r'student-reports', views.StudentReportViewSet, basename='student-reports')
router.register(r'tutor-weekly-reports', views.TutorWeeklyReportViewSet, basename='tutor-weekly-reports')
router.register(r'teacher-weekly-reports', views.TeacherWeeklyReportViewSet, basename='teacher-weekly-reports')
router.register(r'parent-preferences', views.ParentReportPreferenceViewSet, basename='parent-preferences')

# Analytics API endpoints
analytics_router = DefaultRouter()
analytics_router.register(r'analytics/dashboard', analytics_api.DashboardAnalyticsViewSet, basename='analytics-dashboard')
analytics_router.register(r'analytics/students', analytics_api.StudentAnalyticsViewSet, basename='analytics-students')
analytics_router.register(r'analytics/assignments', analytics_api.AssignmentAnalyticsViewSet, basename='analytics-assignments')
analytics_router.register(r'analytics/attendance', analytics_api.AttendanceAnalyticsViewSet, basename='analytics-attendance')
analytics_router.register(r'analytics/engagement', analytics_api.EngagementAnalyticsViewSet, basename='analytics-engagement')
analytics_router.register(r'analytics/progress', analytics_api.ProgressAnalyticsViewSet, basename='analytics-progress')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(analytics_router.urls)),
]
