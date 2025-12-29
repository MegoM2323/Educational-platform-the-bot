from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import student_dashboard_views
from . import teacher_dashboard_views
from . import parent_dashboard_views
from . import tutor_dashboard_views
from . import study_plan_views
from . import submission_file_views
from .subject_views import list_all_subjects
from .enrollment_views import (
    enroll_subject,
    unenroll_subject,
    my_enrollments,
    enrollment_status,
    teacher_students
)
from .bulk_operations_views import (
    bulk_assign_endpoint,
    bulk_unassign_endpoint,
    bulk_assign_class_endpoint,
    bulk_assign_materials_endpoint
)

router = DefaultRouter()
router.register(r'subjects', views.SubjectViewSet)
router.register(r'materials', views.MaterialViewSet)
router.register(r'progress', views.MaterialProgressViewSet)
router.register(r'comments', views.MaterialCommentViewSet)
router.register(r'submissions', views.MaterialSubmissionViewSet)
router.register(r'feedback', views.MaterialFeedbackViewSet)
router.register(r'submission-files', submission_file_views.SubmissionFileViewSet)

urlpatterns = [
    # ВАЖНО: пути НЕ должны начинаться с 'materials/', т.к. это уже в config/urls.py

    # Список всех предметов (для UI мультиселекта)
    path('subjects/all/', list_all_subjects, name='list-all-subjects'),

    # Subject Enrollment endpoints (T_MAT_006)
    path('subjects/<int:subject_id>/enroll/', enroll_subject, name='enroll-subject'),
    path('subjects/<int:subject_id>/unenroll/', unenroll_subject, name='unenroll-subject'),
    path('subjects/my-enrollments/', my_enrollments, name='my-enrollments'),
    path('subjects/<int:subject_id>/enrollment-status/', enrollment_status, name='enrollment-status'),
    path('teachers/<int:teacher_id>/students/', teacher_students, name='teacher-students-list'),

    # Student dashboard endpoints (MUST be before router to avoid conflicts)
    path('student/subjects/', student_dashboard_views.student_subjects, name='student-subjects'),
    path('student/', student_dashboard_views.student_dashboard, name='student-dashboard-materials'),
    path('student/assigned/', student_dashboard_views.student_assigned_materials, name='student-assigned-materials'),
    path('student/by-subject/', student_dashboard_views.student_materials_by_subject, name='student-materials-by-subject'),
    path('<int:material_id>/progress/', student_dashboard_views.update_material_progress, name='update-material-progress'),
    path('student/progress/', student_dashboard_views.student_progress_statistics, name='student-progress-statistics'),
    path('student/activity/', student_dashboard_views.student_recent_activity, name='student-recent-activity'),

    path('', include(router.urls)),
    
    # Student study plans endpoints
    path('student/study-plans/', student_dashboard_views.student_study_plans, name='student-study-plans'),
    path('student/study-plans/<int:plan_id>/', student_dashboard_views.student_study_plan_detail, name='student-study-plan-detail'),
    path('student/subjects/<int:subject_id>/study-plans/', student_dashboard_views.student_study_plans_by_subject, name='student-study-plans-by-subject'),
    
    # Student materials API endpoints
    path('student/list/', views.MaterialViewSet.as_view({'get': 'student_materials'}), name='student-materials'),
    path('<int:pk>/download/', views.MaterialViewSet.as_view({'get': 'download_file'}), name='material-download'),
    
    # Teacher dashboard endpoints
    path('teacher/', teacher_dashboard_views.teacher_dashboard, name='teacher-dashboard'),
    path('teacher/students/', teacher_dashboard_views.teacher_students, name='teacher-students'),
    path('teacher/', teacher_dashboard_views.teacher_materials, name='teacher-materials'),
    path('teacher/distribute/', teacher_dashboard_views.distribute_material, name='distribute-material'),
    path('teacher/students/<int:student_id>/subjects/', teacher_dashboard_views.teacher_student_subjects, name='teacher-student-subjects'),
    path('teacher/subjects/<int:subject_id>/students/', teacher_dashboard_views.subject_students, name='teacher-subject-students'),
    path('teacher/subjects/', teacher_dashboard_views.get_all_subjects, name='teacher-all-subjects'),
    path('teacher/all-students/', teacher_dashboard_views.teacher_all_students, name='teacher-all-students'),
    path('teacher/submissions/pending/', teacher_dashboard_views.pending_submissions, name='teacher-pending-submissions'),
    path('teacher/submissions/<int:submission_id>/feedback/', teacher_dashboard_views.submission_feedback, name='teacher-submission-feedback'),
    path('teacher/submissions/<int:submission_id>/status/', teacher_dashboard_views.update_submission_status, name='teacher-submission-status'),
    path('teacher/materials/<int:material_id>/assignments/', teacher_dashboard_views.material_assignments, name='teacher-material-assignments'),
    path('teacher/progress/', teacher_dashboard_views.student_progress_overview, name='teacher-progress-overview'),
    path('reports/teacher/create/', teacher_dashboard_views.create_student_report, name='create-student-report'),
    path('reports/teacher/', teacher_dashboard_views.teacher_reports, name='teacher-reports'),

    # Teacher study plans endpoints
    path('teacher/study-plans/', teacher_dashboard_views.teacher_study_plans, name='teacher-study-plans'),
    path('teacher/study-plans/<int:plan_id>/', teacher_dashboard_views.teacher_study_plan_detail, name='teacher-study-plan-detail'),
    path('teacher/study-plans/<int:plan_id>/send/', teacher_dashboard_views.send_study_plan, name='send-study-plan'),
    path('teacher/study-plans/<int:plan_id>/files/', teacher_dashboard_views.upload_study_plan_file, name='upload-study-plan-file'),
    path('teacher/study-plans/<int:plan_id>/files/<int:file_id>/', teacher_dashboard_views.delete_study_plan_file, name='delete-study-plan-file'),

    # AI Study Plan Generation endpoints
    path('study-plan/generate/', study_plan_views.generate_study_plan, name='generate-study-plan'),
    path('study-plan/generation/<int:generation_id>/', study_plan_views.generation_status, name='generation-status'),

    # Parent dashboard endpoints
    path('parent/', parent_dashboard_views.ParentDashboardView.as_view(), name='parent-dashboard'),
    path('parent/children/', parent_dashboard_views.ParentChildrenView.as_view(), name='parent-children'),
    path('parent/children/<int:child_id>/subjects/', parent_dashboard_views.get_child_subjects, name='child-subjects'),
    path('parent/children/<int:child_id>/progress/', parent_dashboard_views.get_child_progress, name='child-progress'),
    path('parent/children/<int:child_id>/teachers/', parent_dashboard_views.get_child_teachers, name='child-teachers'),
    path('parent/children/<int:child_id>/payments/', parent_dashboard_views.get_payment_status, name='child-payments'),
    path('parent/children/<int:child_id>/payment/<int:enrollment_id>/', parent_dashboard_views.initiate_payment, name='initiate-payment'),
    path('parent/payments/', parent_dashboard_views.parent_payments, name='parent-payments'),
    path('parent/payments/pending/', parent_dashboard_views.parent_pending_payments, name='parent-pending-payments'),
    path('parent/reports/', parent_dashboard_views.get_reports, name='parent-reports'),
    path('parent/reports/<int:child_id>/', parent_dashboard_views.get_reports, name='parent-child-reports'),
    path('parent/children/<int:child_id>/subscription/<int:enrollment_id>/cancel/', parent_dashboard_views.cancel_subscription, name='cancel-subscription'),

    # Tutor dashboard endpoints
    path('tutor/', tutor_dashboard_views.tutor_dashboard, name='tutor-dashboard'),
    path('tutor/students/', tutor_dashboard_views.tutor_students, name='tutor-students'),
    path('tutor/students/<int:student_id>/subjects/', tutor_dashboard_views.tutor_student_subjects, name='tutor-student-subjects'),
    path('tutor/students/<int:student_id>/progress/', tutor_dashboard_views.tutor_student_progress, name='tutor-student-progress'),
    path('tutor/students/<int:student_id>/schedule/', tutor_dashboard_views.tutor_student_schedule, name='tutor-student-schedule'),
    path('tutor/students/assign-subject/', tutor_dashboard_views.tutor_assign_subject, name='tutor-assign-subject'),
    path('tutor/reports/create/', tutor_dashboard_views.tutor_create_report, name='tutor-create-report'),
    path('tutor/reports/', tutor_dashboard_views.tutor_reports, name='tutor-reports'),

    # Bulk operations endpoints (T_MAT_004)
    path('bulk-assign/', bulk_assign_endpoint, name='bulk-assign'),
    path('bulk-unassign/', bulk_unassign_endpoint, name='bulk-unassign'),
    path('bulk-assign-class/', bulk_assign_class_endpoint, name='bulk-assign-class'),
    path('bulk-assign-materials/', bulk_assign_materials_endpoint, name='bulk-assign-materials'),

    # Submission file upload endpoints (T_MAT_008)
    path('<int:pk>/submit-files/',
         submission_file_views.MaterialSubmitFilesViewSet.as_view({'post': 'submit_files'}),
         name='submit-files'),
    path('submission-files/<int:submission_id>/',
         submission_file_views.MaterialSubmitFilesViewSet.as_view({'get': 'get_submission_files'}),
         name='get-submission-files'),
    path('submission-files/<int:file_id>/delete/',
         submission_file_views.MaterialSubmitFilesViewSet.as_view({'delete': 'delete_submission_file'}),
         name='delete-submission-file'),
]
