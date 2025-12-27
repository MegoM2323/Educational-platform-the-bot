"""
T_ASN_007: Late Submission Handling Views

Implements endpoints for:
- Listing late submissions
- Adjusting penalty for specific submissions
- Extending deadline for students
- Late submission reporting and analytics
"""

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from assignments.models import Assignment, AssignmentSubmission, SubmissionExemption
from assignments.services.late_policy import LatePolicyService
from assignments.serializers import (
    AssignmentSubmissionSerializer,
    SubmissionExemptionSerializer
)

logger = logging.getLogger(__name__)
User = get_user_model()


class IsTeacherOrTutor(permissions.BasePermission):
    """Permission class for teacher/tutor access."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ["teacher", "tutor"]
        )


class LateSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing late submissions.

    Endpoints:
    - GET /api/assignments/{id}/late-submissions/ - List late submissions
    - GET /api/assignments/{id}/late-submissions/{id}/ - Get late submission details
    - PATCH /api/assignments/{id}/late-submissions/{id}/adjust-penalty/ - Adjust penalty
    - POST /api/assignments/{id}/extend-deadline/ - Extend deadline for student
    """

    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrTutor]

    def get_queryset(self):
        """Get late submissions for the assignment."""
        assignment_id = self.kwargs.get('assignment_id')

        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return AssignmentSubmission.objects.none()

        # Check if user is the assignment author
        if assignment.author != self.request.user:
            return AssignmentSubmission.objects.none()

        # Return only late submissions for this assignment
        return assignment.submissions.filter(is_late=True).order_by('-days_late')

    def get_assignment(self):
        """Get the assignment from URL kwargs."""
        assignment_id = self.kwargs.get('assignment_id')
        return Assignment.objects.get(id=assignment_id)

    def list(self, request, *args, **kwargs):
        """
        List all late submissions for an assignment.

        GET /api/assignments/{id}/late-submissions/

        Returns:
        - id: submission ID
        - student: student info
        - is_late: whether late
        - days_late: how many days/hours late
        - penalty_applied: penalty amount
        - score: original score
        - is_exempt: whether exempt from penalty
        """
        try:
            assignment = self.get_assignment()
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if assignment.author != request.user:
            return Response(
                {'error': 'Only assignment author can view late submissions'},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Add late submission specific info
        response_data = []
        for i, submission_data in enumerate(serializer.data):
            submission = queryset[i]
            service = LatePolicyService(submission)

            submission_data['late_info'] = {
                'is_late': service.is_late(),
                'days_late': float(submission.days_late),
                'hours_late': float(submission.days_late * 24) if submission.days_late else 0,
                'penalty_applied': float(submission.penalty_applied) if submission.penalty_applied else None,
                'is_exempt': service.is_exempt(),
                'exemption_reason': submission.exemption.reason if service.is_exempt() else None,
            }
            response_data.append(submission_data)

        return Response(response_data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        Get details of a specific late submission.

        GET /api/assignments/{assignment_id}/late-submissions/{submission_id}/
        """
        try:
            assignment = self.get_assignment()
            submission = assignment.submissions.get(
                id=kwargs.get('pk'),
                is_late=True
            )
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except AssignmentSubmission.DoesNotExist:
            return Response(
                {'error': 'Late submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if assignment.author != request.user:
            return Response(
                {'error': 'Only assignment author can view this submission'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(submission)
        service = LatePolicyService(submission)

        response_data = serializer.data
        response_data['late_info'] = {
            'is_late': service.is_late(),
            'days_late': float(submission.days_late),
            'hours_late': float(submission.days_late * 24) if submission.days_late else 0,
            'penalty_applied': float(submission.penalty_applied) if submission.penalty_applied else None,
            'is_exempt': service.is_exempt(),
            'exemption_reason': submission.exemption.reason if service.is_exempt() else None,
            'original_score': submission.score + (submission.penalty_applied or 0) if submission.score else None,
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def adjust_penalty(self, request, *args, **kwargs):
        """
        Adjust penalty for a specific late submission.

        PATCH /api/assignments/{assignment_id}/late-submissions/{submission_id}/adjust-penalty/

        Request body:
        {
            "action": "full_exemption" | "custom_penalty" | "remove_exemption",
            "custom_penalty_rate": 5.0 (if action='custom_penalty'),
            "reason": "Medical excuse"
        }

        Returns updated submission with penalty info.
        """
        try:
            assignment = self.get_assignment()
            submission = assignment.submissions.get(
                id=kwargs.get('pk'),
                is_late=True
            )
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except AssignmentSubmission.DoesNotExist:
            return Response(
                {'error': 'Late submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if assignment.author != request.user:
            return Response(
                {'error': 'Only assignment author can adjust penalties'},
                status=status.HTTP_403_FORBIDDEN
            )

        action_type = request.data.get('action')
        reason = request.data.get('reason', 'Teacher override')

        if not action_type:
            return Response(
                {'error': 'action parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                service = LatePolicyService(submission)

                if action_type == 'full_exemption':
                    # Create full exemption
                    if service.is_exempt():
                        submission.exemption.delete()

                    service.create_exemption(
                        exemption_type='full',
                        reason=reason,
                        created_by=request.user
                    )
                    logger.info(
                        f"Created full exemption for submission {submission.id} by {request.user}"
                    )

                elif action_type == 'custom_penalty':
                    # Create custom penalty rate
                    custom_rate = request.data.get('custom_penalty_rate')
                    if custom_rate is None:
                        return Response(
                            {'error': 'custom_penalty_rate required for custom_penalty action'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    try:
                        custom_rate = Decimal(str(custom_rate))
                        if custom_rate < 0 or custom_rate > 100:
                            return Response(
                                {'error': 'custom_penalty_rate must be between 0 and 100'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    except (ValueError, TypeError):
                        return Response(
                            {'error': 'Invalid custom_penalty_rate value'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    if service.is_exempt():
                        submission.exemption.delete()

                    service.create_exemption(
                        exemption_type='custom_rate',
                        reason=reason,
                        created_by=request.user,
                        custom_penalty_rate=custom_rate
                    )
                    logger.info(
                        f"Created custom penalty exemption ({custom_rate}%) for submission {submission.id} by {request.user}"
                    )

                elif action_type == 'remove_exemption':
                    # Remove exemption
                    if service.is_exempt():
                        service.remove_exemption()
                        logger.info(
                            f"Removed exemption from submission {submission.id} by {request.user}"
                        )

                else:
                    return Response(
                        {'error': f'Invalid action: {action_type}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Reload and return updated submission
                submission.refresh_from_db()
                serializer = self.get_serializer(submission)
                service = LatePolicyService(submission)

                response_data = serializer.data
                response_data['late_info'] = {
                    'is_late': service.is_late(),
                    'days_late': float(submission.days_late),
                    'penalty_applied': float(submission.penalty_applied) if submission.penalty_applied else None,
                    'is_exempt': service.is_exempt(),
                    'exemption_reason': submission.exemption.reason if service.is_exempt() else None,
                }

                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error adjusting penalty: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def extend_deadline(self, request, *args, **kwargs):
        """
        Extend assignment deadline for specific student(s).

        POST /api/assignments/{assignment_id}/extend-deadline/

        Request body:
        {
            "student_ids": [1, 2, 3],
            "new_deadline": "2025-12-31T23:59:59Z",
            "reason": "Extension reason"
        }

        Note: Currently stores in StudentDeadlineExtension model.
        Actual deadline validation happens during submission.
        """
        try:
            assignment = self.get_assignment()
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if assignment.author != request.user:
            return Response(
                {'error': 'Only assignment author can extend deadlines'},
                status=status.HTTP_403_FORBIDDEN
            )

        student_ids = request.data.get('student_ids', [])
        new_deadline_str = request.data.get('new_deadline')
        reason = request.data.get('reason', 'Teacher extension')

        if not student_ids:
            return Response(
                {'error': 'student_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not new_deadline_str:
            return Response(
                {'error': 'new_deadline required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate students exist
        students = User.objects.filter(id__in=student_ids, role='student')
        if students.count() != len(student_ids):
            return Response(
                {'error': 'Some students not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from django.utils.dateparse import parse_datetime
            new_deadline = parse_datetime(new_deadline_str)
            if not new_deadline:
                return Response(
                    {'error': 'Invalid datetime format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_deadline <= assignment.due_date:
                return Response(
                    {'error': 'New deadline must be after original deadline'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            return Response(
                {'error': f'Invalid deadline: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Import the model for deadline extensions
            from assignments.models import StudentDeadlineExtension

            extensions = []
            for student in students:
                extension, created = StudentDeadlineExtension.objects.get_or_create(
                    assignment=assignment,
                    student=student,
                    defaults={
                        'extended_deadline': new_deadline,
                        'reason': reason,
                        'extended_by': request.user,
                    }
                )
                if not created:
                    # Update existing extension
                    extension.extended_deadline = new_deadline
                    extension.reason = reason
                    extension.extended_by = request.user
                    extension.save()

                extensions.append({
                    'student_id': student.id,
                    'student_name': student.get_full_name(),
                    'new_deadline': new_deadline.isoformat(),
                    'reason': reason
                })

                logger.info(
                    f"Extended deadline for {student.get_full_name()} on assignment {assignment.title} "
                    f"to {new_deadline} by {request.user}"
                )

            return Response({
                'message': f'Deadline extended for {len(extensions)} student(s)',
                'extensions': extensions
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error extending deadline: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def late_report(self, request, *args, **kwargs):
        """
        Get late submission report for an assignment.

        GET /api/assignments/{assignment_id}/late-submissions/late_report/

        Returns:
        - total_submissions: Total submission count
        - late_submissions: Number of late submissions
        - late_percentage: Percentage of late submissions
        - late_by_days: Distribution of late submissions by days/hours
        - exemptions: Number of exemptions
        - penalties_waived: Number of penalties waived
        """
        try:
            assignment = self.get_assignment()
        except Assignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        if assignment.author != request.user:
            return Response(
                {'error': 'Only assignment author can view reports'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            all_submissions = assignment.submissions.all()
            late_submissions = all_submissions.filter(is_late=True)

            total = all_submissions.count()
            late_count = late_submissions.count()
            exemption_count = SubmissionExemption.objects.filter(
                submission__in=late_submissions
            ).count()

            # Analyze penalty distribution
            penalties_by_student = {}
            for submission in late_submissions:
                if submission.penalty_applied:
                    penalties_by_student[submission.student.id] = float(submission.penalty_applied)

            # Distribution by days late
            distribution = {
                'same_day': late_submissions.filter(days_late__lt=1).count(),
                '1_day': late_submissions.filter(days_late__gte=1, days_late__lt=2).count(),
                '2_3_days': late_submissions.filter(days_late__gte=2, days_late__lt=4).count(),
                '4_7_days': late_submissions.filter(days_late__gte=4, days_late__lt=8).count(),
                '1_2_weeks': late_submissions.filter(days_late__gte=8, days_late__lt=15).count(),
                'over_2_weeks': late_submissions.filter(days_late__gte=15).count(),
            }

            # Calculate trend
            late_percentage = (late_count / total * 100) if total > 0 else 0

            report = {
                'assignment': {
                    'id': assignment.id,
                    'title': assignment.title,
                    'due_date': assignment.due_date.isoformat(),
                },
                'summary': {
                    'total_submissions': total,
                    'late_submissions': late_count,
                    'late_percentage': round(late_percentage, 2),
                    'on_time_submissions': total - late_count,
                    'on_time_percentage': round(100 - late_percentage, 2),
                },
                'exemptions': {
                    'total_exemptions': exemption_count,
                    'full_exemptions': SubmissionExemption.objects.filter(
                        submission__in=late_submissions,
                        exemption_type='full'
                    ).count(),
                    'custom_rate_exemptions': SubmissionExemption.objects.filter(
                        submission__in=late_submissions,
                        exemption_type='custom_rate'
                    ).count(),
                },
                'distribution': distribution,
                'penalties': {
                    'total_penalties_applied': len(penalties_by_student),
                    'average_penalty': sum(penalties_by_student.values()) / len(penalties_by_student) if penalties_by_student else 0,
                    'penalties_by_student': penalties_by_student,
                }
            }

            return Response(report, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating late report: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
