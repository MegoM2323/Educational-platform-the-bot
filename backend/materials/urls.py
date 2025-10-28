from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import student_dashboard_views
from . import teacher_dashboard_views
from . import parent_dashboard_views

router = DefaultRouter()
router.register(r'subjects', views.SubjectViewSet)
router.register(r'materials', views.MaterialViewSet)
router.register(r'progress', views.MaterialProgressViewSet)
router.register(r'comments', views.MaterialCommentViewSet)
router.register(r'submissions', views.MaterialSubmissionViewSet)
router.register(r'feedback', views.MaterialFeedbackViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Student dashboard endpoints
    path('student/', student_dashboard_views.student_dashboard, name='student-dashboard'),
    path('materials/student/assigned/', student_dashboard_views.student_assigned_materials, name='student-assigned-materials'),
    path('materials/student/by-subject/', student_dashboard_views.student_materials_by_subject, name='student-materials-by-subject'),
    path('dashboard/student/progress/', student_dashboard_views.student_progress_statistics, name='student-progress-statistics'),
    path('dashboard/student/activity/', student_dashboard_views.student_recent_activity, name='student-recent-activity'),
    path('dashboard/student/general-chat/', student_dashboard_views.student_general_chat, name='student-general-chat'),
    path('materials/<int:material_id>/progress/', student_dashboard_views.update_material_progress, name='update-material-progress'),
    
    # Student materials API endpoints
    path('materials/student/', views.MaterialViewSet.as_view({'get': 'student_materials'}), name='student-materials'),
    path('materials/<int:pk>/download/', views.MaterialViewSet.as_view({'get': 'download_file'}), name='material-download'),
    
    # Teacher dashboard endpoints
    path('dashboard/teacher/', teacher_dashboard_views.teacher_dashboard, name='teacher-dashboard'),
    path('dashboard/teacher/students/', teacher_dashboard_views.teacher_students, name='teacher-students'),
    path('materials/teacher/', teacher_dashboard_views.teacher_materials, name='teacher-materials'),
    path('materials/teacher/distribute/', teacher_dashboard_views.distribute_material, name='distribute-material'),
    path('teacher/students/<int:student_id>/subjects/', teacher_dashboard_views.teacher_student_subjects, name='teacher-student-subjects'),
    path('teacher/subjects/<int:subject_id>/students/', teacher_dashboard_views.subject_students, name='teacher-subject-students'),
    path('teacher/submissions/pending/', teacher_dashboard_views.pending_submissions, name='teacher-pending-submissions'),
    path('teacher/submissions/<int:submission_id>/feedback/', teacher_dashboard_views.submission_feedback, name='teacher-submission-feedback'),
    path('teacher/submissions/<int:submission_id>/status/', teacher_dashboard_views.update_submission_status, name='teacher-submission-status'),
    path('teacher/materials/<int:material_id>/assignments/', teacher_dashboard_views.material_assignments, name='teacher-material-assignments'),
    path('dashboard/teacher/progress/', teacher_dashboard_views.student_progress_overview, name='teacher-progress-overview'),
    path('reports/teacher/create/', teacher_dashboard_views.create_student_report, name='create-student-report'),
    path('reports/teacher/', teacher_dashboard_views.teacher_reports, name='teacher-reports'),
    path('dashboard/teacher/general-chat/', teacher_dashboard_views.teacher_general_chat, name='teacher-general-chat'),
    
    # Parent dashboard endpoints
    path('dashboard/parent/', parent_dashboard_views.ParentDashboardView.as_view(), name='parent-dashboard'),
    path('dashboard/parent/children/', parent_dashboard_views.ParentChildrenView.as_view(), name='parent-children'),
    path('dashboard/parent/children/<int:child_id>/subjects/', parent_dashboard_views.get_child_subjects, name='child-subjects'),
    path('dashboard/parent/children/<int:child_id>/progress/', parent_dashboard_views.get_child_progress, name='child-progress'),
    path('dashboard/parent/children/<int:child_id>/teachers/', parent_dashboard_views.get_child_teachers, name='child-teachers'),
    path('dashboard/parent/children/<int:child_id>/payments/', parent_dashboard_views.get_payment_status, name='child-payments'),
    path('dashboard/parent/children/<int:child_id>/payment/<int:subject_id>/', parent_dashboard_views.initiate_payment, name='initiate-payment'),
    path('dashboard/parent/payments/', parent_dashboard_views.parent_payments, name='parent-payments'),
    path('dashboard/parent/payments/pending/', parent_dashboard_views.parent_pending_payments, name='parent-pending-payments'),
    path('dashboard/parent/reports/', parent_dashboard_views.get_reports, name='parent-reports'),
    path('dashboard/parent/reports/<int:child_id>/', parent_dashboard_views.get_reports, name='parent-child-reports'),
]
