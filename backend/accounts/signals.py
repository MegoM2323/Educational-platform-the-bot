"""
Django signals для аудит-логирования операций в приложении accounts.

Логирует все операции с пользователями и профилями для целей аудита и безопасности:
- Создание пользователей (создание профилей, генерация паролей)
- Обновление данных пользователей (изменение email, имени, активности)
- Сброс паролей (кто и когда выполнил)
- Удаление пользователей (soft/hard delete с информацией об оператор)
"""
import logging
from typing import Any, Dict, Optional
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()

# Логгер для аудита
audit_logger = logging.getLogger('audit')
logger = logging.getLogger(__name__)


class AuditLogMessage:
    """Helper класс для формирования структурированных audit log сообщений."""

    @staticmethod
    def create_user(
        user_id: int,
        email: str,
        role: str,
        admin_id: Optional[int] = None,
        admin_email: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Формирует сообщение логирования при создании пользователя.

        Args:
            user_id: ID созданного пользователя
            email: Email пользователя
            role: Роль пользователя
            admin_id: ID администратора, выполнившего операцию
            admin_email: Email администратора
            extra_data: Дополнительные данные (пароль сгенерирован автоматически и т.д.)

        Returns:
            Отформатированное сообщение для логирования
        """
        extra_str = ""
        if extra_data:
            extra_items = [f"{k}={v}" for k, v in extra_data.items()]
            extra_str = f" {' '.join(extra_items)}"

        admin_info = ""
        if admin_id or admin_email:
            admin_info = f" by admin_id={admin_id} admin_email={admin_email}"

        return (
            f"action=create_user user_id={user_id} email={email} role={role}{admin_info}{extra_str}"
        )

    @staticmethod
    def update_user(
        user_id: int,
        email: str,
        role: str,
        changed_fields: Dict[str, tuple],
        admin_id: Optional[int] = None,
        admin_email: Optional[str] = None
    ) -> str:
        """
        Формирует сообщение логирования при обновлении пользователя.

        Args:
            user_id: ID пользователя
            email: Email пользователя
            role: Роль пользователя
            changed_fields: Словарь {field_name: (old_value, new_value)}
            admin_id: ID администратора
            admin_email: Email администратора

        Returns:
            Отформатированное сообщение для логирования
        """
        changes = " ".join([
            f"{field}='{old}'->>'{new}'"
            for field, (old, new) in changed_fields.items()
        ])

        admin_info = ""
        if admin_id or admin_email:
            admin_info = f" by admin_id={admin_id} admin_email={admin_email}"

        return (
            f"action=update_user user_id={user_id} email={email} role={role} "
            f"changes=[{changes}]{admin_info}"
        )

    @staticmethod
    def reset_password(
        user_id: int,
        email: str,
        admin_id: Optional[int] = None,
        admin_email: Optional[str] = None
    ) -> str:
        """
        Формирует сообщение логирования при сбросе пароля.

        Args:
            user_id: ID пользователя
            email: Email пользователя
            admin_id: ID администратора
            admin_email: Email администратора

        Returns:
            Отформатированное сообщение для логирования
        """
        admin_info = ""
        if admin_id or admin_email:
            admin_info = f" by admin_id={admin_id} admin_email={admin_email}"

        return f"action=reset_password user_id={user_id} email={email}{admin_info}"

    @staticmethod
    def delete_user(
        user_id: int,
        email: str,
        role: str,
        soft_delete: bool = True,
        admin_id: Optional[int] = None,
        admin_email: Optional[str] = None
    ) -> str:
        """
        Формирует сообщение логирования при удалении пользователя.

        Args:
            user_id: ID пользователя
            email: Email пользователя
            role: Роль пользователя
            soft_delete: True если soft delete (деактивация), False если hard delete
            admin_id: ID администратора
            admin_email: Email администратора

        Returns:
            Отформатированное сообщение для логирования
        """
        delete_type = "soft" if soft_delete else "hard"
        admin_info = ""
        if admin_id or admin_email:
            admin_info = f" by admin_id={admin_id} admin_email={admin_email}"

        return (
            f"action=delete_user type={delete_type} user_id={user_id} "
            f"email={email} role={role}{admin_info}"
        )

    @staticmethod
    def create_profile(
        profile_type: str,
        user_id: int,
        email: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Формирует сообщение логирования при создании профиля.

        Args:
            profile_type: Тип профиля (StudentProfile, TeacherProfile, etc.)
            user_id: ID пользователя
            email: Email пользователя
            extra_data: Дополнительные данные

        Returns:
            Отформатированное сообщение для логирования
        """
        extra_str = ""
        if extra_data:
            extra_items = [f"{k}={v}" for k, v in extra_data.items()]
            extra_str = f" {' '.join(extra_items)}"

        return f"action=create_profile type={profile_type} user_id={user_id} email={email}{extra_str}"


@receiver(post_save, sender=User)
def auto_create_user_profile(sender, instance: User, created: bool, **kwargs) -> None:
    """
    Signal обработчик для автоматического создания профилей при создании пользователя.

    Создает профиль в зависимости от роли пользователя:
    - StudentProfile для студентов
    - TeacherProfile для преподавателей
    - TutorProfile для тьюторов
    - ParentProfile для родителей

    Args:
        sender: Модель User
        instance: Инстанс пользователя
        created: True если пользователь был создан, False если обновлен
        **kwargs: Дополнительные аргументы от Django
    """
    import os

    # Skip auto-create in test mode to prevent fixture conflicts
    # Tests manage profile creation explicitly to avoid UNIQUE constraint errors
    if os.getenv('ENVIRONMENT', 'production').lower() == 'test':
        return

    if not created:
        return

    try:
        if instance.role == User.Role.STUDENT:
            profile, created = StudentProfile.objects.get_or_create(user=instance)
            if created:
                logger.info(f"[Signal] StudentProfile auto-created for user_id={instance.id} email={instance.email}")
            else:
                logger.debug(f"[Signal] StudentProfile already exists for user_id={instance.id}")
        elif instance.role == User.Role.TEACHER:
            profile, created = TeacherProfile.objects.get_or_create(user=instance)
            if created:
                logger.info(f"[Signal] TeacherProfile auto-created for user_id={instance.id} email={instance.email}")
            else:
                logger.debug(f"[Signal] TeacherProfile already exists for user_id={instance.id}")
        elif instance.role == User.Role.TUTOR:
            profile, created = TutorProfile.objects.get_or_create(user=instance)
            if created:
                logger.info(f"[Signal] TutorProfile auto-created for user_id={instance.id} email={instance.email}")
            else:
                logger.debug(f"[Signal] TutorProfile already exists for user_id={instance.id}")
        elif instance.role == User.Role.PARENT:
            profile, created = ParentProfile.objects.get_or_create(user=instance)
            if created:
                logger.info(f"[Signal] ParentProfile auto-created for user_id={instance.id} email={instance.email}")
            else:
                logger.debug(f"[Signal] ParentProfile already exists for user_id={instance.id}")
    except Exception as exc:
        logger.error(f"[Signal] Error auto-creating profile for user_id={instance.id} email={instance.email}: {exc}", exc_info=True)


@receiver(post_save, sender=User)
def auto_create_notification_settings(sender, instance: User, created: bool, **kwargs) -> None:
    """
    Signal обработчик для автоматического создания настроек уведомлений при создании пользователя.

    Создает NotificationSettings с default preferences для каждого нового пользователя.

    Args:
        sender: Модель User
        instance: Инстанс пользователя
        created: True если пользователь был создан, False если обновлен
        **kwargs: Дополнительные аргументы от Django
    """
    import os

    # Skip auto-create in test mode to prevent fixture conflicts
    if os.getenv('ENVIRONMENT', 'production').lower() == 'test':
        return

    if not created:
        return

    try:
        from notifications.models import NotificationSettings

        notification_settings, created = NotificationSettings.objects.get_or_create(user=instance)
        if created:
            logger.info(f"[Signal] NotificationSettings auto-created for user_id={instance.id} email={instance.email}")
        else:
            logger.debug(f"[Signal] NotificationSettings already exists for user_id={instance.id}")
    except Exception as exc:
        logger.error(f"[Signal] Error auto-creating NotificationSettings for user_id={instance.id}: {exc}", exc_info=True)


@receiver(post_save, sender=User)
def log_user_creation_or_update(sender, instance: User, created: bool, **kwargs) -> None:
    """
    Signal обработчик для логирования создания и обновления пользователей.

    Логирует:
    - Создание нового пользователя (создание профилей, базовые данные)
    - Обновление данных пользователя (какие поля изменились)

    Args:
        sender: Модель User
        instance: Инстанс пользователя
        created: True если пользователь был создан, False если обновлен
        **kwargs: Дополнительные аргументы от Django
    """
    try:
        if created:
            # Логирование создания пользователя
            extra_data = {
                'first_name': instance.first_name or 'N/A',
                'last_name': instance.last_name or 'N/A',
                'is_active': instance.is_active,
                'is_staff': instance.is_staff,
            }

            audit_message = AuditLogMessage.create_user(
                user_id=instance.id,
                email=instance.email,
                role=instance.role,
                extra_data=extra_data
            )
            audit_logger.info(audit_message)
            logger.debug(f"[Signal] User created: {instance.email} (role={instance.role})")

        else:
            # Логирование обновления пользователя
            # Получаем "до" данные из БД
            try:
                old_instance = User.objects.get(pk=instance.pk)
                changed_fields = {}

                # Проверяем основные поля
                for field in ['email', 'first_name', 'last_name', 'is_active', 'is_staff', 'role']:
                    old_value = getattr(old_instance, field)
                    new_value = getattr(instance, field)
                    if old_value != new_value:
                        changed_fields[field] = (old_value, new_value)

                # Логируем только если есть изменения
                if changed_fields:
                    audit_message = AuditLogMessage.update_user(
                        user_id=instance.id,
                        email=instance.email,
                        role=instance.role,
                        changed_fields=changed_fields
                    )
                    audit_logger.info(audit_message)
                    logger.debug(f"[Signal] User updated: {instance.email}, changes={list(changed_fields.keys())}")

            except User.DoesNotExist:
                # Если не найдена "до" версия, просто логируем что было обновление
                logger.warning(f"[Signal] Could not find old instance for user {instance.id}")

    except Exception as exc:
        logger.error(f"[Signal] Error logging user change for {instance.email}: {exc}")


@receiver(post_save, sender=StudentProfile)
def log_student_profile_creation(sender, instance: StudentProfile, created: bool, **kwargs) -> None:
    """
    Signal обработчик для логирования создания профилей студентов.

    Args:
        sender: Модель StudentProfile
        instance: Инстанс профиля студента
        created: True если был создан
        **kwargs: Дополнительные аргументы от Django
    """
    try:
        if created:
            extra_data = {
                'grade': instance.grade or 'N/A',
                'goal': instance.goal or 'N/A',
                'tutor_id': instance.tutor_id,
                'parent_id': instance.parent_id,
            }

            audit_message = AuditLogMessage.create_profile(
                profile_type='StudentProfile',
                user_id=instance.user.id,
                email=instance.user.email,
                extra_data=extra_data
            )
            audit_logger.info(audit_message)
            logger.debug(f"[Signal] StudentProfile created for user {instance.user.id}")

    except Exception as exc:
        logger.error(f"[Signal] Error logging StudentProfile creation: {exc}")


@receiver(post_save, sender=StudentProfile)
def create_tutor_chats_on_tutor_assignment(sender, instance: StudentProfile, created: bool, update_fields, **kwargs) -> None:
    """
    Create FORUM_TUTOR chats for all existing enrollments when tutor is assigned to student.

    This signal handles the case when a tutor is assigned AFTER enrollments already exist.
    It creates FORUM_TUTOR chats for each active enrollment of the student.

    The signal is idempotent - it checks for existing chats before creating new ones.

    Args:
        sender: StudentProfile model class
        instance: The StudentProfile instance being saved
        created: Boolean indicating if instance was just created
        update_fields: Set of field names that were updated (None if all fields)
        **kwargs: Additional keyword arguments from signal
    """
    # Only proceed if tutor was assigned (either on creation or update)
    if not instance.tutor:
        return

    # Check if tutor field was actually changed
    # On creation, always proceed if tutor is set
    # On update, only proceed if 'tutor' is in update_fields or update_fields is None (all fields updated)
    if not created:
        if update_fields is not None and 'tutor' not in update_fields:
            return

    try:
        # Import here to avoid circular imports
        from materials.models import SubjectEnrollment
        from chat.models import ChatRoom
    except ModuleNotFoundError:
        # Materials or chat modules not available (e.g., in tests)
        logger.debug(f"[Signal] Materials or chat modules not available for student {instance.user.id}")
        return

    try:
        # Get all active enrollments for this student
        enrollments = SubjectEnrollment.objects.filter(
            student=instance.user,
            is_active=True
        ).select_related('subject', 'teacher')

        if not enrollments.exists():
            logger.info(
                f"[Signal] No active enrollments found for student {instance.user.id} when assigning tutor {instance.tutor.id}"
            )
            return

        created_count = 0
        skipped_count = 0

        for enrollment in enrollments:
            # Check if FORUM_TUTOR chat already exists for this enrollment
            existing_chat = ChatRoom.objects.filter(
                type=ChatRoom.Type.FORUM_TUTOR,
                enrollment=enrollment
            ).first()

            if existing_chat:
                # BUG FIX: When tutor is changed, add new tutor to existing chat
                # Check if new tutor is already a participant
                if not existing_chat.participants.filter(id=instance.tutor.id).exists():
                    # Add new tutor as participant (M2M)
                    existing_chat.participants.add(instance.tutor)

                    # Import ChatParticipant for unread tracking
                    from chat.models import ChatParticipant
                    ChatParticipant.objects.get_or_create(
                        room=existing_chat,
                        user=instance.tutor
                    )

                    # Update chat name to reflect new tutor
                    subject_name = enrollment.get_subject_name()
                    student_name = instance.user.get_full_name()
                    tutor_name = instance.tutor.get_full_name()
                    existing_chat.name = f"{subject_name} - {student_name} <-> {tutor_name}"
                    existing_chat.save(update_fields=['name'])

                    logger.info(
                        f"[Signal] Added new tutor {instance.tutor.id} to existing FORUM_TUTOR chat {existing_chat.id} "
                        f"for enrollment {enrollment.id}"
                    )
                else:
                    skipped_count += 1
                    logger.debug(
                        f"[Signal] Tutor {instance.tutor.id} already in FORUM_TUTOR chat for enrollment {enrollment.id}, skipping"
                    )
                continue

            # Create FORUM_TUTOR chat
            subject_name = enrollment.get_subject_name()
            student_name = instance.user.get_full_name()
            tutor_name = instance.tutor.get_full_name()

            tutor_chat_name = f"{subject_name} - {student_name} ↔ {tutor_name}"

            tutor_chat = ChatRoom.objects.create(
                name=tutor_chat_name,
                type=ChatRoom.Type.FORUM_TUTOR,
                enrollment=enrollment,
                created_by=instance.user,
                description=f"Forum for {subject_name} between {student_name} and {tutor_name}"
            )

            # Add student and tutor as participants
            tutor_chat.participants.add(instance.user, instance.tutor)

            created_count += 1
            logger.info(
                f"[Signal] Created FORUM_TUTOR chat '{tutor_chat.name}' for enrollment {enrollment.id}"
            )

        logger.info(
            f"[Signal] Tutor assignment for student {instance.user.id}: "
            f"created {created_count} FORUM_TUTOR chats, skipped {skipped_count} existing"
        )

    except Exception as e:
        logger.error(
            f"[Signal] Error creating FORUM_TUTOR chats for student {instance.user.id}: {str(e)}",
            exc_info=True
        )
        # Don't raise - allow StudentProfile save to succeed


@receiver(post_save, sender=TeacherProfile)
def log_teacher_profile_creation(sender, instance: TeacherProfile, created: bool, **kwargs) -> None:
    """
    Signal обработчик для логирования создания профилей преподавателей.

    Args:
        sender: Модель TeacherProfile
        instance: Инстанс профиля преподавателя
        created: True если был создан
        **kwargs: Дополнительные аргументы от Django
    """
    try:
        if created:
            extra_data = {
                'subject': instance.subject or 'N/A',
                'experience_years': instance.experience_years or 0,
                'bio': instance.bio[:50] if instance.bio else 'N/A',  # Первые 50 символов
            }

            audit_message = AuditLogMessage.create_profile(
                profile_type='TeacherProfile',
                user_id=instance.user.id,
                email=instance.user.email,
                extra_data=extra_data
            )
            audit_logger.info(audit_message)
            logger.debug(f"[Signal] TeacherProfile created for user {instance.user.id}")

    except Exception as exc:
        logger.error(f"[Signal] Error logging TeacherProfile creation: {exc}")


@receiver(post_save, sender=TutorProfile)
def log_tutor_profile_creation(sender, instance: TutorProfile, created: bool, **kwargs) -> None:
    """
    Signal обработчик для логирования создания профилей тьюторов.

    Args:
        sender: Модель TutorProfile
        instance: Инстанс профиля тьютора
        created: True если был создан
        **kwargs: Дополнительные аргументы от Django
    """
    try:
        if created:
            extra_data = {
                'specialization': instance.specialization or 'N/A',
                'experience_years': instance.experience_years or 0,
                'bio': instance.bio[:50] if instance.bio else 'N/A',
            }

            audit_message = AuditLogMessage.create_profile(
                profile_type='TutorProfile',
                user_id=instance.user.id,
                email=instance.user.email,
                extra_data=extra_data
            )
            audit_logger.info(audit_message)
            logger.debug(f"[Signal] TutorProfile created for user {instance.user.id}")

    except Exception as exc:
        logger.error(f"[Signal] Error logging TutorProfile creation: {exc}")


@receiver(post_save, sender=ParentProfile)
def log_parent_profile_creation(sender, instance: ParentProfile, created: bool, **kwargs) -> None:
    """
    Signal обработчик для логирования создания профилей родителей.

    Args:
        sender: Модель ParentProfile
        instance: Инстанс профиля родителя
        created: True если был создан
        **kwargs: Дополнительные аргументы от Django
    """
    try:
        if created:
            audit_message = AuditLogMessage.create_profile(
                profile_type='ParentProfile',
                user_id=instance.user.id,
                email=instance.user.email
            )
            audit_logger.info(audit_message)
            logger.debug(f"[Signal] ParentProfile created for user {instance.user.id}")

    except Exception as exc:
        logger.error(f"[Signal] Error logging ParentProfile creation: {exc}")


@receiver(pre_delete, sender=User)
def log_user_deletion(sender, instance: User, **kwargs) -> None:
    """
    Signal обработчик для логирования удаления пользователей.

    Логирует информацию о пользователе перед его удалением.

    Args:
        sender: Модель User
        instance: Инстанс пользователя
        **kwargs: Дополнительные аргументы от Django
    """
    try:
        # Определяем тип удаления: если is_active=False, то это был soft delete
        # hard delete происходит только если явно вызвана операция delete()
        soft_delete = not instance.is_active

        audit_message = AuditLogMessage.delete_user(
            user_id=instance.id,
            email=instance.email,
            role=instance.role,
            soft_delete=soft_delete
        )
        audit_logger.info(audit_message)
        logger.debug(f"[Signal] User deleted: {instance.email} (type={'soft' if soft_delete else 'hard'})")

    except Exception as exc:
        logger.error(f"[Signal] Error logging user deletion: {exc}")
