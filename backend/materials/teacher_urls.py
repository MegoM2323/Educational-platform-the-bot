from django.urls import path
from . import teacher_dashboard_views as v


urlpatterns = [
    path('dashboard/', v.teacher_dashboard, name='teacher-dashboard'),
    path('students/', v.teacher_students, name='teacher-students'),
    path('students/<int:student_id>/subjects/', v.teacher_student_subjects, name='teacher-student-subjects'),
    path('subjects/<int:subject_id>/students/', v.subject_students, name='teacher-subject-students'),

    # Materials
    path('materials/', v.teacher_materials, name='teacher-materials'),
    path('materials/<int:material_id>/assignments/', v.material_assignments, name='teacher-material-assignments'),

    # Submissions review
    path('submissions/pending/', v.pending_submissions, name='teacher-pending-submissions'),
    path('submissions/<int:submission_id>/feedback/', v.submission_feedback, name='teacher-submission-feedback'),
    path('submissions/<int:submission_id>/status/', v.update_submission_status, name='teacher-submission-status'),

    # Reports & progress
    path('progress/', v.student_progress_overview, name='teacher-progress-overview'),
    path('reports/', v.teacher_reports, name='teacher-reports'),
    path('reports/create/', v.create_student_report, name='create-student-report'),
    path('general-chat/', v.teacher_general_chat, name='teacher-general-chat'),
]


