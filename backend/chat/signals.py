"""
Signal handlers for chat system.

Includes:
- Auto-creation of forum chats when SubjectEnrollment is created
- Pachca notifications for new forum messages
- Auto-add new users to general chat
"""

import logging
from django.db import transaction
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

try:
    from materials.models import SubjectEnrollment
except ImportError:
    SubjectEnrollment = None

from accounts.models import StudentProfile, ParentProfile
from .models import ChatRoom, Message, ChatParticipant
from .services.pachca_service import PachcaService

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=SubjectEnrollment)
def create_forum_chat_on_enrollment(
    sender, instance: SubjectEnrollment, created: bool, **kwargs
) -> None:
    """
    Automatically create forum chats when a student enrolls in a subject.

    Creates two chats:
    1. Student-Teacher chat (FORUM_SUBJECT type) - includes parent
    2. Student-Tutor chat if student has a tutor (FORUM_TUTOR type) - includes parent

    This signal is idempotent - uses get_or_create to prevent race conditions.
    Only triggers when a new enrollment is created, not on updates.

    Args:
        sender: SubjectEnrollment model class
        instance: The SubjectEnrollment instance being saved
        created: Boolean indicating if instance was just created
        **kwargs: Additional keyword arguments from signal
    """
    if not created:
        return

    # Verify that instance is actually a SubjectEnrollment
    # (sometimes post_save signals can be triggered incorrectly)
    if SubjectEnrollment is None or not isinstance(instance, SubjectEnrollment):
        return

    if not instance.teacher:
        logger.warning(
            f"SubjectEnrollment {instance.id} has no teacher assigned, skipping forum chat creation"
        )
        return

    try:
        # Get student profile for tutor and parent info
        student_profile: StudentProfile | None = None
        try:
            student_profile = StudentProfile.objects.select_related(
                "tutor", "parent"
            ).get(user=instance.student)
        except StudentProfile.DoesNotExist:
            logger.warning(
                f"StudentProfile not found for user {instance.student.id} during enrollment "
                f"{instance.id} for subject {instance.subject.id}"
            )

        subject_name = instance.get_subject_name()
        student_name = instance.student.get_full_name()
        teacher_name = instance.teacher.get_full_name()

        # Format: "{Subject} - {Student} ↔ {Teacher}"
        forum_chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"

        # Use transaction.atomic for consistency between ChatRoom and ChatParticipant
        with transaction.atomic():
            # Use get_or_create to prevent race conditions
            forum_chat, forum_created = ChatRoom.objects.get_or_create(
                type=ChatRoom.Type.FORUM_SUBJECT,
                enrollment=instance,
                defaults={
                    "name": forum_chat_name,
                    "created_by": instance.student,
                    "description": f"Forum for {subject_name} between {student_name} and {teacher_name}",
                },
            )

            # Collect all participants for this chat
            participants_to_add = [instance.student, instance.teacher]

            # Add parent if exists
            if student_profile and student_profile.parent:
                participants_to_add.append(student_profile.parent)

            # Add participants to M2M relation (idempotent - duplicates ignored)
            forum_chat.participants.add(*participants_to_add)

            # Create ChatParticipant records using bulk_create with ignore_conflicts
            participant_records = [
                ChatParticipant(room=forum_chat, user=user)
                for user in participants_to_add
            ]
            ChatParticipant.objects.bulk_create(
                participant_records, ignore_conflicts=True
            )

        if forum_created:
            logger.info(
                f"Created forum_subject chat '{forum_chat.name}' for enrollment {instance.id} "
                f"with {len(participants_to_add)} participants"
            )
        else:
            logger.info(
                f"Forum_subject chat already exists for enrollment {instance.id}, "
                f"ensured {len(participants_to_add)} participants"
            )

        # Create student-tutor forum chat if student has a tutor
        # Check TWO ways a student can have a tutor:
        # 1. Via StudentProfile.tutor (direct assignment)
        # 2. Via User.created_by_tutor (tutor who created the student)
        tutors_to_add = []
        if student_profile and student_profile.tutor:
            tutors_to_add.append(student_profile.tutor)
        if instance.student.created_by_tutor:
            tutors_to_add.append(instance.student.created_by_tutor)

        if tutors_to_add:
            # Remove duplicates (if tutor == created_by_tutor)
            unique_tutors = list({tutor.id: tutor for tutor in tutors_to_add}.values())

            # Build chat name using first tutor
            first_tutor = unique_tutors[0]
            tutor_name = first_tutor.get_full_name()
            tutor_chat_name = f"{subject_name} - {student_name} ↔ {tutor_name}"

            # Use transaction.atomic for consistency
            with transaction.atomic():
                # Use get_or_create to prevent race conditions
                tutor_chat, tutor_created = ChatRoom.objects.get_or_create(
                    type=ChatRoom.Type.FORUM_TUTOR,
                    enrollment=instance,
                    defaults={
                        "name": tutor_chat_name,
                        "created_by": instance.student,
                        "description": f"Forum for {subject_name} between {student_name} and {', '.join([t.get_full_name() for t in unique_tutors])}",
                    },
                )

                # Collect all participants for tutor chat
                tutor_participants = [instance.student] + unique_tutors

                # Add parent if exists
                if student_profile and student_profile.parent:
                    tutor_participants.append(student_profile.parent)

                # Add participants to M2M relation (idempotent)
                tutor_chat.participants.add(*tutor_participants)

                # Create ChatParticipant records using bulk_create with ignore_conflicts
                tutor_participant_records = [
                    ChatParticipant(room=tutor_chat, user=user)
                    for user in tutor_participants
                ]
                ChatParticipant.objects.bulk_create(
                    tutor_participant_records, ignore_conflicts=True
                )

            if tutor_created:
                logger.info(
                    f"Created forum_tutor chat '{tutor_chat.name}' for enrollment {instance.id} "
                    f"with {len(tutor_participants)} participants (tutors: {len(unique_tutors)})"
                )
            else:
                logger.info(
                    f"Forum_tutor chat already exists for enrollment {instance.id}, "
                    f"ensured {len(tutor_participants)} participants"
                )

    except Exception as e:
        logger.error(
            f"Error creating forum chats for SubjectEnrollment {instance.id}: {str(e)}",
            exc_info=True,
        )
        # Don't raise the exception - log it but let the enrollment creation succeed


@receiver(post_save, sender=Message)
def send_forum_notification(sender, instance: Message, created: bool, **kwargs) -> None:
    """
    Trigger Pachca notification when new forum message is created.

    Only triggers for forum chats (FORUM_SUBJECT and FORUM_TUTOR types).
    Runs asynchronously via Celery task - errors do not block message creation.

    Celery task handles:
    - Exponential backoff retry (3 attempts: 1min, 2min, 4min delays)
    - Structured logging with full context
    - Monitoring for repeated failures

    Args:
        sender: Message model class
        instance: The Message instance being saved
        created: Boolean indicating if instance was just created
        **kwargs: Additional keyword arguments from signal
    """
    if not created:
        return

    try:
        chat_room: ChatRoom | None = instance.room
        if not chat_room:
            logger.warning(
                f"Message {instance.id} has no associated ChatRoom",
                extra={"message_id": instance.id},
            )
            return

        # Only send notification for forum chats
        if chat_room.type not in (
            ChatRoom.Type.FORUM_SUBJECT,
            ChatRoom.Type.FORUM_TUTOR,
        ):
            return

        # Dispatch Celery task for async processing with retry
        from chat.tasks import send_pachca_forum_notification_task

        try:
            send_pachca_forum_notification_task.apply_async(
                args=[instance.id, chat_room.id],
                countdown=2,  # Wait 2 seconds before sending (debounce)
            )
            logger.info(
                f"Pachca notification task queued for message {instance.id} in chat {chat_room.id}",
                extra={
                    "message_id": instance.id,
                    "chat_room_id": chat_room.id,
                    "chat_type": chat_room.type,
                },
            )
        except Exception as e:
            # Celery/Redis connection failed - log warning but don't block message sending
            # Message is already saved and broadcast via WebSocket, notification is optional
            logger.warning(
                f"Failed to queue Pachca notification task for message {instance.id}: {e}",
                extra={
                    "message_id": instance.id,
                    "chat_room_id": chat_room.id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            # Don't re-raise - notification failure shouldn't break message sending

    except Exception as e:
        # Critical: unexpected error during notification setup
        logger.error(
            f"Error in notification signal for message {instance.id}: {str(e)}",
            exc_info=True,
            extra={
                "message_id": instance.id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        # Don't raise - log error but let message creation succeed


@receiver(post_save, sender=StudentProfile)
def sync_parent_participants(
    sender, instance: StudentProfile, created: bool, **kwargs
) -> None:
    """
    When a parent is assigned to a student, add the parent to all chats where the student is a participant.

    This ensures parents can see all their child's chats (FORUM_SUBJECT, FORUM_TUTOR, etc.).
    Uses transaction.atomic() to ensure consistency between M2M and ChatParticipant model.

    Args:
        sender: StudentProfile model class
        instance: The StudentProfile instance being saved
        created: Boolean indicating if instance was just created
        **kwargs: Additional keyword arguments from signal
    """
    if not instance.parent:
        return

    student_user = instance.user
    parent_user = instance.parent

    try:
        with transaction.atomic():
            student_rooms = ChatRoom.objects.filter(
                participants__id=student_user.id
            ).distinct()

            if not student_rooms.exists():
                logger.debug(
                    f"Student {student_user.id} has no chat rooms yet, skipping parent sync"
                )
                return

            participants_to_create = []
            rooms_to_add_parent = []

            for room in student_rooms:
                if not room.participants.filter(id=parent_user.id).exists():
                    room.participants.add(parent_user)
                    rooms_to_add_parent.append(room)
                    participants_to_create.append(
                        ChatParticipant(
                            room=room, user=parent_user, joined_at=timezone.now()
                        )
                    )

            if participants_to_create:
                ChatParticipant.objects.bulk_create(
                    participants_to_create, ignore_conflicts=True, batch_size=100
                )
                logger.info(
                    f"Added parent {parent_user.id} to {len(rooms_to_add_parent)} chat rooms for student {student_user.id}",
                    extra={
                        "parent_id": parent_user.id,
                        "student_id": student_user.id,
                        "rooms_count": len(rooms_to_add_parent),
                        "room_ids": [room.id for room in rooms_to_add_parent],
                    },
                )
            else:
                logger.debug(
                    f"Parent {parent_user.id} already in all {student_rooms.count()} chat rooms for student {student_user.id}"
                )

    except Exception as e:
        logger.error(
            f"Error syncing parent {parent_user.id if instance.parent else 'None'} to student {student_user.id} chats: {str(e)}",
            exc_info=True,
            extra={
                "student_profile_id": instance.id,
                "student_id": student_user.id,
                "parent_id": parent_user.id if instance.parent else None,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )


@receiver(post_save, sender=User)
def add_user_to_general_chat(sender, instance: User, created: bool, **kwargs) -> None:
    """
    Automatically add newly created users to the general chat.

    When a new user is created with an eligible role (STUDENT, TEACHER, TUTOR, PARENT),
    they are automatically added as a participant to the general chat if it exists.

    This signal is idempotent - it uses get_or_create for ChatParticipant.

    Args:
        sender: User model class
        instance: The User instance being saved
        created: Boolean indicating if instance was just created
        **kwargs: Additional keyword arguments from signal
    """
    import os

    # Skip in test mode to prevent fixture conflicts
    if os.getenv("ENVIRONMENT", "production").lower() == "test":
        return

    if not created:
        return

    # Only add users with eligible roles
    eligible_roles = [
        User.Role.STUDENT,
        User.Role.TEACHER,
        User.Role.TUTOR,
        User.Role.PARENT,
    ]
    if instance.role not in eligible_roles:
        return

    try:
        # Find existing general chat (don't create one if it doesn't exist)
        general_chat = ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).first()

        if not general_chat:
            logger.debug(
                f"[Signal] General chat not found, skipping auto-add for user_id={instance.id}"
            )
            return

        # Wrap in transaction to ensure consistency between M2M and ChatParticipant
        with transaction.atomic():
            # Add user to participants (M2M relation)
            if not general_chat.participants.filter(id=instance.id).exists():
                general_chat.participants.add(instance)

            # Create ChatParticipant record with proper metadata
            participant, participant_created = ChatParticipant.objects.get_or_create(
                room=general_chat,
                user=instance,
                defaults={
                    "is_admin": instance.role == User.Role.TEACHER,
                    "joined_at": timezone.now(),
                },
            )

        if participant_created:
            logger.info(
                f"[Signal] User {instance.id} ({instance.email}) auto-added to general chat",
                extra={
                    "user_id": instance.id,
                    "email": instance.email,
                    "role": instance.role,
                    "chat_room_id": general_chat.id,
                },
            )
        else:
            logger.debug(
                f"[Signal] User {instance.id} already in general chat, skipping"
            )

    except Exception as e:
        # Don't break user creation if this fails
        logger.error(
            f"[Signal] Error adding user {instance.id} to general chat: {str(e)}",
            exc_info=True,
            extra={
                "user_id": instance.id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        # Don't raise - allow user creation to succeed
