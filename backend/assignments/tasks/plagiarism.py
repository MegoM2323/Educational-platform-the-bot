"""
T_ASSIGN_014: Celery tasks for plagiarism detection.

Async tasks for:
- Submitting assignments to plagiarism detection services
- Polling for plagiarism check results
- Sending notifications on completion
- Handling timeouts and retries

Task Queue:
- check_plagiarism: Submit assignment and start checking
- poll_plagiarism_results: Poll for results (called via webhook or periodic task)
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from assignments.models import AssignmentSubmission, PlagiarismReport
from assignments.services.plagiarism import PlagiarismDetectionFactory
from notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_plagiarism(self, submission_id: int):
    """
    T_ASSIGN_014: Submit assignment submission for plagiarism checking.

    Submits the submission text to configured plagiarism detection service
    and creates a PlagiarismReport to track the check progress.

    Retries up to 3 times on failure (API timeout, connection error, etc.).

    Args:
        submission_id: ID of AssignmentSubmission to check

    Returns:
        dict: {
            'status': 'submitted'|'error',
            'report_id': str (if successful),
            'error': str (if failed)
        }
    """
    try:
        # Get submission
        try:
            submission = AssignmentSubmission.objects.get(id=submission_id)
        except AssignmentSubmission.DoesNotExist:
            logger.error(f"Submission {submission_id} not found")
            return {'status': 'error', 'error': 'Submission not found'}

        # Ensure no duplicate report
        existing_report = PlagiarismReport.objects.filter(submission=submission).exists()
        if existing_report:
            logger.warning(f"Plagiarism report already exists for submission {submission_id}")
            return {'status': 'error', 'error': 'Report already exists'}

        # Create pending plagiarism report
        plagiarism_report = PlagiarismReport.objects.create(
            submission=submission,
            detection_status=PlagiarismReport.DetectionStatus.PENDING
        )

        logger.info(f"Created plagiarism report {plagiarism_report.id} for submission {submission_id}")

        # Get submission text
        if not submission.content and not submission.file:
            logger.warning(f"Submission {submission_id} has no content to check")
            plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.FAILED
            plagiarism_report.error_message = "No content to check (empty submission)"
            plagiarism_report.save()
            return {'status': 'error', 'error': 'No content to check'}

        # Extract text from file if needed
        text_to_check = submission.content or ''
        if submission.file:
            try:
                # Read file content (supports .txt only for now)
                if submission.file.name.endswith('.txt'):
                    submission.file.open('r')
                    text_to_check += '\n' + submission.file.read().decode('utf-8')
                    submission.file.close()
            except Exception as e:
                logger.error(f"Failed to read file from submission {submission_id}: {e}")

        if not text_to_check.strip():
            logger.warning(f"Submission {submission_id} has no readable text")
            plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.FAILED
            plagiarism_report.error_message = "No readable text in submission"
            plagiarism_report.save()
            return {'status': 'error', 'error': 'No readable text'}

        # Submit to plagiarism service
        plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.PROCESSING
        plagiarism_report.save()

        client = PlagiarismDetectionFactory.get_client()
        filename = f"submission_{submission.id}_{submission.student.id}"
        report_id = client.submit_for_checking(text_to_check, filename)

        if report_id:
            plagiarism_report.service_report_id = report_id
            plagiarism_report.save()

            logger.info(
                f"Plagiarism check submitted for submission {submission_id}: "
                f"report_id={report_id}, service={plagiarism_report.service}"
            )

            # Queue task to poll for results (via webhook or periodic task)
            poll_plagiarism_results.apply_async(
                args=[plagiarism_report.id],
                countdown=10  # Start polling after 10 seconds
            )

            return {
                'status': 'submitted',
                'report_id': report_id,
                'submission_id': submission_id
            }
        else:
            # Service rejected submission
            plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.FAILED
            plagiarism_report.error_message = "Service rejected submission"
            plagiarism_report.save()

            logger.error(f"Plagiarism service rejected submission {submission_id}")
            return {'status': 'error', 'error': 'Service rejected submission'}

    except Exception as e:
        logger.error(f"Error checking plagiarism for submission {submission_id}: {e}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_in = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            logger.info(f"Retrying in {retry_in}s (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=retry_in)
        else:
            # Max retries exhausted
            logger.error(f"Max retries exhausted for submission {submission_id}")
            try:
                report = PlagiarismReport.objects.get(submission_id=submission_id)
                report.detection_status = PlagiarismReport.DetectionStatus.FAILED
                report.error_message = f"Service error after {self.max_retries} retries: {str(e)}"
                report.save()
            except PlagiarismReport.DoesNotExist:
                pass
            return {'status': 'error', 'error': str(e)}


@shared_task
def poll_plagiarism_results(plagiarism_report_id: int):
    """
    T_ASSIGN_014: Poll plagiarism detection service for results.

    Gets results from plagiarism service and updates PlagiarismReport.
    Called via webhook (preferred) or periodic polling if webhook unavailable.

    Args:
        plagiarism_report_id: ID of PlagiarismReport to update

    Returns:
        dict: {
            'status': 'completed'|'processing'|'error',
            'similarity_score': float (if completed),
            'sources_count': int
        }
    """
    try:
        # Get plagiarism report
        try:
            plagiarism_report = PlagiarismReport.objects.get(id=plagiarism_report_id)
        except PlagiarismReport.DoesNotExist:
            logger.error(f"Plagiarism report {plagiarism_report_id} not found")
            return {'status': 'error', 'error': 'Report not found'}

        # Don't poll if already completed
        if plagiarism_report.detection_status == PlagiarismReport.DetectionStatus.COMPLETED:
            logger.debug(f"Plagiarism report {plagiarism_report_id} already completed")
            return {'status': 'completed', 'similarity_score': float(plagiarism_report.similarity_score)}

        # Ensure we have a service report ID to poll
        if not plagiarism_report.service_report_id:
            logger.error(f"Plagiarism report {plagiarism_report_id} has no service report ID")
            plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.FAILED
            plagiarism_report.error_message = "Missing service report ID"
            plagiarism_report.save()
            return {'status': 'error', 'error': 'Missing service report ID'}

        # Get client and poll for results
        client = PlagiarismDetectionFactory.get_client()
        results = client.get_results(plagiarism_report.service_report_id)

        if results is None:
            # Still processing or error
            logger.debug(f"Plagiarism check still processing for report {plagiarism_report_id}")
            return {'status': 'processing'}

        # Update report with results
        with transaction.atomic():
            plagiarism_report.similarity_score = results.get('similarity_score', 0)
            plagiarism_report.sources = results.get('sources', [])
            plagiarism_report.detection_status = PlagiarismReport.DetectionStatus.COMPLETED
            plagiarism_report.checked_at = timezone.now()
            plagiarism_report.save()

            logger.info(
                f"Plagiarism check completed for submission {plagiarism_report.submission_id}: "
                f"similarity={plagiarism_report.similarity_score}%"
            )

            # Send notifications
            _send_plagiarism_notifications(plagiarism_report)

        return {
            'status': 'completed',
            'similarity_score': float(plagiarism_report.similarity_score),
            'sources_count': len(plagiarism_report.sources)
        }

    except Exception as e:
        logger.error(f"Error polling plagiarism results for report {plagiarism_report_id}: {e}")
        try:
            report = PlagiarismReport.objects.get(id=plagiarism_report_id)
            if report.detection_status == PlagiarismReport.DetectionStatus.PROCESSING:
                report.detection_status = PlagiarismReport.DetectionStatus.FAILED
                report.error_message = f"Polling error: {str(e)}"
                report.save()
        except PlagiarismReport.DoesNotExist:
            pass
        return {'status': 'error', 'error': str(e)}


def _send_plagiarism_notifications(plagiarism_report: PlagiarismReport):
    """
    Send notifications about plagiarism check results.

    Sends:
    - Student: General notification (without source details)
    - Teacher: Notification if similarity > 30% threshold
    """
    submission = plagiarism_report.submission
    student = submission.student
    teacher = submission.assignment.author

    # Student notification
    score_text = "low" if plagiarism_report.similarity_score < 30 else "high"
    student_message = (
        f"Your submission '{submission.assignment.title}' has been "
        f"checked for plagiarism with a {score_text} similarity score."
    )

    try:
        NotificationService.notify(
            recipient=student,
            title="Plagiarism Check Complete",
            message=student_message,
            notification_type="assignment_plagiarism",
            related_object=submission
        )
        logger.info(f"Student notification sent for submission {submission.id}")
    except Exception as e:
        logger.error(f"Failed to send student notification: {e}")

    # Teacher notification if high similarity
    if plagiarism_report.is_high_similarity:
        teacher_message = (
            f"Submission '{submission.assignment.title}' by {student.get_full_name()} "
            f"has high similarity: {plagiarism_report.similarity_score}%. "
            f"Please review for potential plagiarism."
        )

        try:
            NotificationService.notify(
                recipient=teacher,
                title="High Plagiarism Similarity Detected",
                message=teacher_message,
                notification_type="assignment_plagiarism_alert",
                related_object=submission
            )
            logger.info(f"Teacher alert notification sent for submission {submission.id}")
        except Exception as e:
            logger.error(f"Failed to send teacher notification: {e}")
