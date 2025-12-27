"""
T_ASN_001: Practical examples of using DueDateValidator

This file demonstrates common usage patterns for the assignment due date validator.
"""

from django.utils import timezone
from datetime import timedelta
from assignments.models import Assignment
from assignments.validators import DueDateValidator


# ============================================================================
# EXAMPLE 1: Creating an assignment with validation
# ============================================================================

def example_create_assignment_valid():
    """Create assignment with valid dates."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    teacher = User.objects.get(role='teacher')

    now = timezone.now()

    # All dates are valid
    assignment = Assignment(
        title="Math Homework",
        description="Chapter 5 exercises",
        instructions="Complete problems 1-10",
        author=teacher,
        type="homework",
        max_score=100,
        start_date=now + timedelta(hours=1),  # Start in 1 hour
        due_date=now + timedelta(days=7),    # Due in 7 days
        allow_late_submission=True,
        late_submission_deadline=now + timedelta(days=14),  # Late until 14 days
    )

    # This will pass validation in serializer
    return assignment


def example_create_assignment_with_grace_period():
    """Create assignment with grace period for late submissions."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    teacher = User.objects.get(role='teacher')

    now = timezone.now()

    # Assignment with 15-minute grace period
    assignment = Assignment(
        title="Physics Test",
        description="Chapter 3 test",
        instructions="Time limit: 60 minutes",
        author=teacher,
        type="test",
        max_score=100,
        start_date=now + timedelta(hours=1),
        due_date=now + timedelta(days=7),
        allow_late_submission=True,
        late_submission_deadline=now + timedelta(days=7, minutes=15),  # Grace period
    )

    return assignment


# ============================================================================
# EXAMPLE 2: Validating dates at different levels
# ============================================================================

def example_validate_due_date_basic():
    """Basic due date validation."""
    now = timezone.now()
    future_date = now + timedelta(days=7)
    past_date = now - timedelta(days=1)

    # This passes
    try:
        DueDateValidator.validate_due_date(future_date, now)
        print("✓ Future due date is valid")
    except Exception as e:
        print(f"✗ Error: {e}")

    # This fails
    try:
        DueDateValidator.validate_due_date(past_date, now)
        print("✓ Past due date is valid")
    except Exception as e:
        print(f"✗ Error: {e}")
        # Output: "✗ Error: {'due_date': ['Дата сдачи не может быть в прошлом']}"


def example_validate_soft_deadlines():
    """Validate soft deadline structure."""
    now = timezone.now()
    due_date = now + timedelta(days=7)
    extension_deadline = due_date + timedelta(days=5)

    # Valid configuration
    try:
        DueDateValidator.validate_soft_deadlines(due_date, extension_deadline)
        print("✓ Soft deadlines are valid")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Invalid: extension before due date
    invalid_extension = due_date - timedelta(days=1)
    try:
        DueDateValidator.validate_soft_deadlines(due_date, invalid_extension)
        print("✓ Invalid deadline configuration passed (unexpected!)")
    except Exception as e:
        print(f"✗ Error: {e}")
        # Output: "✗ Error: {'late_submission_deadline': [...]}"


# ============================================================================
# EXAMPLE 3: Checking submission status
# ============================================================================

def example_check_submission_status():
    """Check if submission is on-time or late."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    teacher = User.objects.get(role='teacher')

    now = timezone.now()

    # Assignment due yesterday
    assignment = Assignment.objects.create(
        title="Yesterday's Assignment",
        description="Test",
        instructions="Test",
        author=teacher,
        start_date=now - timedelta(days=2),
        due_date=now - timedelta(days=1),
        allow_late_submission=True,
        late_submission_deadline=now + timedelta(days=5),  # But late allowed for 5 more days
    )

    # Check submission status at current time
    result = DueDateValidator.validate_dates_for_submission(assignment, now)

    print(f"Status: {result['status']}")              # 'late_allowed'
    print(f"Is late: {result['is_late']}")            # True
    print(f"Days late: {result['days_late']:.2f}")    # ~1.0
    print(f"Message: {result['message']}")            # 'Поздняя сдача разрешена'

    if result['status'] == 'on_time':
        print("✓ Submission is on-time")
    elif result['status'] == 'late_allowed':
        print("⚠ Submission is late but allowed")
        # Apply late penalty here
    elif result['status'] == 'late_blocked':
        print("✗ Submission is not allowed (deadline passed)")
        # Reject submission


def example_check_submission_blocked():
    """Check when submission is blocked."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    teacher = User.objects.get(role='teacher')

    now = timezone.now()

    # Assignment that doesn't allow late submissions
    assignment = Assignment.objects.create(
        title="Strict Deadline Assignment",
        description="Test",
        instructions="Test",
        author=teacher,
        start_date=now - timedelta(days=2),
        due_date=now - timedelta(hours=1),  # Due 1 hour ago
        allow_late_submission=False,        # No late submissions allowed
    )

    result = DueDateValidator.validate_dates_for_submission(assignment, now)

    if result['status'] == 'late_blocked':
        print(f"✗ {result['message']}")  # 'Поздние сдачи не разрешены'
        # Reject the submission with 403 Forbidden


# ============================================================================
# EXAMPLE 4: Time remaining calculations
# ============================================================================

def example_get_time_remaining():
    """Get time remaining until deadline."""
    now = timezone.now()
    due_date = now + timedelta(days=7, hours=3, minutes=30)

    time_info = DueDateValidator.get_time_remaining(due_date, now)

    print(f"Days remaining: {time_info['remaining_days']}")      # 7.15
    print(f"Hours remaining: {time_info['hours_remaining']}")    # 171.5
    print(f"Seconds remaining: {time_info['remaining_seconds']}") # 616200
    print(f"Is overdue: {time_info['is_overdue']}")              # False
    print(f"Is due today: {time_info['is_due_today']}")          # False


def example_format_time_remaining_for_ui():
    """Format time remaining for user display."""
    now = timezone.now()
    due_date = now + timedelta(days=7, hours=3)

    time_info = DueDateValidator.get_time_remaining(due_date, now)

    if time_info['is_overdue']:
        print("⏰ DEADLINE PASSED")
    elif time_info['is_due_today']:
        hours = time_info['hours_remaining']
        print(f"⏰ Due today in {hours:.1f} hours")
    elif time_info['remaining_days'] < 1:
        hours = time_info['hours_remaining']
        print(f"⏰ Due in {hours:.1f} hours")
    else:
        days = int(time_info['remaining_days'])
        print(f"📅 Due in {days} days")


# ============================================================================
# EXAMPLE 5: Processing submissions with validation
# ============================================================================

def example_process_submission(assignment, student):
    """Process a student submission with validation."""
    from assignments.models import AssignmentSubmission

    now = timezone.now()

    # Check if submission is allowed
    validation_result = DueDateValidator.validate_dates_for_submission(assignment, now)

    if validation_result['status'] == 'late_blocked':
        # Reject submission
        return {
            'success': False,
            'error': validation_result['message'],
            'status_code': 403
        }

    # Create submission
    submission = AssignmentSubmission(
        assignment=assignment,
        student=student,
        content="Student's answer",
        is_late=validation_result['is_late'],
        days_late=validation_result['days_late'],
    )
    submission.save()

    return {
        'success': True,
        'submission_id': submission.id,
        'is_late': submission.is_late,
        'days_late': submission.days_late,
        'message': validation_result['message']
    }


# ============================================================================
# EXAMPLE 6: Creating assignments via API with validation
# ============================================================================

def example_api_assignment_creation():
    """
    Example of assignment creation via REST API.

    The AssignmentCreateSerializer will automatically validate dates:
    1. validate_due_date() checks due_date is in future
    2. validate() checks soft deadline structure
    """

    from rest_framework.test import APIClient

    client = APIClient()
    now = timezone.now()

    # Valid request
    payload = {
        'title': 'API Assignment',
        'description': 'Created via API',
        'instructions': 'Test',
        'type': 'homework',
        'max_score': 100,
        'start_date': (now + timedelta(hours=1)).isoformat(),
        'due_date': (now + timedelta(days=7)).isoformat(),
        'allow_late_submission': True,
        'late_submission_deadline': (now + timedelta(days=14)).isoformat(),
    }

    # response = client.post('/api/assignments/', payload, format='json')
    # Returns: 201 CREATED with assignment data

    # Invalid request: due date in past
    invalid_payload = {
        **payload,
        'due_date': (now - timedelta(hours=1)).isoformat(),  # Past date!
    }

    # response = client.post('/api/assignments/', invalid_payload, format='json')
    # Returns: 400 BAD REQUEST with:
    # {'due_date': ['Дата сдачи не может быть в прошлом']}


# ============================================================================
# EXAMPLE 7: Batch operations with validation
# ============================================================================

def example_bulk_assignment_creation():
    """Create multiple assignments with validation."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    teacher = User.objects.get(role='teacher')

    now = timezone.now()
    assignments_data = [
        {
            'title': 'Week 1 Assignment',
            'due_offset_days': 7,
            'extension_days': 3,
        },
        {
            'title': 'Week 2 Assignment',
            'due_offset_days': 14,
            'extension_days': 3,
        },
        {
            'title': 'Week 3 Assignment',
            'due_offset_days': 21,
            'extension_days': 3,
        },
    ]

    created_assignments = []

    for data in assignments_data:
        due_date = now + timedelta(days=data['due_offset_days'])
        extension_deadline = due_date + timedelta(days=data['extension_days'])

        # Validate dates before creating
        try:
            DueDateValidator.validate_soft_deadlines(due_date, extension_deadline)

            assignment = Assignment.objects.create(
                title=data['title'],
                description='Bulk created',
                instructions='Test',
                author=teacher,
                start_date=now,
                due_date=due_date,
                allow_late_submission=True,
                late_submission_deadline=extension_deadline,
            )

            created_assignments.append(assignment)
            print(f"✓ Created: {assignment.title}")

        except Exception as e:
            print(f"✗ Failed: {data['title']} - {e}")

    return created_assignments


# ============================================================================
# EXAMPLE 8: Deadline management utilities
# ============================================================================

def example_check_deadline_passed():
    """Check if a deadline has passed."""
    now = timezone.now()

    due_date_passed = now - timedelta(hours=2)
    due_date_future = now + timedelta(days=7)

    # Deadline in past
    if DueDateValidator.check_deadline_passed(due_date_passed, now):
        print("✗ Deadline has passed")

    # Deadline in future
    if not DueDateValidator.check_deadline_passed(due_date_future, now):
        print("✓ Deadline is in future")


def example_find_overdue_assignments():
    """Find all overdue assignments."""
    now = timezone.now()

    # Get all assignments that are past due
    assignments = Assignment.objects.all()

    overdue = []
    for assignment in assignments:
        if DueDateValidator.check_deadline_passed(assignment.due_date, now):
            time_info = DueDateValidator.get_time_remaining(assignment.due_date, now)
            overdue.append({
                'assignment': assignment,
                'days_overdue': abs(time_info['remaining_days']),
                'extension_available': bool(assignment.late_submission_deadline),
            })

    return overdue


# ============================================================================
# EXAMPLE 9: Error handling
# ============================================================================

def example_handle_validation_errors():
    """Handle validation errors gracefully."""
    from django.core.exceptions import ValidationError

    now = timezone.now()

    try:
        # Try to validate an invalid due date
        DueDateValidator.validate_due_date(now - timedelta(days=1), now)

    except ValidationError as e:
        # e.error_dict contains field-specific errors
        if hasattr(e, 'error_dict'):
            for field, errors in e.error_dict.items():
                print(f"Field: {field}")
                for error in errors:
                    print(f"  Error: {error.message}")
        else:
            print(f"Validation error: {e}")


# ============================================================================
# EXAMPLE 10: Serializer-level integration
# ============================================================================

def example_serializer_validation_integration():
    """
    How validation is integrated in AssignmentCreateSerializer.

    The serializer automatically calls:
    1. validate_due_date() for field validation
    2. validate() for object-level validation

    These methods use DueDateValidator internally.
    """

    from rest_framework import serializers
    from assignments.serializers import AssignmentCreateSerializer

    serializer = AssignmentCreateSerializer(data={
        'title': 'Test',
        'description': 'Test',
        'instructions': 'Test',
        'type': 'homework',
        'max_score': 100,
        'start_date': timezone.now().isoformat(),
        'due_date': (timezone.now() - timezone.timedelta(hours=1)).isoformat(),  # Invalid!
    })

    if not serializer.is_valid():
        # serializer.errors contains validation errors
        # {'due_date': ['Дата сдачи не может быть в прошлом']}
        print(f"Validation errors: {serializer.errors}")
    else:
        assignment = serializer.save()
        print(f"Assignment created: {assignment}")


if __name__ == '__main__':
    print("These are examples for reference.")
    print("Do not run this file directly - use as documentation reference.")
