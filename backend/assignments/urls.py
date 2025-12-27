from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'assignments', views.AssignmentViewSet)
router.register(r'submissions', views.AssignmentSubmissionViewSet)
router.register(r'questions', views.AssignmentQuestionViewSet)
router.register(r'answers', views.AssignmentAnswerViewSet)
router.register(r'comment-templates', views.CommentTemplateViewSet, basename='comment-template')

urlpatterns = [
    path('', include(router.urls)),
    # T_ASSIGN_008: Nested routes for submission comments
    path(
        'submissions/<int:submission_id>/comments/',
        views.SubmissionCommentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='submission-comment-list'
    ),
    path(
        'submissions/<int:submission_id>/comments/<int:pk>/',
        views.SubmissionCommentViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='submission-comment-detail'
    ),
    path(
        'submissions/<int:submission_id>/comments/<int:pk>/publish/',
        views.SubmissionCommentViewSet.as_view({'post': 'publish'}),
        name='submission-comment-publish'
    ),
    path(
        'submissions/<int:submission_id>/comments/<int:pk>/toggle_pin/',
        views.SubmissionCommentViewSet.as_view({'post': 'toggle_pin'}),
        name='submission-comment-toggle-pin'
    ),
    path(
        'submissions/<int:submission_id>/comments/<int:pk>/mark_read/',
        views.SubmissionCommentViewSet.as_view({'post': 'mark_read'}),
        name='submission-comment-mark-read'
    ),
]
