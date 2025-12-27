"""
T_ASN_003: Assignment Attempt Tracking Service

Handles creation, validation, and management of assignment attempts.
Supports multiple submission attempts with attempt limiting and deadline validation.
"""

from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import AssignmentAttempt, AssignmentSubmission, Assignment


class AttemptValidationService:
    """Service for validating attempt creation and management."""

    @staticmethod
    def can_create_attempt(assignment: Assignment, student_id: int) -> tuple[bool, str]:
        """
        Check if a student can create a new attempt for the assignment.

        Returns:
            tuple: (can_create: bool, message: str)
        """
        # Check if assignment allows more attempts
        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student_id=student_id
        ).first()

        if not submission:
            return False, "No submission found for this student."

        # Get existing attempts count
        attempts_count = AssignmentAttempt.objects.filter(
            submission=submission
        ).count()

        # Check against attempt limit
        if attempts_count >= assignment.attempts_limit:
            return (
                False,
                f"Maximum attempts ({assignment.attempts_limit}) exceeded."
            )

        # Check deadline if assignment is still open
        now = timezone.now()
        if assignment.due_date and now > assignment.due_date:
            if not assignment.allow_late_submission:
                return False, "Assignment is closed and late submissions are not allowed."

        return True, "Ready to submit"

    @staticmethod
    def get_current_attempt_number(submission: AssignmentSubmission) -> int:
        """Get the next attempt number for a submission."""
        latest_attempt = AssignmentAttempt.objects.filter(
            submission=submission
        ).order_by('-attempt_number').first()

        if latest_attempt:
            return latest_attempt.attempt_number + 1
        return 1

    @staticmethod
    def is_deadline_exceeded(assignment: Assignment) -> bool:
        """Check if the assignment deadline has passed."""
        if not assignment.due_date:
            return False
        return timezone.now() > assignment.due_date

    @staticmethod
    def validate_attempt_submission(assignment: Assignment, student_id: int) -> dict:
        """
        Comprehensive validation for attempt submission.

        Returns:
            dict: {
                'is_valid': bool,
                'error': str or None,
                'attempt_number': int,
                'is_late': bool,
                'submission': AssignmentSubmission or None
            }
        """
        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student_id=student_id
        ).first()

        if not submission:
            return {
                'is_valid': False,
                'error': 'No submission found for this student',
                'attempt_number': None,
                'is_late': False,
                'submission': None
            }

        # Check if more attempts are allowed
        can_create, message = AttemptValidationService.can_create_attempt(
            assignment,
            student_id
        )

        if not can_create:
            return {
                'is_valid': False,
                'error': message,
                'attempt_number': None,
                'is_late': False,
                'submission': submission
            }

        # Check if submission is late
        is_late = timezone.now() > assignment.due_date if assignment.due_date else False

        return {
            'is_valid': True,
            'error': None,
            'attempt_number': AttemptValidationService.get_current_attempt_number(submission),
            'is_late': is_late,
            'submission': submission
        }


class AttemptCreationService:
    """Service for creating and managing assignment attempts."""

    @staticmethod
    @transaction.atomic
    def create_attempt(
        submission: AssignmentSubmission,
        content: str,
        file=None
    ) -> AssignmentAttempt:
        """
        Create a new assignment attempt with transaction safety.

        Args:
            submission: The assignment submission
            content: The submission content/answer
            file: Optional file attachment

        Returns:
            AssignmentAttempt: The created attempt

        Raises:
            ValidationError: If attempt cannot be created
        """
        assignment = submission.assignment
        student = submission.student

        # Validate before creating
        validation = AttemptValidationService.validate_attempt_submission(
            assignment,
            student.id
        )

        if not validation['is_valid']:
            raise ValidationError(validation['error'])

        attempt_number = validation['attempt_number']

        # Create the attempt
        attempt = AssignmentAttempt.objects.create(
            submission=submission,
            assignment=assignment,
            student=student,
            attempt_number=attempt_number,
            content=content,
            file=file,
            status=AssignmentAttempt.Status.SUBMITTED,
            max_score=assignment.max_score
        )

        return attempt

    @staticmethod
    @transaction.atomic
    def grade_attempt(
        attempt: AssignmentAttempt,
        score: int,
        feedback: str = "",
        status: str = AssignmentAttempt.Status.GRADED
    ) -> AssignmentAttempt:
        """
        Grade an assignment attempt.

        Args:
            attempt: The attempt to grade
            score: The numeric score
            feedback: Optional feedback
            status: New status (defaults to GRADED)

        Returns:
            AssignmentAttempt: The updated attempt
        """
        attempt.score = score
        attempt.feedback = feedback
        attempt.status = status
        attempt.graded_at = timezone.now()
        attempt.save(update_fields=['score', 'feedback', 'status', 'graded_at'])

        return attempt

    @staticmethod
    def get_attempt_history(submission: AssignmentSubmission):
        """Get all attempts for a submission ordered by attempt number."""
        return AssignmentAttempt.objects.filter(
            submission=submission
        ).order_by('attempt_number')

    @staticmethod
    def get_best_attempt(submission: AssignmentSubmission) -> AssignmentAttempt:
        """Get the best-scoring attempt for a submission."""
        return AssignmentAttempt.objects.filter(
            submission=submission,
            is_graded=True  # Only graded attempts
        ).order_by('-score').first()

    @staticmethod
    def get_latest_attempt(submission: AssignmentSubmission) -> AssignmentAttempt:
        """Get the most recent attempt for a submission."""
        return AssignmentAttempt.objects.filter(
            submission=submission
        ).order_by('-attempt_number').first()


class AttemptStatisticsService:
    """Service for gathering attempt statistics."""

    @staticmethod
    def get_attempt_stats(assignment: Assignment) -> dict:
        """
        Get statistics about attempts for an assignment.

        Returns:
            dict: Statistics including average attempts, completion rates, etc.
        """
        all_attempts = AssignmentAttempt.objects.filter(assignment=assignment)

        total_students = assignment.assigned_to.count()
        students_with_attempts = (
            all_attempts
            .values('student_id')
            .distinct()
            .count()
        )

        graded_attempts = all_attempts.filter(
            status=AssignmentAttempt.Status.GRADED
        )

        if graded_attempts.exists():
            avg_score = graded_attempts.aggregate(
                avg=models.Avg('score')
            )['avg'] or 0
            avg_attempts = (
                all_attempts
                .values('submission_id')
                .annotate(count=models.Count('id'))
                .aggregate(avg=models.Avg('count'))
            )['avg'] or 1
        else:
            avg_score = 0
            avg_attempts = 0

        return {
            'total_students': total_students,
            'students_with_attempts': students_with_attempts,
            'completion_rate': (
                (students_with_attempts / total_students * 100) if total_students > 0 else 0
            ),
            'total_attempts': all_attempts.count(),
            'graded_attempts': graded_attempts.count(),
            'average_score': round(avg_score, 2),
            'average_attempts_per_student': round(avg_attempts, 2),
        }

    @staticmethod
    def get_student_stats(submission: AssignmentSubmission) -> dict:
        """Get attempt statistics for a specific student."""
        attempts = AssignmentAttempt.objects.filter(submission=submission)

        if not attempts.exists():
            return {
                'total_attempts': 0,
                'graded_attempts': 0,
                'best_score': None,
                'latest_score': None,
                'completion_status': 'not_started'
            }

        graded = attempts.filter(status=AssignmentAttempt.Status.GRADED)
        latest = attempts.order_by('-attempt_number').first()
        best = graded.order_by('-score').first() if graded.exists() else None

        return {
            'total_attempts': attempts.count(),
            'graded_attempts': graded.count(),
            'best_score': best.score if best else None,
            'latest_score': latest.score if latest and latest.score else None,
            'completion_status': (
                'completed' if graded.exists() else 'in_progress'
            ),
            'latest_attempt_number': latest.attempt_number if latest else None
        }
