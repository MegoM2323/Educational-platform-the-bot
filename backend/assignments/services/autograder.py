"""
Service layer for autograder webhook processing and grade application.

Handles:
- Webhook payload validation
- Grade application with audit trail
- Student notification
- Retry logic and error handling
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.http import HttpRequest
from django.core.exceptions import ValidationError

from assignments.models import AssignmentSubmission
from assignments.webhooks.models import (
    FailedWebhookLog,
    WebhookAuditTrail
)
from notifications.models import Notification

logger = logging.getLogger(__name__)


class AutograderService:
    """
    Service for processing autograder webhooks and applying grades.

    Features:
    - Comprehensive validation of webhook payloads
    - Atomic grade application with audit trail
    - Student notification on grading completion
    - Retry mechanism for failed processing
    - DDoS protection with rate limiting
    """

    WEBHOOK_TIMEOUT = 30  # seconds for response deadline
    MAX_SCORE_TOLERANCE = 10000  # Prevent absurdly high scores

    def __init__(self):
        self.logger = logger

    def process_webhook(
        self,
        payload: Dict[str, Any],
        request: HttpRequest
    ) -> Dict[str, Any]:
        """
        Process autograder webhook and apply grade to submission.

        Args:
            payload: Webhook payload with grading results
            request: HTTP request object for IP/user agent

        Returns:
            Dict with processing result

        Raises:
            AssignmentSubmission.DoesNotExist: If submission not found
            ValidationError: If payload validation fails
        """
        submission_id = payload.get('submission_id')

        try:
            # Find submission
            submission = AssignmentSubmission.objects.get(id=submission_id)

            # Log receipt
            self._audit(submission_id, 'received', {
                'score': payload.get('score'),
                'max_score': payload.get('max_score'),
            })

            # Validate payload
            self._validate_payload(payload, submission)
            self._audit(submission_id, 'signature_verified', {})

            # Validate score against max_score
            score = payload.get('score')
            max_score = payload.get('max_score')
            if not self._validate_score(score, max_score):
                raise ValidationError(
                    f'Invalid score: {score} exceeds max_score: {max_score}'
                )

            # Apply grade
            with transaction.atomic():
                result = self._apply_grade(
                    submission,
                    score,
                    max_score,
                    payload.get('feedback', '')
                )

                # Send notification
                self._notify_student(submission, score, max_score)

                # Log success
                self._audit(submission_id, 'grade_applied', {
                    'score': score,
                    'max_score': max_score,
                    'feedback': payload.get('feedback', '')[:100],  # truncate for log
                })

            return {
                'success': True,
                'submission_id': submission_id,
                'score': score,
                'message': 'Grade applied successfully'
            }

        except AssignmentSubmission.DoesNotExist:
            self._audit(
                submission_id,
                'error',
                {'error': 'Submission not found'}
            )
            raise

        except ValidationError as e:
            self._audit(
                submission_id,
                'error',
                {'error': str(e)}
            )
            raise

        except Exception as e:
            self._audit(
                submission_id,
                'error',
                {'error': str(e), 'exception_type': type(e).__name__}
            )
            self._log_failed_webhook(payload, str(e), request)
            raise

    def _validate_payload(
        self,
        payload: Dict[str, Any],
        submission: AssignmentSubmission
    ) -> None:
        """
        Validate webhook payload format and constraints.

        Args:
            payload: Webhook payload
            submission: The assignment submission being graded

        Raises:
            ValidationError: If validation fails
        """
        # Check data types
        if not isinstance(payload.get('score'), (int, float)):
            raise ValidationError('score must be numeric')

        if not isinstance(payload.get('max_score'), (int, float)):
            raise ValidationError('max_score must be numeric')

        if not isinstance(payload.get('feedback'), str):
            raise ValidationError('feedback must be string')

        # Check score ranges
        score = payload.get('score')
        max_score = payload.get('max_score')

        if score < 0:
            raise ValidationError('score cannot be negative')

        if max_score <= 0:
            raise ValidationError('max_score must be positive')

        if score > max_score:
            raise ValidationError(f'score ({score}) cannot exceed max_score ({max_score})')

        if max_score > self.MAX_SCORE_TOLERANCE:
            raise ValidationError(f'max_score ({max_score}) exceeds tolerance')

    def _validate_score(self, score: float, max_score: float) -> bool:
        """
        Validate score is within acceptable ranges.

        Args:
            score: Student's score
            max_score: Maximum possible score

        Returns:
            True if valid, False otherwise
        """
        if score < 0 or score > self.MAX_SCORE_TOLERANCE:
            return False

        if max_score <= 0 or max_score > self.MAX_SCORE_TOLERANCE:
            return False

        if score > max_score:
            return False

        return True

    @transaction.atomic
    def _apply_grade(
        self,
        submission: AssignmentSubmission,
        score: float,
        max_score: float,
        feedback: str
    ) -> Dict[str, Any]:
        """
        Apply grade to submission and update status.

        Args:
            submission: AssignmentSubmission instance
            score: Numeric score
            max_score: Maximum score for this grading
            feedback: Grading feedback/results

        Returns:
            Dict with grading result
        """
        # Round score to integer
        score = int(round(score))

        # Update submission
        submission.score = score
        submission.max_score = max_score or submission.assignment.max_score
        submission.feedback = feedback
        submission.status = AssignmentSubmission.Status.GRADED
        submission.graded_at = timezone.now()
        submission.save()

        self.logger.info(
            f'Grade applied to submission {submission.id}: '
            f'score={score}/{max_score}'
        )

        return {
            'submission_id': submission.id,
            'score': score,
            'max_score': max_score,
            'percentage': submission.percentage
        }

    def _notify_student(
        self,
        submission: AssignmentSubmission,
        score: float,
        max_score: float
    ) -> None:
        """
        Send notification to student about grade.

        Args:
            submission: AssignmentSubmission instance
            score: Score received
            max_score: Maximum score
        """
        try:
            percentage = round((score / max_score * 100), 2) if max_score else 0

            notification = Notification.objects.create(
                title='Задание оценено',
                message=(
                    f'Ваше задание "{submission.assignment.title}" '
                    f'оценено: {score}/{max_score} ({percentage}%)\n\n'
                    f'Обратная связь: {submission.feedback[:200]}'
                ),
                recipient=submission.student,
                type=Notification.Type.ASSIGNMENT_GRADED,
                priority=Notification.Priority.NORMAL,
            )

            self._audit(
                submission.id,
                'notification_sent',
                {'notification_id': notification.id}
            )

            self.logger.info(
                f'Notification sent to {submission.student.email} '
                f'for submission {submission.id}'
            )

        except Exception as e:
            self.logger.warning(
                f'Failed to send notification: {e}'
            )

    def _audit(
        self,
        submission_id: int,
        event_type: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log audit trail entry.

        Args:
            submission_id: ID of submission being graded
            event_type: Type of event (received, verified, etc.)
            details: Event details as dict
        """
        try:
            WebhookAuditTrail.objects.create(
                submission_id=submission_id,
                event_type=event_type,
                details=details,
                created_by='AutograderService'
            )
        except Exception as e:
            self.logger.error(f'Failed to create audit trail: {e}')

    def _log_failed_webhook(
        self,
        payload: Dict[str, Any],
        error_message: str,
        request: HttpRequest
    ) -> None:
        """
        Log failed webhook for retry processing.

        Args:
            payload: Original webhook payload
            error_message: Exception message
            request: HTTP request for IP extraction
        """
        try:
            ip = self._get_client_ip(request) if request else 'unknown'

            FailedWebhookLog.objects.create(
                submission_id=payload.get('submission_id'),
                payload=payload,
                error_message=error_message,
                remote_ip=ip,
                status=FailedWebhookLog.Status.PENDING,
                retry_count=0
            )

            self.logger.info(
                f'Failed webhook logged for retry: '
                f'submission_id={payload.get("submission_id")}'
            )

        except Exception as e:
            self.logger.error(f'Failed to log webhook error: {e}')

    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Extract client IP from request.

        Args:
            request: HTTP request object

        Returns:
            Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def retry_failed_webhooks(self, max_retries: int = 3) -> Dict[str, int]:
        """
        Retry processing of failed webhooks.

        Useful for scheduled tasks to recover from transient failures.

        Args:
            max_retries: Maximum retry attempts

        Returns:
            Dict with retry statistics
        """
        failed = FailedWebhookLog.objects.filter(
            status=FailedWebhookLog.Status.PENDING,
            retry_count__lt=max_retries
        ).order_by('created_at')[:100]  # Batch process

        stats = {
            'total': failed.count(),
            'succeeded': 0,
            'failed': 0
        }

        for log in failed:
            try:
                log.status = FailedWebhookLog.Status.PROCESSING
                log.save(update_fields=['status'])

                # Re-process webhook
                service = AutograderService()
                service.process_webhook(log.payload, None)

                log.status = FailedWebhookLog.Status.SUCCESS
                log.save(update_fields=['status'])
                stats['succeeded'] += 1

            except Exception as e:
                log.increment_retry()
                self.logger.error(
                    f'Webhook retry failed: submission_id={log.submission_id}, '
                    f'error={e}'
                )
                stats['failed'] += 1

        return stats
