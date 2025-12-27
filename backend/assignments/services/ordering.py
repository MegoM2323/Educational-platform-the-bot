"""
T_ASN_002: Assignment Question Ordering Service

Handles question ordering operations including:
- Question ordering validation
- Bulk reordering with transaction safety
- Auto-renumbering on deletion
- Randomization support
"""

from django.db import transaction, models
from django.core.exceptions import ValidationError
from assignments.models import AssignmentQuestion, Assignment
import logging
import random

logger = logging.getLogger(__name__)


class QuestionOrderingService:
    """Service for managing question ordering in assignments"""

    @staticmethod
    def validate_unique_order(assignment_id, order, exclude_question_id=None):
        """
        Validate that order is unique for an assignment

        Args:
            assignment_id: ID of the assignment
            order: Order value to check
            exclude_question_id: ID of question to exclude from check (for updates)

        Returns:
            tuple: (is_valid, error_message)
        """
        query = AssignmentQuestion.objects.filter(
            assignment_id=assignment_id,
            order=order
        )

        if exclude_question_id:
            query = query.exclude(id=exclude_question_id)

        if query.exists():
            return False, f"Order {order} is already used in this assignment"

        return True, None

    @staticmethod
    def get_next_order(assignment_id):
        """
        Get the next available order number for an assignment

        Args:
            assignment_id: ID of the assignment

        Returns:
            int: Next order number (max order + 1, or 1 if no questions)
        """
        max_order = AssignmentQuestion.objects.filter(
            assignment_id=assignment_id
        ).aggregate(models.Max('order'))['order__max']

        return (max_order or 0) + 1

    @staticmethod
    @transaction.atomic
    def reorder_questions(assignment_id, reorder_data):
        """
        Bulk reorder questions within an assignment

        Args:
            assignment_id: ID of the assignment
            reorder_data: List of dicts with 'id' and 'order' keys

        Returns:
            dict: Result with status and affected questions

        Raises:
            ValidationError: If validation fails
        """
        # Validate assignment exists
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            raise ValidationError(f"Assignment {assignment_id} not found")

        # Extract question IDs and validate they exist
        question_ids = [item['id'] for item in reorder_data]
        questions = list(AssignmentQuestion.objects.filter(
            assignment=assignment,
            id__in=question_ids
        ))

        if len(questions) != len(question_ids):
            raise ValidationError("Some questions do not exist in this assignment")

        # Create mapping of question_id -> new order
        reorder_map = {item['id']: item['order'] for item in reorder_data}

        # Validate no duplicate orders
        orders = list(reorder_map.values())
        if len(orders) != len(set(orders)):
            raise ValidationError("Duplicate order values provided")

        # Update orders in batch
        updated_count = 0
        for question in questions:
            new_order = reorder_map[question.id]
            question.order = new_order
            question.save(update_fields=['order', 'updated_at'])
            updated_count += 1

        logger.info(
            f"Reordered {updated_count} questions in assignment {assignment_id}"
        )

        return {
            'status': 'success',
            'assignment_id': assignment_id,
            'updated_count': updated_count,
            'questions': [
                {'id': q.id, 'order': reorder_map[q.id]}
                for q in questions
            ]
        }

    @staticmethod
    @transaction.atomic
    def auto_renumber_after_deletion(assignment_id):
        """
        Auto-renumber questions after one is deleted to prevent gaps

        Args:
            assignment_id: ID of the assignment

        Returns:
            dict: Result with renumbering details
        """
        questions = AssignmentQuestion.objects.filter(
            assignment_id=assignment_id
        ).order_by('order')

        updates = 0
        for index, question in enumerate(questions):
            new_order = index + 1
            if question.order != new_order:
                question.order = new_order
                question.save(update_fields=['order', 'updated_at'])
                updates += 1

        logger.info(
            f"Auto-renumbered {updates} questions in assignment {assignment_id}"
        )

        return {
            'status': 'success',
            'assignment_id': assignment_id,
            'renumbered_count': updates
        }

    @staticmethod
    def get_ordered_questions(assignment_id, randomize=False, student_id=None):
        """
        Get questions for an assignment in order
        Optionally randomize for per-student randomization

        Args:
            assignment_id: ID of the assignment
            randomize: Whether to randomize for this student
            student_id: ID of the student (for seeding randomization)

        Returns:
            QuerySet or list: Questions ordered by order field
        """
        questions = AssignmentQuestion.objects.filter(
            assignment_id=assignment_id
        ).order_by('order')

        if randomize and student_id:
            # Convert to list for shuffling
            question_list = list(questions)

            # Use student_id as seed for consistent randomization per student
            random.Random(student_id).shuffle(question_list)

            return question_list

        return questions

    @staticmethod
    def validate_order_sequence(assignment_id, allow_gaps=False):
        """
        Validate question ordering for an assignment

        Args:
            assignment_id: ID of the assignment
            allow_gaps: Whether gaps in ordering are allowed

        Returns:
            dict: Validation result with any issues found
        """
        questions = AssignmentQuestion.objects.filter(
            assignment_id=assignment_id
        ).order_by('order').values('id', 'order')

        if not questions:
            return {'valid': True, 'total_questions': 0}

        issues = []
        orders = [q['order'] for q in questions]

        # Check for duplicates
        if len(orders) != len(set(orders)):
            issues.append("Duplicate order values detected")

        # Check for gaps if strict ordering required
        if not allow_gaps:
            expected = list(range(1, len(orders) + 1))
            if orders != expected:
                issues.append(
                    f"Order sequence has gaps. Expected {expected}, got {orders}"
                )

        return {
            'valid': len(issues) == 0,
            'total_questions': len(questions),
            'issues': issues
        }
