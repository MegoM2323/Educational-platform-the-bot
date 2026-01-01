from django.urls import path

from . import student_api_views as views
from . import student_dashboard_views


urlpatterns = [
    # Subjects and teachers
    path("subjects/", views.list_student_subjects, name="student-subjects"),
    path("subjects/<int:subject_id>/materials/", views.list_subject_materials, name="student-subject-materials"),
    path("subjects/<int:subject_id>/teacher/", views.get_subject_teacher, name="student-subject-teacher"),
    # Submissions and feedback
    path("materials/<int:material_id>/submissions/", views.submit_material_submission, name="student-submit-material"),
    path("submissions/", views.list_student_submissions, name="student-submissions"),
    path(
        "submissions/<int:submission_id>/feedback/", views.get_submission_feedback, name="student-submission-feedback"
    ),
    # Progress
    path("progress/", views.get_student_progress, name="student-progress"),
    # Study plans
    path("study-plans/", student_dashboard_views.student_study_plans, name="student-study-plans"),
    path(
        "study-plans/<int:plan_id>/",
        student_dashboard_views.student_study_plan_detail,
        name="student-study-plan-detail",
    ),
    path(
        "subjects/<int:subject_id>/study-plans/",
        student_dashboard_views.student_study_plans_by_subject,
        name="student-study-plans-by-subject",
    ),
]
