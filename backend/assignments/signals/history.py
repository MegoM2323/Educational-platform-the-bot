"""
T_ASSIGN_010: Django signals for assignment history and submission versioning.

Tracks:
- All Assignment field changes and creates AssignmentHistory records
- Submission resubmissions as SubmissionVersion records
- Changed_by context from request (passed through signals)
"""
import logging
import json
from datetime import datetime
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from assignments.models import (
    Assignment,
    AssignmentSubmission,
    AssignmentHistory,
    SubmissionVersion,
)

logger = logging.getLogger(__name__)


# Thread-local storage for request context (changed_by user)
import threading

_request_context = threading.local()


def set_changed_by_user(user):
    """Store the user who made the change in thread-local storage."""
    _request_context.changed_by_user = user


def get_changed_by_user():
    """Retrieve the user who made the change."""
    return getattr(_request_context, "changed_by_user", None)


def clear_changed_by_user():
    """Clear the stored user."""
    if hasattr(_request_context, "changed_by_user"):
        delattr(_request_context, "changed_by_user")


def serialize_changes(changes):
    """
    Convert non-JSON-serializable objects to strings for JSONField storage.

    Recursively processes dict/list and converts datetime objects to ISO format.
    """
    if isinstance(changes, dict):
        return {k: serialize_changes(v) for k, v in changes.items()}
    elif isinstance(changes, list):
        return [serialize_changes(item) for item in changes]
    elif isinstance(changes, datetime):
        return changes.isoformat()
    else:
        return changes


# Fields to track for assignment changes
ASSIGNMENT_TRACKED_FIELDS = [
    "title",
    "description",
    "instructions",
    "type",
    "status",
    "max_score",
    "time_limit",
    "attempts_limit",
    "start_date",
    "due_date",
    "difficulty_level",
    "tags",
    "late_submission_deadline",
    "late_penalty_type",
    "late_penalty_value",
    "penalty_frequency",
    "max_penalty",
    "allow_late_submission",
]


@receiver(pre_save, sender=Assignment)
def track_assignment_changes(sender, instance, **kwargs):
    """
    Pre-save signal to capture what fields changed in an Assignment.

    Stores the "old" state in a temporary attribute for comparison in post_save.
    """
    if not instance.pk:
        # New assignment, nothing to compare
        return

    try:
        old_instance = Assignment.objects.get(pk=instance.pk)
        instance._old_state = {
            field: getattr(old_instance, field) for field in ASSIGNMENT_TRACKED_FIELDS
        }
    except Assignment.DoesNotExist:
        instance._old_state = {}


@receiver(post_save, sender=Assignment)
def create_assignment_history(sender, instance, created, **kwargs):
    """
    Post-save signal to create AssignmentHistory when assignment is modified.

    Detects field changes and creates a history record with diff information.
    """
    if created:
        # New assignments don't need history until they're updated
        logger.info(f"Assignment {instance.id} created: {instance.title}")
        return

    # Skip if no old state was captured
    if not hasattr(instance, "_old_state"):
        return

    old_state = instance._old_state
    changes = {}
    fields_changed = []

    # Compare each tracked field
    for field in ASSIGNMENT_TRACKED_FIELDS:
        old_value = old_state.get(field)
        new_value = getattr(instance, field)

        # Only record actual changes
        if old_value != new_value:
            fields_changed.append(field)
            changes[field] = {"old": old_value, "new": new_value}

    # Only create history if something actually changed
    if not changes:
        logger.debug(f"Assignment {instance.id} saved but no tracked fields changed")
        return

    # Build human-readable summary
    summary_parts = []
    for field in fields_changed:
        old_val = changes[field]["old"]
        new_val = changes[field]["new"]
        summary_parts.append(f"{field}: '{old_val}' → '{new_val}'")
    change_summary = "; ".join(summary_parts)

    # Get the user who made the change
    changed_by = get_changed_by_user()

    try:
        # Serialize non-JSON-serializable objects (e.g., datetime) before saving
        serialized_changes = serialize_changes(changes)

        history = AssignmentHistory.objects.create(
            assignment=instance,
            changed_by=changed_by,
            changes_dict=serialized_changes,
            change_summary=change_summary,
            fields_changed=fields_changed,
        )
        logger.info(
            f"Created history record {history.id} for assignment {instance.id}: "
            f"Changed fields: {', '.join(fields_changed)}"
        )
    except Exception as e:
        logger.error(f"Error creating assignment history: {e}", exc_info=True)
    finally:
        clear_changed_by_user()
        # Clean up the temporary attribute
        if hasattr(instance, "_old_state"):
            delattr(instance, "_old_state")


@receiver(pre_save, sender=AssignmentSubmission)
def track_submission_submission(sender, instance, **kwargs):
    """
    Pre-save signal to prepare for submission versioning.

    Detects when a new submission is being made (version increment).
    """
    # Check if this is an update or a new submission
    if instance.pk:
        # This is an update to existing submission
        return

    # Mark as new submission for post_save handler
    instance._is_new_submission = True


@receiver(post_save, sender=AssignmentSubmission)
def create_submission_version(sender, instance, created, **kwargs):
    """
    Post-save signal to create SubmissionVersion for submissions.

    When a submission is created or updated, create a version record.
    """
    if not created:
        # Only create versions on submission creation, not on status updates
        return

    try:
        # Get the latest version number for this submission
        latest_version = (
            SubmissionVersion.objects.filter(submission=instance)
            .order_by("-version_number")
            .first()
        )

        version_number = (latest_version.version_number + 1) if latest_version else 1

        # Get previous version if it exists
        previous_version = latest_version if latest_version else None

        # Create the version record
        version = SubmissionVersion.objects.create(
            submission=instance,
            version_number=version_number,
            file=instance.file if instance.file else None,
            content=instance.content,
            is_final=True,  # New submissions are final by default
            submitted_by=instance.student,
            previous_version=previous_version,
        )

        # Mark previous version as not final
        if previous_version:
            previous_version.is_final = False
            previous_version.save(update_fields=["is_final"])

        logger.info(
            f"Created submission version {version.id} (v{version_number}) "
            f"for submission {instance.id} by {instance.student}"
        )
    except Exception as e:
        logger.error(f"Error creating submission version: {e}", exc_info=True)
    finally:
        # Clean up temporary attribute
        if hasattr(instance, "_is_new_submission"):
            delattr(instance, "_is_new_submission")
