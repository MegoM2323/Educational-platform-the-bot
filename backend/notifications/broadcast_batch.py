"""
Broadcast Batch Operations Service

Оптимизированный сервис для массовой рассылки уведомлений с поддержкой:
- Пакетной обработки получателей
- Отслеживания прогресса
- Обработки ошибок
- Возможности отмены и повтора
"""
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Model, QuerySet
from celery import shared_task

logger = logging.getLogger(__name__)


class BroadcastBatchProcessor:
    """
    Процессор для пакетной обработки рассылок
    """

    # Размер пакета для bulk_create
    BATCH_SIZE = 1000

    # Размер пакета для обработки отправок
    SEND_BATCH_SIZE = 100

    # Максимальное количество попыток переотправки
    MAX_RETRIES = 3

    # Задержка между попытками (в секундах)
    RETRY_DELAYS = [10, 60, 300]  # 10s, 1m, 5m

    @classmethod
    def create_broadcast_recipients_batch(
        cls,
        broadcast_id: int,
        recipient_ids: List[int],
        batch_size: int = None
    ) -> Dict:
        """
        Создать BroadcastRecipient записи в батчах для оптимизации

        Args:
            broadcast_id: ID рассылки
            recipient_ids: Список ID получателей
            batch_size: Размер пакета (по умолчанию BATCH_SIZE)

        Returns:
            Словарь с результатом:
            {
                'success': True/False,
                'created_count': int,
                'total_count': int,
                'batches_processed': int,
                'errors': []
            }
        """
        from notifications.models import Broadcast, BroadcastRecipient
        from accounts.models import User

        batch_size = batch_size or cls.BATCH_SIZE
        errors = []
        created_count = 0
        batches_processed = 0

        try:
            # Проверить существование рассылки
            broadcast = Broadcast.objects.get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.error(f"[create_batch] Broadcast {broadcast_id} not found")
            return {
                'success': False,
                'error': f'Broadcast {broadcast_id} not found',
                'created_count': 0,
                'total_count': 0,
                'batches_processed': 0,
                'errors': []
            }

        total_count = len(recipient_ids)

        try:
            # Разделить на батчи
            for i in range(0, total_count, batch_size):
                batch_ids = recipient_ids[i:i + batch_size]

                # Получить пользователей для этого батча
                users = User.objects.filter(id__in=batch_ids, is_active=True)

                if not users.exists():
                    logger.warning(
                        f"[create_batch] No active users found in batch {batches_processed + 1}"
                    )
                    continue

                # Создать BroadcastRecipient для каждого пользователя
                broadcast_recipients = [
                    BroadcastRecipient(broadcast=broadcast, recipient=user)
                    for user in users
                ]

                # Использовать bulk_create с ignore_conflicts для обработки дубликатов
                with transaction.atomic():
                    created_objs = BroadcastRecipient.objects.bulk_create(
                        broadcast_recipients,
                        batch_size=batch_size,
                        ignore_conflicts=True
                    )

                    created_count += len(created_objs)
                    batches_processed += 1

                    logger.debug(
                        f"[create_batch] Broadcast {broadcast_id}: "
                        f"batch {batches_processed} processed, "
                        f"created {len(created_objs)} records"
                    )

        except Exception as e:
            logger.error(
                f"[create_batch] Error processing batch for broadcast {broadcast_id}: {str(e)}",
                exc_info=True
            )
            errors.append(str(e))
            return {
                'success': False,
                'error': str(e),
                'created_count': created_count,
                'total_count': total_count,
                'batches_processed': batches_processed,
                'errors': errors
            }

        logger.info(
            f"[create_batch] Broadcast {broadcast_id}: "
            f"created {created_count} recipients in {batches_processed} batches"
        )

        return {
            'success': True,
            'created_count': created_count,
            'total_count': total_count,
            'batches_processed': batches_processed,
            'errors': errors
        }

    @classmethod
    def send_to_group_batch(
        cls,
        broadcast_id: int,
        target_group: str,
        target_filter: Optional[Dict] = None,
        batch_size: int = None
    ) -> Dict:
        """
        Отправить рассылку целевой группе с пакетной обработкой

        Args:
            broadcast_id: ID рассылки
            target_group: Целевая группа (all_students, by_subject, etc.)
            target_filter: Фильтры для целевой группы
            batch_size: Размер пакета

        Returns:
            Словарь с результатом отправки
        """
        from notifications.models import Broadcast, BroadcastRecipient
        from accounts.models import User

        batch_size = batch_size or cls.SEND_BATCH_SIZE
        target_filter = target_filter or {}

        try:
            broadcast = Broadcast.objects.get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.error(f"[send_batch] Broadcast {broadcast_id} not found")
            return {'success': False, 'error': f'Broadcast {broadcast_id} not found'}

        # Получить получателей в зависимости от группы
        recipients_qs = cls._get_recipients_queryset(target_group, target_filter)

        if not recipients_qs.exists():
            logger.warning(
                f"[send_batch] No recipients found for group={target_group}"
            )
            return {
                'success': False,
                'error': f'No recipients found for group {target_group}',
                'sent_count': 0,
                'failed_count': 0
            }

        total_count = recipients_qs.count()
        sent_count = 0
        failed_count = 0
        batches_processed = 0

        try:
            # Обработать получателей батчами
            for i in range(0, total_count, batch_size):
                batch_recipients = recipients_qs[i:i + batch_size]

                with transaction.atomic():
                    for recipient in batch_recipients:
                        try:
                            # Создать или обновить BroadcastRecipient
                            br, created = BroadcastRecipient.objects.get_or_create(
                                broadcast=broadcast,
                                recipient=recipient
                            )

                            if created:
                                sent_count += 1

                        except Exception as e:
                            logger.error(
                                f"[send_batch] Error processing recipient {recipient.id}: {str(e)}"
                            )
                            failed_count += 1

                batches_processed += 1
                logger.debug(
                    f"[send_batch] Broadcast {broadcast_id}: "
                    f"batch {batches_processed} processed"
                )

        except Exception as e:
            logger.error(
                f"[send_batch] Error sending broadcast {broadcast_id}: {str(e)}",
                exc_info=True
            )
            return {
                'success': False,
                'error': str(e),
                'sent_count': sent_count,
                'failed_count': failed_count
            }

        logger.info(
            f"[send_batch] Broadcast {broadcast_id}: "
            f"sent {sent_count}, failed {failed_count}, "
            f"in {batches_processed} batches"
        )

        return {
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_count': total_count,
            'batches_processed': batches_processed
        }

    @classmethod
    def send_to_role_batch(
        cls,
        broadcast_id: int,
        role: str,
        batch_size: int = None
    ) -> Dict:
        """
        Отправить рассылку пользователям определенной роли

        Args:
            broadcast_id: ID рассылки
            role: Роль пользователя (student, teacher, tutor, parent)
            batch_size: Размер пакета

        Returns:
            Словарь с результатом
        """
        return cls.send_to_group_batch(
            broadcast_id,
            target_group=f'all_{role}s',
            batch_size=batch_size
        )

    @classmethod
    def send_to_custom_list_batch(
        cls,
        broadcast_id: int,
        user_ids: List[int],
        batch_size: int = None
    ) -> Dict:
        """
        Отправить рассылку кастомному списку пользователей

        Args:
            broadcast_id: ID рассылки
            user_ids: Список ID пользователей
            batch_size: Размер пакета

        Returns:
            Словарь с результатом
        """
        return cls.send_to_group_batch(
            broadcast_id,
            target_group='custom',
            target_filter={'user_ids': user_ids},
            batch_size=batch_size
        )

    @classmethod
    def retry_failed_batch(
        cls,
        broadcast_id: int,
        max_retries: int = None,
        batch_size: int = None
    ) -> Dict:
        """
        Повторить отправку неудачных получателей с пакетной обработкой

        Args:
            broadcast_id: ID рассылки
            max_retries: Максимум повторов
            batch_size: Размер пакета

        Returns:
            Словарь с результатом
        """
        from notifications.models import Broadcast, BroadcastRecipient

        batch_size = batch_size or cls.SEND_BATCH_SIZE
        max_retries = max_retries or cls.MAX_RETRIES

        try:
            broadcast = Broadcast.objects.select_for_update().get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.error(f"[retry_batch] Broadcast {broadcast_id} not found")
            return {'success': False, 'error': f'Broadcast {broadcast_id} not found'}

        # Получить неудачных получателей
        failed_recipients = BroadcastRecipient.objects.filter(
            broadcast=broadcast,
            telegram_sent=False
        ).select_related('recipient')

        if not failed_recipients.exists():
            logger.info(f"[retry_batch] No failed recipients for broadcast {broadcast_id}")
            return {
                'success': True,
                'message': 'No failed recipients to retry',
                'retried_count': 0
            }

        total_failed = failed_recipients.count()
        retried_count = 0

        try:
            # Обработать неудачные записи батчами
            for i in range(0, total_failed, batch_size):
                batch = failed_recipients[i:i + batch_size]

                with transaction.atomic():
                    for recipient_record in batch:
                        # Сбросить флаг отправки для повтора
                        recipient_record.telegram_sent = False
                        recipient_record.telegram_error = None
                        recipient_record.save(
                            update_fields=['telegram_sent', 'telegram_error']
                        )
                        retried_count += 1

                logger.debug(
                    f"[retry_batch] Broadcast {broadcast_id}: "
                    f"reset {retried_count}/{total_failed} failed recipients"
                )

        except Exception as e:
            logger.error(
                f"[retry_batch] Error retrying broadcast {broadcast_id}: {str(e)}",
                exc_info=True
            )
            return {
                'success': False,
                'error': str(e),
                'retried_count': retried_count
            }

        logger.info(
            f"[retry_batch] Broadcast {broadcast_id}: "
            f"reset {retried_count} failed recipients for retry"
        )

        return {
            'success': True,
            'message': f'Queued {retried_count} failed recipients for retry',
            'retried_count': retried_count,
            'total_failed': total_failed
        }

    @classmethod
    def get_batch_status(cls, broadcast_id: int) -> Dict:
        """
        Получить статус пакетной обработки рассылки

        Args:
            broadcast_id: ID рассылки

        Returns:
            Словарь со статусом обработки
        """
        from notifications.models import Broadcast, BroadcastRecipient

        try:
            broadcast = Broadcast.objects.get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.warning(f"[get_status] Broadcast {broadcast_id} not found")
            raise ValueError(f"Broadcast {broadcast_id} not found")

        # Получить статистику
        total_recipients = broadcast.recipient_count
        sent_count = BroadcastRecipient.objects.filter(
            broadcast=broadcast,
            telegram_sent=True
        ).count()
        failed_count = BroadcastRecipient.objects.filter(
            broadcast=broadcast,
            telegram_sent=False,
            telegram_error__isnull=False
        ).count()
        pending_count = total_recipients - sent_count - failed_count

        # Рассчитать процент
        progress_pct = 0
        if total_recipients > 0:
            progress_pct = round(
                ((sent_count + failed_count) / total_recipients) * 100
            )

        logger.info(
            f"[get_status] Broadcast {broadcast_id}: "
            f"total={total_recipients}, sent={sent_count}, "
            f"failed={failed_count}, pending={pending_count}, "
            f"progress={progress_pct}%"
        )

        return {
            'broadcast_id': broadcast_id,
            'status': broadcast.status,
            'total_recipients': total_recipients,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'pending_count': pending_count,
            'progress_pct': progress_pct,
            'created_at': broadcast.created_at,
            'sent_at': broadcast.sent_at,
            'completed_at': broadcast.completed_at
        }

    @staticmethod
    def _get_recipients_queryset(
        target_group: str,
        target_filter: Dict
    ) -> QuerySet:
        """
        Получить queryset получателей по целевой группе

        Args:
            target_group: Целевая группа
            target_filter: Фильтры

        Returns:
            QuerySet пользователей
        """
        from accounts.models import User, StudentProfile
        from materials.models import SubjectEnrollment, TeacherSubject

        if target_group == 'all_students':
            return User.objects.filter(role='student', is_active=True)

        elif target_group == 'all_teachers':
            return User.objects.filter(role='teacher', is_active=True)

        elif target_group == 'all_tutors':
            return User.objects.filter(role='tutor', is_active=True)

        elif target_group == 'all_parents':
            return User.objects.filter(role='parent', is_active=True)

        elif target_group == 'by_subject':
            subject_id = target_filter.get('subject_id')
            if not subject_id:
                return User.objects.none()

            # Получить студентов и учителей по предмету
            student_ids = SubjectEnrollment.objects.filter(
                subject_id=subject_id
            ).values_list('student_id', flat=True)

            teacher_ids = TeacherSubject.objects.filter(
                subject_id=subject_id
            ).values_list('teacher_id', flat=True)

            return User.objects.filter(
                Q(id__in=student_ids) | Q(id__in=teacher_ids),
                is_active=True
            ).distinct()

        elif target_group == 'by_tutor':
            tutor_id = target_filter.get('tutor_id')
            if not tutor_id:
                return User.objects.none()

            student_ids = StudentProfile.objects.filter(
                tutor_id=tutor_id
            ).values_list('user_id', flat=True)

            return User.objects.filter(id__in=student_ids, is_active=True)

        elif target_group == 'by_teacher':
            teacher_id = target_filter.get('teacher_id')
            if not teacher_id:
                return User.objects.none()

            student_ids = SubjectEnrollment.objects.filter(
                teacher_id=teacher_id
            ).values_list('student_id', flat=True)

            return User.objects.filter(id__in=student_ids, is_active=True)

        elif target_group == 'custom':
            user_ids = target_filter.get('user_ids', [])
            if not user_ids:
                return User.objects.none()

            return User.objects.filter(id__in=user_ids, is_active=True)

        return User.objects.none()


# ============= CELERY TASKS =============

@shared_task(bind=True, max_retries=3)
def process_broadcast_batch_async(
    self,
    broadcast_id: int,
    target_group: str,
    target_filter: Optional[Dict] = None,
    batch_size: int = None
) -> Dict:
    """
    Асинхронная задача для обработки рассылки с пакетизацией

    Args:
        broadcast_id: ID рассылки
        target_group: Целевая группа
        target_filter: Фильтры целевой группы
        batch_size: Размер пакета

    Returns:
        Словарь с результатом
    """
    try:
        result = BroadcastBatchProcessor.send_to_group_batch(
            broadcast_id,
            target_group,
            target_filter,
            batch_size
        )

        if result['success']:
            logger.info(
                f"[process_batch_async] Broadcast {broadcast_id} processed: "
                f"sent={result.get('sent_count')}, "
                f"failed={result.get('failed_count')}"
            )
            return result
        else:
            raise Exception(result['error'])

    except Exception as exc:
        logger.error(
            f"[process_batch_async] Error processing broadcast {broadcast_id}: {str(exc)}",
            exc_info=True
        )

        if self.request.retries >= self.max_retries:
            logger.error(
                f"[process_batch_async] Max retries reached for broadcast {broadcast_id}"
            )
            return {'success': False, 'error': str(exc)}

        # Повторить с экспоненциальной задержкой
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries)
        )


@shared_task(bind=True, max_retries=2)
def retry_failed_broadcasts_async(
    self,
    broadcast_id: int,
    batch_size: int = None
) -> Dict:
    """
    Асинхронная задача для повтора неудачных отправок

    Args:
        broadcast_id: ID рассылки
        batch_size: Размер пакета

    Returns:
        Словарь с результатом
    """
    try:
        result = BroadcastBatchProcessor.retry_failed_batch(
            broadcast_id,
            batch_size=batch_size
        )

        if result['success']:
            logger.info(
                f"[retry_async] Broadcast {broadcast_id}: "
                f"retried {result.get('retried_count')} recipients"
            )
            return result
        else:
            raise Exception(result['error'])

    except Exception as exc:
        logger.error(
            f"[retry_async] Error retrying broadcast {broadcast_id}: {str(exc)}",
            exc_info=True
        )

        if self.request.retries >= self.max_retries:
            return {'success': False, 'error': str(exc)}

        raise self.retry(exc=exc, countdown=300)
