"""
T_ASSIGN_010: API views for assignment history and submission versioning.

Endpoints:
- GET /api/assignments/{id}/history/ - List assignment changes
- GET /api/assignments/{id}/history/{history_id}/ - View change details
- GET /api/submissions/{id}/versions/ - List submission versions
- GET /api/submissions/{id}/versions/{version_id}/ - View version details
- GET /api/submissions/{id}/diff/ - Compare two versions
- POST /api/submissions/{id}/restore/ - Restore previous version
- GET /api/submissions/{id}/restores/ - View restoration history
"""
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
import difflib

from assignments.models import (
    Assignment, AssignmentSubmission, AssignmentHistory, SubmissionVersion,
    SubmissionVersionDiff, SubmissionVersionRestore
)
from assignments.serializers_history import (
    AssignmentHistorySerializer, SubmissionVersionSerializer,
    SubmissionVersionListSerializer, SubmissionVersionDetailSerializer,
    SubmissionVersionDiffSerializer, SubmissionVersionRestoreSerializer,
    SubmissionRestoreRequestSerializer
)

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    """Standard pagination for history endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsTeacherOrTutorOrStudent(permissions.BasePermission):
    """Permission to check if user is teacher, tutor, or the student making the request."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["teacher", "tutor", "student", "admin"]
        )


class AssignmentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing assignment history.

    Endpoints:
    - GET /api/assignments/{assignment_id}/history/ - List all changes
    - GET /api/assignments/{assignment_id}/history/{id}/ - View specific change
    """
    serializer_class = AssignmentHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        """Get history for the specified assignment."""
        assignment_id = self.kwargs.get('assignment_id')
        queryset = AssignmentHistory.objects.filter(
            assignment_id=assignment_id
        ).select_related('changed_by', 'assignment').order_by('-change_time')

        # Students can only see history for their assigned assignments
        if self.request.user.role == 'student':
            queryset = queryset.filter(
                assignment__assigned_to=self.request.user
            )

        return queryset

    def get_object(self):
        """Get a specific history record."""
        assignment_id = self.kwargs.get('assignment_id')
        history_id = self.kwargs.get('pk')

        # Verify assignment exists and user has access
        assignment = get_object_or_404(Assignment, id=assignment_id)
        if self.request.user.role == 'student':
            if not assignment.assigned_to.filter(id=self.request.user.id).exists():
                self.permission_denied(self.request)

        return get_object_or_404(
            AssignmentHistory,
            id=history_id,
            assignment_id=assignment_id
        )


class SubmissionVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing submission versions.

    Endpoints:
    - GET /api/submissions/{submission_id}/versions/ - List all versions
    - GET /api/submissions/{submission_id}/versions/{id}/ - View version details
    - GET /api/submissions/{submission_id}/diff/ - Compare versions
    - POST /api/submissions/{submission_id}/restore/ - Restore version
    - GET /api/submissions/{submission_id}/restores/ - View restoration history
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return SubmissionVersionListSerializer
        elif self.action in ['retrieve', 'diff']:
            return SubmissionVersionDetailSerializer
        elif self.action == 'restores':
            return SubmissionVersionRestoreSerializer
        return SubmissionVersionSerializer

    def get_queryset(self):
        """Get versions for the specified submission."""
        submission_id = self.kwargs.get('submission_id')
        queryset = SubmissionVersion.objects.filter(
            submission_id=submission_id
        ).select_related('submitted_by', 'submission', 'previous_version')

        return queryset.order_by('version_number')

    def get_submission(self):
        """Get and verify access to the submission."""
        submission_id = self.kwargs.get('submission_id')
        submission = get_object_or_404(AssignmentSubmission, id=submission_id)

        # Check permissions
        user = self.request.user
        if user.role == 'student' and submission.student_id != user.id:
            self.permission_denied(self.request, "Cannot view other students' submissions")
        elif user.role == 'parent':
            # Check if student is their child
            children = user.parent_profile.children.all()
            if submission.student not in children:
                self.permission_denied(self.request, "Cannot view non-child submissions")

        return submission

    def get_object(self):
        """Get a specific version."""
        version_id = self.kwargs.get('pk')
        submission_id = self.kwargs.get('submission_id')

        # Verify submission access
        self.get_submission()

        return get_object_or_404(
            SubmissionVersion,
            id=version_id,
            submission_id=submission_id
        )

    @action(detail=False, methods=['get'])
    def diff(self, request, submission_id=None):
        """
        Compare two submission versions.

        Query parameters:
        - version_a: Version number of first version
        - version_b: Version number of second version
        """
        submission = self.get_submission()

        version_a_num = request.query_params.get('version_a')
        version_b_num = request.query_params.get('version_b')

        if not version_a_num or not version_b_num:
            return Response(
                {'error': 'Both version_a and version_b parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            version_a = SubmissionVersion.objects.get(
                submission=submission,
                version_number=int(version_a_num)
            )
            version_b = SubmissionVersion.objects.get(
                submission=submission,
                version_number=int(version_b_num)
            )
        except (SubmissionVersion.DoesNotExist, ValueError):
            return Response(
                {'error': 'Invalid version number(s)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if diff already exists
        diff_obj = SubmissionVersionDiff.objects.filter(
            version_a=version_a,
            version_b=version_b
        ).first()

        if not diff_obj:
            # Generate diff
            diff_content = self._generate_diff(version_a, version_b)
            try:
                diff_obj = SubmissionVersionDiff.objects.create(
                    version_a=version_a,
                    version_b=version_b,
                    diff_content=diff_content
                )
            except Exception as e:
                logger.error(f"Error creating diff: {e}")
                diff_content = {'error': 'Failed to generate diff'}

        serializer = SubmissionVersionDiffSerializer(diff_obj, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def restore(self, request, submission_id=None):
        """
        Restore a previous submission version.

        Request body:
        {
            "version_number": 1,
            "reason": "Student requested resubmission"
        }

        This creates a NEW version copying the content of the old version,
        rather than overwriting. This maintains version history.
        """
        submission = self.get_submission()

        # Only teachers/tutors can restore
        if request.user.role not in ['teacher', 'tutor', 'admin']:
            return Response(
                {'error': 'Only teachers/tutors can restore versions'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SubmissionRestoreRequestSerializer(
            data=request.data,
            context={'submission': submission}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        version_number = serializer.validated_data['version_number']
        reason = serializer.validated_data.get('reason', '')

        try:
            restore_from_version = SubmissionVersion.objects.get(
                submission=submission,
                version_number=version_number
            )
        except SubmissionVersion.DoesNotExist:
            return Response(
                {'error': f'Version {version_number} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get the next version number
        latest_version = SubmissionVersion.objects.filter(
            submission=submission
        ).order_by('-version_number').first()
        new_version_number = (latest_version.version_number + 1) if latest_version else 1

        # Create new version with restored content
        try:
            new_version = SubmissionVersion.objects.create(
                submission=submission,
                version_number=new_version_number,
                file=restore_from_version.file,
                content=restore_from_version.content,
                is_final=True,
                submitted_by=request.user,
                previous_version=latest_version
            )

            # Mark previous version as not final
            if latest_version:
                latest_version.is_final = False
                latest_version.save(update_fields=['is_final'])

            # Create audit trail
            restore_record = SubmissionVersionRestore.objects.create(
                submission=submission,
                restored_from_version=restore_from_version,
                restored_to_version=new_version,
                restored_by=request.user,
                reason=reason
            )

            logger.info(
                f"Restored submission {submission.id} from v{version_number} "
                f"to v{new_version_number} by {request.user}"
            )

            serializer = SubmissionVersionSerializer(new_version, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error restoring submission version: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to restore version'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def restores(self, request, submission_id=None):
        """
        List all restoration events for this submission.

        Shows audit trail of when versions were restored and why.
        """
        submission = self.get_submission()

        restores = SubmissionVersionRestore.objects.filter(
            submission=submission
        ).select_related(
            'restored_by', 'restored_from_version', 'restored_to_version'
        ).order_by('-restored_at')

        page = self.paginate_queryset(restores)
        if page is not None:
            serializer = SubmissionVersionRestoreSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubmissionVersionRestoreSerializer(
            restores,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @staticmethod
    def _generate_diff(version_a, version_b):
        """Generate a diff between two submission versions."""
        content_a = (version_a.content or '').split('\n')
        content_b = (version_b.content or '').split('\n')

        # Use difflib to generate unified diff
        diff = list(difflib.unified_diff(
            content_a,
            content_b,
            lineterm='',
            fromfile=f'v{version_a.version_number}',
            tofile=f'v{version_b.version_number}'
        ))

        # Parse diff into structured format
        result = {
            'lines': diff,
            'added_count': sum(1 for line in diff if line.startswith('+')),
            'removed_count': sum(1 for line in diff if line.startswith('-')),
            'summary': f"Changed {len(content_a)} -> {len(content_b)} lines"
        }

        return result
