"""
T_ASN_008: Assignment cloning service

Service for handling assignment cloning with validation, permissions, and audit logging.
"""

import logging
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import Assignment
from core.audit import AuditService

logger = logging.getLogger(__name__)


class AssignmentCloningService:
    """
    Service for cloning assignments with full validation and audit trail.

    Features:
    - Clone assignment with all questions and options
    - Optional title and due date customization
    - Question randomization
    - Permission validation
    - Audit logging
    - Atomic transactions
    """

    @staticmethod
    def validate_clone_permission(assignment: Assignment, user):
        """
        Validate that user has permission to clone the assignment.

        Only the assignment creator can clone.

        Args:
            assignment: Assignment to clone
            user: User attempting to clone

        Returns:
            True if authorized

        Raises:
            PermissionError: If user is not the assignment creator
        """
        if assignment.author != user:
            raise PermissionError(
                f"User {user.id} cannot clone assignment {assignment.id} "
                f"created by {assignment.author.id}"
            )
        return True

    @staticmethod
    def validate_clone_params(
        assignment: Assignment,
        new_title: str = None,
        new_due_date: datetime = None,
        randomize_questions: bool = False
    ):
        """
        Validate cloning parameters.

        Args:
            assignment: Assignment to validate
            new_title: Optional new title
            new_due_date: Optional new due date
            randomize_questions: Whether to randomize questions

        Returns:
            Tuple of (is_valid, errors)

        Raises:
            ValidationError: If parameters are invalid
        """
        errors = {}

        # Validate title length
        if new_title:
            if len(new_title) > 200:
                errors['title'] = 'Title must be 200 characters or less'
            if len(new_title.strip()) == 0:
                errors['title'] = 'Title cannot be empty'

        # Validate due date
        if new_due_date:
            if new_due_date < timezone.now():
                errors['due_date'] = 'Due date cannot be in the past'

        # Validate question existence
        if not assignment.questions.exists():
            logger.warning(f"Assignment {assignment.id} has no questions to clone")

        if errors:
            raise ValidationError(errors)

        return True

    @staticmethod
    @transaction.atomic
    def clone_assignment(
        assignment: Assignment,
        user,
        new_title: str = None,
        new_due_date: datetime = None,
        randomize_questions: bool = False
    ) -> Assignment:
        """
        Clone an assignment with all questions and options.

        Args:
            assignment: Assignment to clone
            user: User performing the clone
            new_title: Optional new title for cloned assignment
            new_due_date: Optional new due date
            randomize_questions: Whether to randomize question order

        Returns:
            New cloned Assignment instance

        Raises:
            PermissionError: If user is not assignment creator
            ValidationError: If parameters are invalid
        """
        # Validate permissions
        AssignmentCloningService.validate_clone_permission(assignment, user)

        # Validate parameters
        AssignmentCloningService.validate_clone_params(
            assignment,
            new_title=new_title,
            new_due_date=new_due_date,
            randomize_questions=randomize_questions
        )

        try:
            # Use model's clone method
            cloned_assignment = assignment.clone(
                cloner=user,
                new_title=new_title,
                new_due_date=new_due_date,
                randomize_questions=randomize_questions
            )

            # Log the cloning action
            logger.info(
                f"Assignment cloned: source={assignment.id} '{assignment.title}', "
                f"clone={cloned_assignment.id} '{cloned_assignment.title}', "
                f"user={user.id}, randomized={randomize_questions}"
            )

            return cloned_assignment

        except Exception as e:
            logger.error(
                f"Error cloning assignment {assignment.id}: {str(e)}"
            )
            raise

    @staticmethod
    def get_clone_suggestions(assignment: Assignment) -> dict:
        """
        Get suggestions for cloning (next semester dates, etc).

        Args:
            assignment: Assignment to get suggestions for

        Returns:
            Dictionary with clone suggestions
        """
        from dateutil.relativedelta import relativedelta

        suggestions = {
            'suggested_title': f"Copy of {assignment.title}",
            'current_due_date': assignment.due_date,
            'suggested_new_due_date': assignment.due_date + relativedelta(months=1),
            'questions_count': assignment.questions.count(),
            'has_rubric': assignment.rubric is not None,
        }

        return suggestions
