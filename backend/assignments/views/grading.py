"""
T_ASN_004: ViewSets for auto-grading operations

Provides REST API endpoints for:
- Auto-grading submissions
- Bulk auto-grading for assignments
- Getting grading breakdown
"""

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from assignments.models import Assignment, AssignmentSubmission
from assignments.services.grading import GradingService
from assignments.tasks.grading import (
    auto_grade_assignment_task,
    auto_grade_submission_task,
    batch_auto_grade_submissions
)

logger = logging.getLogger(__name__)


class IsTeacherOrTutor(permissions.BasePermission):
    """
    Permission class to restrict access to teachers and tutors only.
    """
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["teacher", "tutor", "admin"]
        )


class AutoGradingMixin:
    """
    Mixin to add auto-grading actions to ViewSets.
    """

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsTeacherOrTutor]
    )
    def auto_grade(self, request, pk=None):
        """
        Auto-grade a single submission.

        POST /api/assignments/{assignment_id}/submissions/{submission_id}/auto-grade/

        Request body:
        {
            "grading_mode": "proportional",  # or "all_or_nothing"
            "numeric_tolerance": 0.05,        # 5% tolerance for numeric answers
            "async": false                    # whether to process asynchronously
        }

        Returns:
        {
            "success": true,
            "submission_id": 1,
            "total_score": 75,
            "max_score": 100,
            "percentage": 75.0,
            "grade_letter": "C",
            "question_results": [
                {
                    "question_id": 1,
                    "question_type": "single_choice",
                    "points_possible": 10,
                    "points_earned": 10,
                    "is_correct": true,
                    "explanation": "Правильный ответ"
                }
            ],
            "summary": {
                "total_questions": 10,
                "correct_answers": 7,
                "incorrect_answers": 2,
                "unanswered": 1
            }
        }
        """
        submission = self.get_object()

        # Check permissions
        if request.user.role == 'teacher':
            if submission.assignment.author != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

        grading_mode = request.data.get(
            'grading_mode',
            GradingService.GRADING_MODE_PROPORTIONAL
        )
        numeric_tolerance = request.data.get('numeric_tolerance', 0.05)
        use_async = request.data.get('async', False)

        # Validate grading mode
        if grading_mode not in [
            GradingService.GRADING_MODE_ALL_OR_NOTHING,
            GradingService.GRADING_MODE_PROPORTIONAL
        ]:
            return Response(
                {'error': 'Invalid grading_mode'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if use_async:
                # Queue async task
                task = auto_grade_submission_task.delay(
                    submission.id,
                    grading_mode=grading_mode,
                    numeric_tolerance=numeric_tolerance
                )
                return Response({
                    'success': True,
                    'submission_id': submission.id,
                    'task_id': task.id,
                    'message': 'Submission queued for auto-grading'
                })

            else:
                # Grade synchronously
                service = GradingService()
                result = service.auto_grade_submission(
                    submission,
                    grading_mode=grading_mode,
                    numeric_tolerance=numeric_tolerance
                )

                return Response({
                    'success': True,
                    'submission_id': submission.id,
                    'total_score': result['total_score'],
                    'max_score': result['max_score'],
                    'percentage': result['percentage'],
                    'grade_letter': result['grade_letter'],
                    'question_results': result['question_results'],
                    'summary': result['summary']
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error auto-grading submission {submission.id}: {e}')
            return Response(
                {'error': 'Failed to auto-grade submission'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsTeacherOrTutor],
        url_path='auto-grade-all'
    )
    def auto_grade_all(self, request, pk=None):
        """
        Auto-grade all submitted assignments for a given assignment.

        POST /api/assignments/{assignment_id}/auto-grade-all/

        Request body:
        {
            "grading_mode": "proportional",
            "numeric_tolerance": 0.05,
            "async": true
        }

        Returns:
        {
            "success": true,
            "assignment_id": 1,
            "task_id": "abc123",  # if async
            "statistics": {
                "total": 25,
                "graded": 24,
                "failed": 1,
                "errors": [
                    {"submission_id": 5, "error": "..."}
                ]
            }
        }
        """
        assignment = self.get_object()

        # Check permissions
        if request.user.role == 'teacher':
            if assignment.author != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

        grading_mode = request.data.get(
            'grading_mode',
            GradingService.GRADING_MODE_PROPORTIONAL
        )
        numeric_tolerance = request.data.get('numeric_tolerance', 0.05)
        use_async = request.data.get('async', True)

        try:
            if use_async:
                # Queue async task
                task = auto_grade_assignment_task.delay(
                    assignment.id,
                    grading_mode=grading_mode,
                    numeric_tolerance=numeric_tolerance
                )
                return Response({
                    'success': True,
                    'assignment_id': assignment.id,
                    'task_id': task.id,
                    'message': 'Assignment queued for auto-grading'
                })

            else:
                # Grade synchronously
                service = GradingService()
                stats = service.auto_grade_assignment(
                    assignment,
                    grading_mode=grading_mode,
                    numeric_tolerance=numeric_tolerance
                )

                return Response({
                    'success': True,
                    'assignment_id': assignment.id,
                    'statistics': stats
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error auto-grading assignment {assignment.id}: {e}')
            return Response(
                {'error': 'Failed to auto-grade assignment'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def grading_breakdown(self, request, pk=None):
        """
        Get detailed grading breakdown for a submission.

        GET /api/assignments/{assignment_id}/submissions/{submission_id}/grading-breakdown/

        Returns detailed information about each question and answer:
        {
            "submission_id": 1,
            "assignment_id": 1,
            "student_id": 2,
            "total_score": 75,
            "max_score": 100,
            "percentage": 75.0,
            "questions": [
                {
                    "question_id": 1,
                    "question_text": "What is 2+2?",
                    "question_type": "multiple_choice",
                    "points_possible": 10,
                    "points_earned": 10,
                    "is_correct": true,
                    "student_answer": ["4"],
                    "correct_answer": ["4"]
                }
            ]
        }
        """
        submission = self.get_object()

        # Check permissions
        if request.user.role == 'student':
            if submission.student != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.role == 'parent':
            children = request.user.parent_profile.children.all()
            if submission.student not in children:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

        try:
            service = GradingService()
            breakdown = service.get_grading_breakdown(submission)
            return Response(breakdown, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error getting grading breakdown: {e}')
            return Response(
                {'error': 'Failed to get grading breakdown'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
