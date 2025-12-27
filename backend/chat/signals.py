"""
Signal handlers for chat system.

Includes:
- Auto-creation of forum chats when SubjectEnrollment is created
- Pachca notifications for new forum messages
- Auto-add new users to general chat
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

from materials.models import SubjectEnrollment
from accounts.models import StudentProfile
from .models import ChatRoom, Message, ChatParticipant
from .services.pachca_service import PachcaService

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=SubjectEnrollment)
def create_forum_chat_on_enrollment(sender, instance: SubjectEnrollment, created: bool, **kwargs) -> None:
    """
    Automatically create forum chats when a student enrolls in a subject.

    Creates two chats:
    1. Student-Teacher chat (FORUM_SUBJECT type)
    2. Student-Tutor chat if student has a tutor (FORUM_TUTOR type)

    This signal is idempotent - it checks if chats already exist before creating.

    Args:
        sender: SubjectEnrollment model class
        instance: The SubjectEnrollment instance being saved
        created: Boolean indicating if instance was just created
        **kwargs: Additional keyword arguments from signal
    """
    if not created:
        return

    try:
        # Get student profile for tutor info
        student_profile: StudentProfile | None = None
        try:
            student_profile = StudentProfile.objects.select_related('tutor').get(
                user=instance.student
            )
        except StudentProfile.DoesNotExist:
            logger.warning(
                f"StudentProfile not found for user {instance.student.id} during enrollment "
                f"{instance.id} for subject {instance.subject.id}"
            )

        # Create student-teacher forum chat
        subject_name = instance.get_subject_name()
        student_name = instance.student.get_full_name()
        teacher_name = instance.teacher.get_full_name()

        # Format: "{Subject} - {Student} ↔ {Teacher}"
        forum_chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"

        # Check if forum chat already exists (idempotent)
        existing_forum_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=instance
        ).first()

        if not existing_forum_chat:
            forum_chat = ChatRoom.objects.create(
                name=forum_chat_name,
                type=ChatRoom.Type.FORUM_SUBJECT,
                enrollment=instance,
                created_by=instance.student,
                description=f"Forum for {subject_name} between {student_name} and {teacher_name}"
            )
            # Add student and teacher as participants (M2M)
            forum_chat.participants.add(instance.student, instance.teacher)

            # Create ChatParticipant records for unread_count tracking and WebSocket access
            ChatParticipant.objects.get_or_create(
                room=forum_chat,
                user=instance.student
            )
            ChatParticipant.objects.get_or_create(
                room=forum_chat,
                user=instance.teacher
            )

            logger.info(
                f"Created forum_subject chat '{forum_chat.name}' for enrollment {instance.id}"
            )
        else:
            logger.info(
                f"Forum_subject chat already exists for enrollment {instance.id}, skipping creation"
            )

        # Create student-tutor forum chat if student has a tutor
        if student_profile and student_profile.tutor:
            tutor_name = student_profile.tutor.get_full_name()
            tutor_chat_name = f"{subject_name} - {student_name} ↔ {tutor_name}"

            # Check if tutor chat already exists
            existing_tutor_chat = ChatRoom.objects.filter(
                type=ChatRoom.Type.FORUM_TUTOR,
                enrollment=instance
            ).first()

            if not existing_tutor_chat:
                tutor_chat = ChatRoom.objects.create(
                    name=tutor_chat_name,
                    type=ChatRoom.Type.FORUM_TUTOR,
                    enrollment=instance,
                    created_by=instance.student,
                    description=f"Forum for {subject_name} between {student_name} and {tutor_name}"
                )
                # Add student and tutor as participants (M2M)
                tutor_chat.participants.add(instance.student, student_profile.tutor)

                # Create ChatParticipant records for unread_count tracking and WebSocket access
                ChatParticipant.objects.get_or_create(
                    room=tutor_chat,
                    user=instance.student
                )
                ChatParticipant.objects.get_or_create(
                    room=tutor_chat,
                    user=student_profile.tutor
                )

                logger.info(
                    f"Created forum_tutor chat '{tutor_chat.name}' for enrollment {instance.id}"
                )
            else:
                logger.info(
                    f"Forum_tutor chat already exists for enrollment {instance.id}, skipping creation"
                )

    except Exception as e:
        logger.error(
            f"Error creating forum chats for SubjectEnrollment {instance.id}: {str(e)}",
            exc_info=True
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
                extra={'message_id': instance.id}
            )
            return

        # Only send notification for forum chats
        if chat_room.type not in (ChatRoom.Type.FORUM_SUBJECT, ChatRoom.Type.FORUM_TUTOR):
            return

        # Dispatch Celery task for async processing with retry
        from chat.tasks import send_pachca_forum_notification_task

        send_pachca_forum_notification_task.apply_async(
            args=[instance.id, chat_room.id],
            countdown=2,  # Wait 2 seconds before sending (debounce)
        )

        logger.info(
            f"Pachca notification task queued for message {instance.id} in chat {chat_room.id}",
            extra={
                'message_id': instance.id,
                'chat_room_id': chat_room.id,
                'chat_type': chat_room.type
            }
        )

    except Exception as e:
        # Critical: Celery task dispatch failed
        logger.error(
            f"Error dispatching Pachca notification task for message {instance.id}: {str(e)}",
            exc_info=True,
            extra={
                'message_id': instance.id,
                'error_type': type(e).__name__,
                'error': str(e)
            }
        )
        # Don't raise - log error but let message creation succeed


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
    if os.getenv('ENVIRONMENT', 'production').lower() == 'test':
        return

    if not created:
        return

    # Only add users with eligible roles
    eligible_roles = [User.Role.STUDENT, User.Role.TEACHER, User.Role.TUTOR, User.Role.PARENT]
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

        # Add user to participants (M2M relation)
        if not general_chat.participants.filter(id=instance.id).exists():
            general_chat.participants.add(instance)

        # Create ChatParticipant record with proper metadata
        participant, participant_created = ChatParticipant.objects.get_or_create(
            room=general_chat,
            user=instance,
            defaults={
                'is_admin': instance.role == User.Role.TEACHER,
                'joined_at': timezone.now()
            }
        )

        if participant_created:
            logger.info(
                f"[Signal] User {instance.id} ({instance.email}) auto-added to general chat",
                extra={
                    'user_id': instance.id,
                    'email': instance.email,
                    'role': instance.role,
                    'chat_room_id': general_chat.id
                }
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
                'user_id': instance.id,
                'error_type': type(e).__name__,
                'error': str(e)
            }
        )
        # Don't raise - allow user creation to succeed
