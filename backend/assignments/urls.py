from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views_plagiarism import SubmissionPlagiarismViewSet, plagiarism_webhook

router = DefaultRouter()
router.register(r"", views.AssignmentViewSet, basename="assignment")
router.register(r"submissions", views.AssignmentSubmissionViewSet, basename="submission")
router.register(r"questions", views.AssignmentQuestionViewSet, basename="question")
router.register(r"answers", views.AssignmentAnswerViewSet, basename="answer")
router.register(r"comment-templates", views.CommentTemplateViewSet, basename="comment-template")
router.register(r"peer-assignments", views.PeerReviewAssignmentViewSet, basename="peer-assignment")
router.register(r"peer-reviews", views.PeerReviewViewSet, basename="peer-review")
router.register(r"attempts", views.AssignmentAttemptViewSet, basename="attempt")

urlpatterns = [
    # List-level actions for assignments (must come before router patterns)
    path(
        "assign/",
        views.AssignmentViewSet.as_view({"post": "assign"}),
        name="assignment-assign",
    ),
    path(
        "grading-rubric/",
        views.AssignmentViewSet.as_view({"post": "grading_rubric"}),
        name="assignment-grading-rubric",
    ),
    path(
        "apply-template/",
        views.AssignmentViewSet.as_view({"post": "apply_template"}),
        name="assignment-apply-template",
    ),
    # List actions for submissions and questions (before router to avoid conflicts)
    path(
        "submissions/",
        views.AssignmentSubmissionViewSet.as_view({"post": "create", "get": "list"}),
        name="submission-list",
    ),
    path(
        "questions/",
        views.AssignmentQuestionViewSet.as_view({"post": "create", "get": "list"}),
        name="question-list",
    ),
    # T_ASSIGN_014: Plagiarism detection endpoints (before router to avoid conflicts)
    path(
        "submissions/<int:submission_id>/plagiarism/",
        SubmissionPlagiarismViewSet.as_view({"get": "get_plagiarism_report"}),
        name="submission-plagiarism-report",
    ),
    path(
        "submissions/<int:submission_id>/plagiarism/check/",
        SubmissionPlagiarismViewSet.as_view({"post": "start_plagiarism_check"}),
        name="submission-plagiarism-check",
    ),
    path(
        "submissions/<int:submission_id>/plagiarism/status/",
        SubmissionPlagiarismViewSet.as_view({"get": "check_plagiarism_status"}),
        name="submission-plagiarism-status",
    ),
    # Webhook endpoint
    path("webhooks/plagiarism/", plagiarism_webhook, name="plagiarism-webhook"),
    # T_ASSIGN_008: Nested routes for submission comments (before router)
    path(
        "submissions/<int:submission_id>/comments/",
        views.SubmissionCommentViewSet.as_view({"get": "list", "post": "create"}),
        name="submission-comment-list",
    ),
    path(
        "submissions/<int:submission_id>/comments/<int:pk>/",
        views.SubmissionCommentViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="submission-comment-detail",
    ),
    path(
        "submissions/<int:submission_id>/comments/<int:pk>/publish/",
        views.SubmissionCommentViewSet.as_view({"post": "publish"}),
        name="submission-comment-publish",
    ),
    path(
        "submissions/<int:submission_id>/comments/<int:pk>/toggle_pin/",
        views.SubmissionCommentViewSet.as_view({"post": "toggle_pin"}),
        name="submission-comment-toggle-pin",
    ),
    path(
        "submissions/<int:submission_id>/comments/<int:pk>/mark_read/",
        views.SubmissionCommentViewSet.as_view({"post": "mark_read"}),
        name="submission-comment-mark-read",
    ),
    path("", include(router.urls)),
]
