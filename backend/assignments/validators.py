"""
T_ASN_001: Comprehensive due date validation for assignments.

Provides validation rules for assignment due dates including:
- Due date after creation date
- Due date not in past for new assignments
- Extension deadline validation
- Grace period handling
- Soft deadline enforcement
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class DueDateValidator:
    """
    Validates assignment due dates with support for soft deadlines and extensions.

    Features:
    - Validates due date is after creation date
    - Prevents past due dates for new assignments
    - Validates extension deadlines
    - Supports grace periods for late submissions
    - Clear Russian error messages
    """

    class DueDateError(ValidationError):
        """Custom validation error for due date issues"""
        pass

    @staticmethod
    def validate_due_date(due_date, created_at=None, assignment=None):
        """
        Validate a single due date.

        Args:
            due_date: DateTime object for the due date
            created_at: DateTime object for creation (defaults to now)
            assignment: Assignment instance for context (optional)

        Returns:
            None (raises ValidationError on failure)

        Raises:
            ValidationError: With field-specific error messages
        """
        if not due_date:
            raise ValidationError({'due_date': 'Дата сдачи обязательна'})

        # Use current time if created_at not provided
        if created_at is None:
            created_at = timezone.now()

        # Check due_date is after created_at
        if due_date <= created_at:
            raise ValidationError({
                'due_date': 'Дата сдачи должна быть позже даты создания задания'
            })

        # Check due_date is not in the past (for new assignments)
        # Allow 5 minutes grace for clock skew
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        if assignment is None or assignment.pk is None:
            # New assignment - prevent past due dates
            if due_date < five_minutes_ago:
                raise ValidationError({
                    'due_date': 'Дата сдачи не может быть в прошлом'
                })

    @staticmethod
    def validate_soft_deadlines(due_date, extension_deadline=None):
        """
        Validate soft deadline configuration (due_date and extension_deadline).

        Args:
            due_date: DateTime for primary due date
            extension_deadline: DateTime for extension deadline (optional)

        Returns:
            None (raises ValidationError on failure)

        Raises:
            ValidationError: With field-specific errors
        """
        if not due_date:
            raise ValidationError({'due_date': 'Дата сдачи обязательна'})

        # If extension deadline is provided, validate it
        if extension_deadline:
            if extension_deadline <= due_date:
                raise ValidationError({
                    'late_submission_deadline':
                    'Крайний срок для поздней сдачи должен быть позже основной даты сдачи'
                })

            # Extension deadline should not be too far in future (max 30 days)
            max_extension = due_date + timedelta(days=30)
            if extension_deadline > max_extension:
                raise ValidationError({
                    'late_submission_deadline':
                    'Крайний срок не может быть позже чем через 30 дней от основной даты сдачи'
                })

    @staticmethod
    def validate_extension_deadline(
        due_date,
        extension_deadline,
        current_time=None,
        allow_future_only=False
    ):
        """
        Validate extension deadline logic.

        Args:
            due_date: DateTime for primary due date
            extension_deadline: DateTime for extension deadline
            current_time: Current time (defaults to now)
            allow_future_only: If True, deadline must be in future

        Returns:
            None (raises ValidationError on failure)

        Raises:
            ValidationError: With detailed error messages
        """
        if current_time is None:
            current_time = timezone.now()

        # Basic structure validation
        if extension_deadline <= due_date:
            raise ValidationError({
                'late_submission_deadline':
                'Крайний срок должен быть позже основной даты сдачи'
            })

        # Validate extension deadline is not in past (if require future dates)
        if allow_future_only and extension_deadline < current_time:
            raise ValidationError({
                'late_submission_deadline':
                'Крайний срок не может быть в прошлом'
            })

        # Validate reasonable extension window (not more than 30 days)
        extension_days = (extension_deadline - due_date).days
        if extension_days > 30:
            raise ValidationError({
                'late_submission_deadline':
                f'Период расширения не может превышать 30 дней (указано: {extension_days} дней)'
            })

    @staticmethod
    def validate_grace_period(
        due_date,
        grace_period_minutes=0,
        late_submission_deadline=None
    ):
        """
        Validate grace period configuration.

        Grace period is a buffer after due_date where submissions are still on-time.

        Args:
            due_date: DateTime for due date
            grace_period_minutes: Grace period in minutes (0-60 allowed)
            late_submission_deadline: Optional hard deadline for all submissions

        Returns:
            None (raises ValidationError on failure)

        Raises:
            ValidationError: With field-specific errors
        """
        if not due_date:
            raise ValidationError({'due_date': 'Дата сдачи обязательна'})

        # Validate grace period is reasonable (0-60 minutes)
        if grace_period_minutes < 0:
            raise ValidationError({
                'grace_period_minutes': 'Период отсрочки не может быть отрицательным'
            })

        if grace_period_minutes > 60:
            raise ValidationError({
                'grace_period_minutes': 'Период отсрочки не может превышать 60 минут'
            })

        # If we have both grace period and extension deadline, ensure they don't overlap badly
        if late_submission_deadline and grace_period_minutes > 0:
            grace_end = due_date + timedelta(minutes=grace_period_minutes)
            if grace_end > late_submission_deadline:
                raise ValidationError({
                    'grace_period_minutes':
                    'Период отсрочки выходит за пределы крайнего срока поздней сдачи'
                })

    @staticmethod
    def validate_dates_for_submission(
        assignment,
        current_time=None,
        check_allow_late=True
    ):
        """
        Validate if submission is allowed based on current time and deadlines.

        Returns submission status: 'on_time', 'late_allowed', 'late_blocked', or raises error.

        Args:
            assignment: Assignment instance
            current_time: Current time (defaults to now)
            check_allow_late: Whether to check allow_late_submissions flag

        Returns:
            dict with keys:
            - status: 'on_time' | 'late_allowed' | 'late_blocked'
            - message: Human-readable message
            - is_late: Boolean
            - days_late: Float (days past due_date)
            - extension_available: Boolean

        Raises:
            ValidationError: If assignment dates are invalid
        """
        if not assignment:
            raise ValidationError('Задание не найдено')

        if not assignment.due_date:
            raise ValidationError({
                'due_date': 'У задания не установлена дата сдачи'
            })

        if current_time is None:
            current_time = timezone.now()

        result = {
            'status': 'on_time',
            'message': 'Сдача в срок',
            'is_late': False,
            'days_late': 0,
            'extension_available': False
        }

        # Check if submission is late
        if current_time > assignment.due_date:
            result['is_late'] = True
            # Calculate days late
            delta = current_time - assignment.due_date
            result['days_late'] = delta.total_seconds() / (24 * 3600)

            # Check if late submission is allowed
            if assignment.allow_late_submission:
                # Check if extension deadline exists and is still valid
                if assignment.late_submission_deadline:
                    if current_time <= assignment.late_submission_deadline:
                        result['status'] = 'late_allowed'
                        result['message'] = 'Поздняя сдача разрешена (до крайнего срока)'
                        result['extension_available'] = True
                    else:
                        result['status'] = 'late_blocked'
                        result['message'] = 'Крайний срок для сдачи истёк'
                else:
                    # No hard deadline, late allowed indefinitely
                    result['status'] = 'late_allowed'
                    result['message'] = 'Поздняя сдача разрешена'
                    result['extension_available'] = True
            else:
                result['status'] = 'late_blocked'
                result['message'] = 'Поздние сдачи не разрешены'

        return result

    @staticmethod
    def check_deadline_passed(due_date, current_time=None):
        """
        Simple check if deadline has passed.

        Args:
            due_date: DateTime for due date
            current_time: Current time (defaults to now)

        Returns:
            Boolean: True if deadline has passed
        """
        if current_time is None:
            current_time = timezone.now()

        return current_time > due_date

    @staticmethod
    def get_time_remaining(due_date, current_time=None):
        """
        Get time remaining until due date.

        Args:
            due_date: DateTime for due date
            current_time: Current time (defaults to now)

        Returns:
            dict with:
            - remaining_seconds: Total seconds remaining (negative if overdue)
            - remaining_days: Days remaining (can be fractional)
            - is_overdue: Boolean
            - hours_remaining: Hours in current day
            - is_due_today: Boolean
        """
        if current_time is None:
            current_time = timezone.now()

        delta = due_date - current_time
        remaining_seconds = delta.total_seconds()
        remaining_days = remaining_seconds / (24 * 3600)

        return {
            'remaining_seconds': int(remaining_seconds),
            'remaining_days': round(remaining_days, 2),
            'is_overdue': remaining_seconds < 0,
            'hours_remaining': round(remaining_seconds / 3600, 1),
            'is_due_today': (
                due_date.date() == current_time.date()
                if remaining_seconds >= 0
                else False
            )
        }


# Serializer field validators (for use with DRF serializers)

def validate_due_date_field(value):
    """
    DRF field validator for due_date field.

    Usage in serializer:
    due_date = DateTimeField(validators=[validate_due_date_field])
    """
    try:
        DueDateValidator.validate_due_date(value)
    except ValidationError as e:
        # Re-raise with DRF-compatible format
        raise ValidationError(str(e.message) if hasattr(e, 'message') else str(e))


def validate_extension_deadline_field(due_date):
    """
    Serializer-level validator for extension deadline.

    Usage in serializer:
    def validate(self, data):
        validate_extension_deadline_field(data.get('due_date'))
        return data
    """
    def validator(value):
        if value is None:
            return

        try:
            DueDateValidator.validate_extension_deadline(due_date, value)
        except ValidationError as e:
            raise ValidationError(str(e.message) if hasattr(e, 'message') else str(e))

    return validator


def validate_soft_deadlines_serializer(serializer, data):
    """
    Complete serializer validator for soft deadlines.

    Args:
        serializer: The serializer instance
        data: The validated data dict

    Raises:
        ValidationError: If deadlines are invalid
    """
    due_date = data.get('due_date')
    extension_deadline = data.get('late_submission_deadline')

    if due_date:
        try:
            DueDateValidator.validate_soft_deadlines(due_date, extension_deadline)
        except ValidationError as e:
            # Flatten the error dict for serializer
            errors = e.error_dict if hasattr(e, 'error_dict') else {'due_date': str(e)}
            raise ValidationError(errors)
