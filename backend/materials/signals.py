from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging
import os
from .models import (
    Material,
    MaterialProgress,
    SubjectEnrollment,
    SubjectPayment,
    MaterialSubmission,
    StudyPlanFile,
    StudyPlan,
    SubjectSubscription,
)
from notifications.notification_service import NotificationService
from .cache_utils import DashboardCacheManager
from accounts.models import StudentProfile

User = get_user_model()
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения old_tutor_id перед сохранением
_student_profile_pre_save_state = {}
audit_logger = logging.getLogger("audit")


# ============================================================================
# FILE DELETION SIGNALS
# ============================================================================


@receiver(pre_delete, sender=Material)
def delete_material_file(sender, instance, **kwargs):
    """
    Удаляет физический файл при удалении Material объекта.

    Используется pre_delete signal, чтобы получить доступ к файлу до удаления записи из БД.
    """
    if instance.file:
        try:
            # Проверяем, существует ли файл
            if os.path.isfile(instance.file.path):
                os.remove(instance.file.path)
                logger.info(
                    f"Deleted file: {instance.file.path} for Material {instance.id}"
                )
            else:
                logger.warning(
                    f"File not found: {instance.file.path} for Material {instance.id}"
                )
        except FileNotFoundError:
            # Файл уже удален - это нормально, логируем как info
            logger.info(
                f"File already deleted: {instance.file.name} for Material {instance.id}"
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс удаления
            logger.error(
                f"Error deleting file for Material {instance.id}: {e}", exc_info=True
            )


@receiver(pre_delete, sender=StudyPlanFile)
def delete_study_plan_file(sender, instance, **kwargs):
    """
    Удаляет физический файл при удалении StudyPlanFile объекта.

    Используется pre_delete signal, чтобы получить доступ к файлу до удаления записи из БД.
    """
    if instance.file:
        try:
            # Проверяем, существует ли файл
            if os.path.isfile(instance.file.path):
                os.remove(instance.file.path)
                logger.info(
                    f"Deleted file: {instance.file.path} for StudyPlanFile {instance.id}"
                )
            else:
                logger.warning(
                    f"File not found: {instance.file.path} for StudyPlanFile {instance.id}"
                )
        except FileNotFoundError:
            # Файл уже удален - это нормально, логируем как info
            logger.info(
                f"File already deleted: {instance.file.name} for StudyPlanFile {instance.id}"
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс удаления
            logger.error(
                f"Error deleting file for StudyPlanFile {instance.id}: {e}",
                exc_info=True,
            )


@receiver(pre_delete, sender=MaterialSubmission)
def delete_material_submission_file(sender, instance, **kwargs):
    """
    Удаляет физический файл при удалении MaterialSubmission объекта.

    Используется pre_delete signal, чтобы получить доступ к файлу до удаления записи из БД.
    """
    if instance.submission_file:
        try:
            # Проверяем, существует ли файл
            if os.path.isfile(instance.submission_file.path):
                os.remove(instance.submission_file.path)
                logger.info(
                    f"Deleted submission file: {instance.submission_file.path} for MaterialSubmission {instance.id}"
                )
            else:
                logger.warning(
                    f"Submission file not found: {instance.submission_file.path} for MaterialSubmission {instance.id}"
                )
        except FileNotFoundError:
            # Файл уже удален - это нормально, логируем как info
            logger.info(
                f"Submission file already deleted: {instance.submission_file.name} for MaterialSubmission {instance.id}"
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс удаления
            logger.error(
                f"Error deleting submission file for MaterialSubmission {instance.id}: {e}",
                exc_info=True,
            )


# ============================================================================
# CACHE INVALIDATION SIGNALS
# ============================================================================


@receiver(pre_save, sender=StudentProfile)
def capture_student_profile_pre_save(sender, instance, **kwargs):
    """
    Захватываем old_tutor_id перед сохранением для отслеживания изменений.
    """
    try:
        if instance.pk:
            old_instance = StudentProfile.objects.get(pk=instance.pk)
            _student_profile_pre_save_state[instance.pk] = {
                "old_tutor_id": old_instance.tutor_id
            }
    except StudentProfile.DoesNotExist:
        pass


@receiver(post_save, sender=StudentProfile)
def invalidate_student_profile_cache(sender, instance, created, **kwargs):
    """
    Инвалидирует кэш при создании/изменении StudentProfile.

    Особенно важно для изменений поля tutor - инвалидируем только если tutor_id изменился.
    """
    try:
        cache_manager = DashboardCacheManager()

        # Инвалидируем кэш студента
        if instance.user:
            cache_manager.invalidate_student_cache(instance.user.id)
            cache_manager.invalidate_student_enrollments(instance.user.id)
            cache_manager.invalidate_student_teachers(instance.user.id)

        # Инвалидируем кэш тьютора только если tutor_id изменился
        if created:
            # При создании всегда инвалидируем
            if instance.tutor:
                cache_manager.invalidate_tutor_dashboard(instance.tutor.id)
                logger.info(
                    f"[Signal] Invalidated tutor cache on StudentProfile creation: "
                    f"tutor_id={instance.tutor.id}, student_id={instance.user.id}"
                )
        else:
            # При обновлении только если tutor_id изменился
            old_state = _student_profile_pre_save_state.get(instance.pk)
            if old_state:
                old_tutor_id = old_state.get("old_tutor_id")
                del _student_profile_pre_save_state[instance.pk]  # Очищаем

                # Инвалидируем старый кэш тьютора если он был и изменился
                if old_tutor_id and old_tutor_id != instance.tutor_id:
                    cache_manager.invalidate_tutor_dashboard(old_tutor_id)
                    logger.info(
                        f"[Signal] Invalidated old tutor cache: tutor_id={old_tutor_id}"
                    )

                # Инвалидируем новый кэш тьютора если он есть и изменился
                if instance.tutor_id and instance.tutor_id != old_tutor_id:
                    cache_manager.invalidate_tutor_dashboard(instance.tutor_id)
                    logger.info(
                        f"[Signal] Invalidated new tutor cache: tutor_id={instance.tutor_id}"
                    )

        # Инвалидируем кэш родителя при создании/изменении
        if instance.parent:
            cache_manager.invalidate_parent_cache(instance.parent.id)
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=Material)
@receiver(post_delete, sender=Material)
def invalidate_material_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении материалов"""
    try:
        cache_manager = DashboardCacheManager()

        # Инвалидируем кэш для всех студентов, которым назначен материал
        for student in instance.assigned_to.all():
            cache_manager.invalidate_student_cache(student.id)

        # Инвалидируем кэш преподавателя
        cache_manager.invalidate_teacher_cache(instance.author.id)
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=MaterialProgress)
@receiver(post_delete, sender=MaterialProgress)
def invalidate_progress_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении прогресса"""
    try:
        cache_manager = DashboardCacheManager()

        # Инвалидируем кэш студента
        cache_manager.invalidate_student_cache(instance.student.id)

        # Инвалидируем кэш преподавателя материала
        cache_manager.invalidate_teacher_cache(instance.material.author.id)

        # Инвалидируем кэш родителя студента
        try:
            parent = (
                getattr(instance.student.student_profile, "parent", None)
                if hasattr(instance.student, "student_profile")
                else None
            )
            if parent:
                cache_manager.invalidate_parent_cache(parent.id)
        except:
            pass
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=SubjectEnrollment)
@receiver(post_delete, sender=SubjectEnrollment)
def invalidate_enrollment_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении зачислений"""
    try:
        cache_manager = DashboardCacheManager()

        # Инвалидируем кэш студента
        cache_manager.invalidate_student_cache(instance.student.id)
        cache_manager.invalidate_student_enrollments(instance.student.id)
        cache_manager.invalidate_student_teachers(instance.student.id)

        # Инвалидируем кэш преподавателя
        cache_manager.invalidate_teacher_cache(instance.teacher.id)

        # Инвалидируем кэш тьютора студента
        try:
            student_profile = getattr(instance.student, "student_profile", None)
            if student_profile and student_profile.tutor:
                cache_manager.invalidate_tutor_dashboard(student_profile.tutor.id)
                logger.info(
                    f"[Signal] Invalidated tutor cache: "
                    f"tutor_id={student_profile.tutor.id}, "
                    f"student_id={instance.student.id}, "
                    f"action={'created' if kwargs.get('created') else 'deleted'}"
                )
        except Exception as e:
            logger.debug(f"Could not invalidate tutor cache in enrollment signal: {e}")

        # Инвалидируем кэш родителя
        try:
            parent = (
                getattr(instance.student.student_profile, "parent", None)
                if hasattr(instance.student, "student_profile")
                else None
            )
            if parent:
                cache_manager.invalidate_parent_cache(parent.id)
        except:
            pass
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=SubjectPayment)
@receiver(post_delete, sender=SubjectPayment)
def invalidate_payment_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении платежей"""
    try:
        cache_manager = DashboardCacheManager()

        # Инвалидируем кэш родителя
        try:
            parent = (
                getattr(instance.enrollment.student.student_profile, "parent", None)
                if hasattr(instance.enrollment.student, "student_profile")
                else None
            )
            if parent:
                cache_manager.invalidate_parent_cache(parent.id)
        except:
            pass
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=MaterialSubmission)
def notify_teacher_on_submission(sender, instance, created, **kwargs):
    """Уведомление преподавателя о новом домашнем задании"""
    if not created:
        return
    try:
        teacher = instance.material.author
        student = instance.student
        NotificationService().notify_homework_submitted(
            teacher=teacher,
            submission_id=instance.id,
            student=student,
        )
    except Exception:
        pass


@receiver(post_save, sender=StudyPlan)
@receiver(post_delete, sender=StudyPlan)
def invalidate_study_plan_cache(sender, instance, **kwargs):
    """
    Инвалидирует кэш при изменении планов занятий.

    Когда преподаватель отправляет план студенту (status меняется на 'sent'),
    родитель должен увидеть это в своем дашборде.
    """
    try:
        cache_manager = DashboardCacheManager()

        # Инвалидируем кэш студента
        cache_manager.invalidate_student_cache(instance.student.id)

        # Инвалидируем кэш преподавателя
        cache_manager.invalidate_teacher_cache(instance.teacher.id)

        # Инвалидируем кэш родителя (для отображения планов в дашборде)
        try:
            student = instance.student
            if hasattr(student, "student_profile"):
                parent = getattr(student.student_profile, "parent", None)
                if parent:
                    cache_manager.invalidate_parent_cache(parent.id)
                    logger.debug(
                        f"Parent cache invalidated via StudyPlan signal: "
                        f"plan_id={instance.id}, parent_id={parent.id}, "
                        f"student_id={student.id}, status={instance.status}"
                    )
        except Exception as e:
            logger.debug(f"Could not invalidate parent cache in StudyPlan signal: {e}")
    except Exception:
        pass  # Игнорируем ошибки Redis


@receiver(post_save, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    """Инвалидирует кэш при изменении пользователя"""
    try:
        cache_manager = DashboardCacheManager()

        if instance.role == User.Role.STUDENT:
            cache_manager.invalidate_student_cache(instance.id)

            # Инвалидируем кэш родителя
            try:
                parent = (
                    getattr(instance.student_profile, "parent", None)
                    if hasattr(instance, "student_profile")
                    else None
                )
                if parent:
                    cache_manager.invalidate_parent_cache(parent.id)
            except:
                pass

        elif instance.role == User.Role.TEACHER:
            cache_manager.invalidate_teacher_cache(instance.id)

        elif instance.role == User.Role.PARENT:
            cache_manager.invalidate_parent_cache(instance.id)
    except Exception:
        pass  # Игнорируем ошибки Redis


# ============================================================================
# FORUM CHAT AUTO-CREATION SIGNALS
# ============================================================================


@receiver(post_save, sender=SubjectEnrollment)
def create_subject_forum_chat(
    sender, instance: SubjectEnrollment, created: bool, update_fields, **kwargs
) -> None:
    """
    Auto-create FORUM_SUBJECT chat when student is enrolled in subject with teacher.

    This signal creates a private forum chat between student and teacher for a specific subject.
    The chat is created only when:
    - SubjectEnrollment is newly created (not updated)
    - Enrollment is active (is_active=True)

    The signal is idempotent - checks for existing chats before creating.

    Chat naming convention: "{subject_name} - {student_name} ↔ {teacher_name}"
    Participants: student + teacher
    Created by: student (follows forum convention)

    Args:
        sender: SubjectEnrollment model class
        instance: The SubjectEnrollment instance being saved
        created: Boolean indicating if instance was just created
        update_fields: Set of field names that were updated (None if all fields)
        **kwargs: Additional keyword arguments from signal
    """
    # Only proceed on creation of new enrollment
    if not created:
        return

    # Only create chat for active enrollments
    if not instance.is_active:
        logger.debug(
            f"[Signal] Skipping FORUM_SUBJECT chat creation for inactive enrollment {instance.id}"
        )
        return

    try:
        # Import here to avoid circular imports
        from chat.models import ChatRoom, ChatParticipant
        from accounts.models import StudentProfile

        # Check if FORUM_SUBJECT chat already exists for this enrollment
        # Use get_or_create for idempotency
        existing_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=instance
        ).first()

        if existing_chat:
            logger.debug(
                f"[Signal] FORUM_SUBJECT chat already exists for enrollment {instance.id}, skipping"
            )
            return

        # Build chat name: "{subject_name} - {student_name} ↔ {teacher_name}"
        student_name = instance.student.get_full_name()
        subject_name = (
            instance.get_subject_name()
        )  # Respects custom_subject_name if set
        teacher_name = instance.teacher.get_full_name()

        chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"

        # Create FORUM_SUBJECT chat
        forum_chat = ChatRoom.objects.create(
            name=chat_name,
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=instance,
            created_by=instance.student,
            description=f"Forum for {subject_name} between {student_name} and teacher {teacher_name}",
        )

        # Collect all participants: student + teacher + parent (if exists)
        participants_to_add = [instance.student, instance.teacher]

        # Add parent if exists
        try:
            student_profile = StudentProfile.objects.select_related("parent").get(
                user=instance.student
            )
            if student_profile.parent:
                participants_to_add.append(student_profile.parent)
        except StudentProfile.DoesNotExist:
            pass

        # Add participants to M2M relation
        forum_chat.participants.add(*participants_to_add)

        # Create ChatParticipant records for tracking
        participant_records = [
            ChatParticipant(room=forum_chat, user=user) for user in participants_to_add
        ]
        ChatParticipant.objects.bulk_create(participant_records, ignore_conflicts=True)

        logger.info(
            f"[Signal] Created FORUM_SUBJECT chat '{forum_chat.name}' (id={forum_chat.id}) for enrollment {instance.id} "
            f"with {len(participants_to_add)} participants"
        )

        # Verify parent was added (if exists)
        try:
            student_profile = StudentProfile.objects.get(user=instance.student)
            if student_profile.parent:
                if not forum_chat.participants.filter(
                    id=student_profile.parent.id
                ).exists():
                    logger.warning(
                        f"Parent {student_profile.parent.username} ({student_profile.parent.id}) failed to be added to "
                        f"forum {forum_chat.name} ({forum_chat.id})"
                    )
                else:
                    logger.debug(
                        f"Added parent {student_profile.parent.username} ({student_profile.parent.id}) to forum "
                        f"{forum_chat.name} ({forum_chat.id})"
                    )
        except (StudentProfile.DoesNotExist, Exception) as e:
            pass  # Parent verification is optional

        # Audit log
        audit_logger.info(
            f"action=create_forum_subject_chat chat_id={forum_chat.id} enrollment_id={instance.id} "
            f"student_id={instance.student.id} teacher_id={instance.teacher.id} subject_id={instance.subject.id}"
        )

    except Exception as e:
        logger.error(
            f"[Signal] Error creating FORUM_SUBJECT chat for enrollment {instance.id}: {str(e)}",
            exc_info=True,
        )
        # Don't raise - allow SubjectEnrollment save to succeed


# ============================================================================
# SUBSCRIPTION SIGNALS - Инвалидация кеша при изменении подписок
# ============================================================================


@receiver(post_save, sender=SubjectSubscription)
@receiver(post_delete, sender=SubjectSubscription)
def invalidate_subscription_cache(sender, instance, **kwargs):
    """
    Инвалидирует кеш родителя при изменении/удалении подписки.

    Это КРИТИЧНОЕ для:
    1. Обновления статуса платежа после создания подписки
    2. Отображения кнопки "Активен" вместо "Подключить"
    3. Показания даты next_payment_date для рекуррентных платежей
    """
    try:
        cache_manager = DashboardCacheManager()

        # Получаем родителя через enrollment -> student -> student_profile -> parent
        try:
            student = instance.enrollment.student
            parent = (
                getattr(student.student_profile, "parent", None)
                if hasattr(student, "student_profile")
                else None
            )

            if parent:
                # Инвалидируем кеш родителя и его детей
                cache_manager.invalidate_parent_cache(parent.id)
                logger.info(
                    f"[Signal] Invalidated parent cache for parent={parent.id} due to subscription change (sub_id={instance.id})"
                )
            else:
                logger.warning(
                    f"[Signal] Parent not found for subscription {instance.id}"
                )
        except Exception as e:
            logger.warning(
                f"[Signal] Error getting parent for subscription {instance.id}: {e}"
            )
            pass

    except Exception as e:
        logger.error(
            f"[Signal] Error in invalidate_subscription_cache: {e}", exc_info=True
        )
        pass  # Игнорируем ошибки Redis
