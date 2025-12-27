"""
T_ASN_004: Celery tasks for auto-grading operations

Handles async grading tasks:
- Bulk grading for all submissions
- Single submission grading
- Batch processing with progress tracking
"""

import logging
from celery import shared_task
from django.db import transaction

from assignments.models import Assignment, AssignmentSubmission
from assignments.services.grading import GradingService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_grade_assignment_task(
    self,
    assignment_id: int,
    grading_mode: str = 'proportional',
    numeric_tolerance: float = 0.05
) -> dict:
    """
    Async task to auto-grade all submissions for an assignment.

    Args:
        assignment_id: ID of the assignment
        grading_mode: 'all_or_nothing' or 'proportional'
        numeric_tolerance: Tolerance for numeric answers

    Returns:
        Dict with grading statistics
    """
    try:
        assignment = Assignment.objects.get(id=assignment_id)
        service = GradingService()

        result = service.auto_grade_assignment(
            assignment,
            grading_mode=grading_mode,
            numeric_tolerance=numeric_tolerance
        )

        logger.info(
            f"Auto-grading task completed for assignment {assignment_id}: "
            f"{result['graded']} graded, {result['failed']} failed"
        )

        return {
            'success': True,
            'assignment_id': assignment_id,
            'statistics': result
        }

    except Assignment.DoesNotExist:
        logger.error(f"Assignment {assignment_id} not found")
        raise

    except Exception as exc:
        logger.error(f"Error in auto-grading task: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def auto_grade_submission_task(
    self,
    submission_id: int,
    grading_mode: str = 'proportional',
    numeric_tolerance: float = 0.05
) -> dict:
    """
    Async task to auto-grade a single submission.

    Args:
        submission_id: ID of the submission
        grading_mode: 'all_or_nothing' or 'proportional'
        numeric_tolerance: Tolerance for numeric answers

    Returns:
        Dict with grading result
    """
    try:
        submission = AssignmentSubmission.objects.get(id=submission_id)
        service = GradingService()

        result = service.auto_grade_submission(
            submission,
            grading_mode=grading_mode,
            numeric_tolerance=numeric_tolerance
        )

        logger.info(
            f"Auto-graded submission {submission_id}: "
            f"{result['total_score']}/{result['max_score']}"
        )

        return {
            'success': True,
            'submission_id': submission_id,
            'result': result
        }

    except AssignmentSubmission.DoesNotExist:
        logger.error(f"Submission {submission_id} not found")
        raise

    except Exception as exc:
        logger.error(f"Error in auto-grading task: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def batch_auto_grade_submissions(
    submission_ids: list,
    grading_mode: str = 'proportional',
    numeric_tolerance: float = 0.05
) -> dict:
    """
    Batch auto-grade multiple submissions.

    Args:
        submission_ids: List of submission IDs
        grading_mode: 'all_or_nothing' or 'proportional'
        numeric_tolerance: Tolerance for numeric answers

    Returns:
        Dict with batch statistics
    """
    service = GradingService()

    stats = {
        'total': len(submission_ids),
        'success': 0,
        'failed': 0,
        'errors': []
    }

    for submission_id in submission_ids:
        try:
            submission = AssignmentSubmission.objects.get(id=submission_id)
            service.auto_grade_submission(
                submission,
                grading_mode=grading_mode,
                numeric_tolerance=numeric_tolerance
            )
            stats['success'] += 1
        except AssignmentSubmission.DoesNotExist:
            stats['failed'] += 1
            stats['errors'].append({
                'submission_id': submission_id,
                'error': 'Submission not found'
            })
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({
                'submission_id': submission_id,
                'error': str(e)
            })
            logger.error(f"Error grading submission {submission_id}: {e}")

    return stats
