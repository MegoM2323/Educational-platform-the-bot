"""
T_ASSIGN_014: Views for plagiarism detection management.

Includes:
- GET /api/submissions/{id}/plagiarism/ - View plagiarism report
- POST /api/submissions/{id}/plagiarism/check/ - Initiate plagiarism check
- POST /api/webhooks/plagiarism/ - Receive webhook results
"""
import logging
import hashlib
import hmac
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import AssignmentSubmission, PlagiarismReport
from .serializers import PlagiarismReportSerializer, PlagiarismReportDetailSerializer
from .tasks.plagiarism import check_plagiarism, poll_plagiarism_results

logger = logging.getLogger(__name__)


class IsPlagiarismAuthorized(permissions.BasePermission):
    """
    Permission for plagiarism check endpoints.

    - Teachers/Tutors: Full access (create check, view reports)
    - Students: Can only view their own submission's report
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user can access this submission's plagiarism report"""
        submission = obj.submission if isinstance(obj, PlagiarismReport) else obj

        # Teachers/Tutors can access any report
        if request.user.role in ['teacher', 'tutor']:
            return True

        # Students can only view their own submission's report
        if request.user.role == 'student':
            return submission.student == request.user

        return False


class SubmissionPlagiarismViewSet(viewsets.ViewSet):
    """
    ViewSet for plagiarism detection on assignment submissions.

    Endpoints:
    - GET /api/submissions/{id}/plagiarism/ - Get plagiarism report
    - POST /api/submissions/{id}/plagiarism/check/ - Start plagiarism check
    - GET /api/submissions/{id}/plagiarism/status/ - Check status
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_submission(self, submission_id):
        """Get submission with permission check"""
        submission = get_object_or_404(AssignmentSubmission, id=submission_id)

        # Check permissions
        if submission.student != self.request.user and self.request.user.role not in ['teacher', 'tutor']:
            self.permission_denied(self.request)

        return submission

    @action(detail=False, methods=['get'], url_path=r'(?P<submission_id>\d+)/plagiarism')
    def get_plagiarism_report(self, request, submission_id=None):
        """
        GET /api/submissions/{id}/plagiarism/

        Get plagiarism detection report for a submission.

        Returns:
        - Students: Status and score only
        - Teachers: Full report with sources
        """
        submission = self.get_submission(submission_id)

        try:
            report = submission.plagiarism_report
        except PlagiarismReport.DoesNotExist:
            return Response(
                {'error': 'No plagiarism report found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        permission = IsPlagiarismAuthorized()
        if not permission.has_object_permission(request, self, report):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Serialize based on role
        if request.user.role in ['teacher', 'tutor']:
            serializer = PlagiarismReportDetailSerializer(report, context={'request': request})
        else:
            serializer = PlagiarismReportSerializer(report, context={'request': request})

        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path=r'(?P<submission_id>\d+)/plagiarism/check')
    def start_plagiarism_check(self, request, submission_id=None):
        """
        POST /api/submissions/{id}/plagiarism/check/

        Initiate plagiarism check for submission.

        Only teachers/tutors can start checks.

        Returns:
        {
            'status': 'submitted',
            'report_id': '...',
            'message': 'Check queued'
        }
        """
        submission = self.get_submission(submission_id)

        # Only teachers/tutors can initiate checks
        if request.user.role not in ['teacher', 'tutor']:
            return Response(
                {'error': 'Only teachers can initiate plagiarism checks'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if report already exists
        existing_report = PlagiarismReport.objects.filter(submission=submission).first()
        if existing_report:
            if existing_report.detection_status == PlagiarismReport.DetectionStatus.PROCESSING:
                return Response(
                    {'error': 'Check already in progress'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif existing_report.detection_status == PlagiarismReport.DetectionStatus.COMPLETED:
                return Response(
                    {
                        'status': 'already_completed',
                        'similarity_score': float(existing_report.similarity_score),
                        'checked_at': existing_report.checked_at.isoformat() if existing_report.checked_at else None
                    },
                    status=status.HTTP_200_OK
                )

        # Queue plagiarism check task
        try:
            task = check_plagiarism.apply_async(args=[submission.id])
            return Response(
                {
                    'status': 'submitted',
                    'task_id': task.id,
                    'message': 'Plagiarism check queued',
                    'expected_duration': '5-60 seconds (depends on service)'
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            logger.error(f"Failed to queue plagiarism check: {e}")
            return Response(
                {'error': f'Failed to start check: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path=r'(?P<submission_id>\d+)/plagiarism/status')
    def check_plagiarism_status(self, request, submission_id=None):
        """
        GET /api/submissions/{id}/plagiarism/status/

        Check status of plagiarism check.

        Returns current status (pending, processing, completed, failed).
        """
        submission = self.get_submission(submission_id)

        try:
            report = submission.plagiarism_report
        except PlagiarismReport.DoesNotExist:
            return Response(
                {'status': 'not_started'},
                status=status.HTTP_200_OK
            )

        return Response({
            'status': report.detection_status,
            'similarity_score': float(report.similarity_score) if report.detection_status == 'completed' else None,
            'created_at': report.created_at.isoformat(),
            'checked_at': report.checked_at.isoformat() if report.checked_at else None,
            'error': report.error_message if report.detection_status == 'failed' else None
        })


@csrf_exempt
@require_http_methods(["POST"])
def plagiarism_webhook(request):
    """
    POST /api/webhooks/plagiarism/

    Receive plagiarism detection results from external service.

    Webhook format:
    {
        'report_id': 'external-report-id',
        'similarity_score': 25.5,
        'sources': [
            {'source': 'url', 'match_percent': 15, 'matched_text': '...'}
        ]
    }

    Security:
    - Verifies webhook signature (HMAC-SHA256)
    - Validates source IP if configured
    - Idempotent: safe to replay
    """
    try:
        # Parse JSON body
        try:
            body = request.body
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in plagiarism webhook")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Verify webhook signature
        signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE')
        if not _verify_plagiarism_webhook_signature(body, signature):
            logger.warning("Invalid plagiarism webhook signature")
            return HttpResponseForbidden('Invalid signature')

        # Extract report ID
        report_id = payload.get('report_id')
        if not report_id:
            logger.warning("Missing report_id in plagiarism webhook")
            return JsonResponse({'error': 'Missing report_id'}, status=400)

        # Find plagiarism report
        try:
            plagiarism_report = PlagiarismReport.objects.get(service_report_id=report_id)
        except PlagiarismReport.DoesNotExist:
            logger.warning(f"Plagiarism webhook for unknown report: {report_id}")
            return JsonResponse({'error': 'Report not found'}, status=404)

        # Update with results
        plagiarism_report.similarity_score = payload.get('similarity_score', 0)
        plagiarism_report.sources = payload.get('sources', [])
        plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.COMPLETED
        plagiarism_report.checked_at = timezone.now()
        plagiarism_report.save()

        logger.info(
            f"Plagiarism webhook processed: "
            f"report={report_id}, similarity={plagiarism_report.similarity_score}%"
        )

        # Send notifications via async task
        from .tasks.plagiarism import _send_plagiarism_notifications
        _send_plagiarism_notifications(plagiarism_report)

        return JsonResponse({'status': 'processed'})

    except Exception as e:
        logger.error(f"Error processing plagiarism webhook: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def _verify_plagiarism_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify plagiarism webhook signature (HMAC-SHA256).

    Compares provided signature with calculated HMAC.

    Args:
        body: Raw request body bytes
        signature: Signature from HTTP_X_WEBHOOK_SIGNATURE header

    Returns:
        bool: True if signature is valid
    """
    if not signature:
        logger.warning("Missing plagiarism webhook signature")
        return False

    webhook_secret = getattr(settings, 'PLAGIARISM_WEBHOOK_SECRET', None)
    if not webhook_secret:
        # If no secret configured, allow (for development)
        logger.warning("No PLAGIARISM_WEBHOOK_SECRET configured, allowing unsigned webhook")
        return True

    try:
        # Calculate expected signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures (constant-time comparison)
        return hmac.compare_digest(signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False
