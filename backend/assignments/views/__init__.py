"""
Assignments views package

Organizes views into logical modules:
- grading: Grading-related views
- history: Assignment history and versioning views
- late_submissions: Late submission handling views
"""

from .late_submissions import LateSubmissionViewSet

# Импортируем основные ViewSets из views_main
from ..views_main import (
    AssignmentViewSet,
    AssignmentSubmissionViewSet,
    AssignmentQuestionViewSet,
    AssignmentAnswerViewSet,
    CommentTemplateViewSet,
    SubmissionCommentViewSet,
    PeerReviewAssignmentViewSet,
    PeerReviewViewSet,
    AssignmentAttemptViewSet,
)

__all__ = [
    'LateSubmissionViewSet',
    'AssignmentViewSet',
    'AssignmentSubmissionViewSet',
    'AssignmentQuestionViewSet',
    'AssignmentAnswerViewSet',
    'CommentTemplateViewSet',
    'SubmissionCommentViewSet',
    'PeerReviewAssignmentViewSet',
    'PeerReviewViewSet',
    'AssignmentAttemptViewSet',
]
