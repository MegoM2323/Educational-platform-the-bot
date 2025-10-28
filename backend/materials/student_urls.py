from django.urls import path

from . import student_api_views as views


urlpatterns = [
    # Subjects and teachers
    path("subjects/", views.list_student_subjects, name="student-subjects"),
    path("subjects/<int:subject_id>/materials/", views.list_subject_materials, name="student-subject-materials"),
    path("subjects/<int:subject_id>/teacher/", views.get_subject_teacher, name="student-subject-teacher"),
    
    # Submissions and feedback
    path("materials/<int:material_id>/submissions/", views.submit_material_submission, name="student-submit-material"),
    path("submissions/", views.list_student_submissions, name="student-submissions"),
    path("submissions/<int:submission_id>/feedback/", views.get_submission_feedback, name="student-submission-feedback"),
]


