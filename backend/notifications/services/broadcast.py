"""
Broadcast Service - Сервис для управления массовыми рассылками
Предоставляет функциональность отправки с отслеживанием прогресса, отмены и повторной попытки.
Использует BroadcastBatchProcessor для оптимизированной пакетной обработки.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime

from django.utils import timezone
from django.db import transaction
from celery import shared_task

logger = logging.getLogger(__name__)

# Import batch processor for optimized batch operations
try:
    from notifications.broadcast_batch import (
        BroadcastBatchProcessor,
        process_broadcast_batch_async,
        retry_failed_broadcasts_async
    )
except ImportError:
    logger.warning("BroadcastBatchProcessor not available")


class BroadcastService:
    """
    Сервис для управления массовыми рассылками
    """

    @staticmethod
    def get_progress(broadcast_id: int) -> Dict:
        """
        Получить информацию о прогрессе рассылки

        Args:
            broadcast_id: ID рассылки

        Returns:
            Словарь с информацией о прогрессе:
            {
                'status': 'pending|processing|completed|failed|cancelled',
                'total_recipients': 500,
                'sent_count': 450,
                'failed_count': 50,
                'pending_count': 0,
                'progress_pct': 90,
                'error_summary': '50 failed: network error'
            }
        """
        from notifications.models import Broadcast, BroadcastRecipient

        try:
            broadcast = Broadcast.objects.get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.warning(f"[get_progress] Broadcast {broadcast_id} not found")
            raise ValueError(f"Broadcast {broadcast_id} not found")

        # Получить статистику по получателям
        total_recipients = broadcast.recipient_count
        sent_count = broadcast.sent_count
        failed_count = broadcast.failed_count
        pending_count = total_recipients - sent_count - failed_count

        # Рассчитать процент прогресса
        progress_pct = 0
        if total_recipients > 0:
            progress_pct = round((sent_count / total_recipients) * 100)

        # Получить сводку ошибок
        error_summary = ""
        if failed_count > 0:
            # Получить наиболее частую ошибку
            failed_recipients = BroadcastRecipient.objects.filter(
                broadcast=broadcast,
                telegram_sent=False,
                telegram_error__isnull=False
            ).values('telegram_error').distinct()

            if failed_recipients.exists():
                error_msg = failed_recipients.first()['telegram_error']
                error_summary = f"{failed_count} failed: {error_msg}"
            else:
                error_summary = f"{failed_count} failed: unknown error"

        logger.info(
            f"[get_progress] Broadcast {broadcast_id}: "
            f"status={broadcast.status}, sent={sent_count}, "
            f"failed={failed_count}, pending={pending_count}"
        )

        return {
            'id': broadcast.id,
            'status': broadcast.status,
            'total_recipients': total_recipients,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'pending_count': pending_count,
            'progress_pct': progress_pct,
            'error_summary': error_summary,
            'created_at': broadcast.created_at,
            'sent_at': broadcast.sent_at,
            'completed_at': broadcast.completed_at,
        }

    @staticmethod
    @transaction.atomic
    def cancel_broadcast(broadcast_id: int) -> Dict:
        """
        Отменить рассылку и остановить дальнейшую отправку

        Args:
            broadcast_id: ID рассылки

        Returns:
            Словарь с результатом отмены
        """
        from notifications.models import Broadcast

        try:
            broadcast = Broadcast.objects.select_for_update().get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.warning(f"[cancel_broadcast] Broadcast {broadcast_id} not found")
            raise ValueError(f"Broadcast {broadcast_id} not found")

        # Проверить статус - нельзя отменить уже завершенную рассылку
        if broadcast.status in [
            Broadcast.Status.SENT,
            Broadcast.Status.COMPLETED,
            Broadcast.Status.CANCELLED
        ]:
            logger.warning(
                f"[cancel_broadcast] Broadcast {broadcast_id} already {broadcast.status}"
            )
            raise ValueError(f"Cannot cancel broadcast with status {broadcast.status}")

        # Обновить статус
        broadcast.status = Broadcast.Status.CANCELLED
        broadcast.completed_at = timezone.now()
        broadcast.save()

        logger.info(
            f"[cancel_broadcast] Broadcast {broadcast_id} cancelled. "
            f"Pending recipients: {broadcast.recipient_count - broadcast.sent_count - broadcast.failed_count}"
        )

        return {
            'success': True,
            'message': 'Рассылка успешно отменена',
            'broadcast_id': broadcast.id,
            'cancelled_at': broadcast.completed_at,
        }

    @staticmethod
    @transaction.atomic
    def retry_failed(broadcast_id: int, max_retries: int = 3) -> Dict:
        """
        Повторить отправку для неудачных получателей

        Args:
            broadcast_id: ID рассылки
            max_retries: максимальное количество повторных попыток

        Returns:
            Словарь с результатом повторной попытки
        """
        from notifications.models import Broadcast, BroadcastRecipient

        try:
            broadcast = Broadcast.objects.select_for_update().get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.warning(f"[retry_failed] Broadcast {broadcast_id} not found")
            raise ValueError(f"Broadcast {broadcast_id} not found")

        # Получить неудачных получателей
        failed_recipients = BroadcastRecipient.objects.filter(
            broadcast=broadcast,
            telegram_sent=False
        ).select_related('recipient')

        if not failed_recipients.exists():
            logger.info(f"[retry_failed] No failed recipients for broadcast {broadcast_id}")
            return {
                'success': True,
                'message': 'Нет неудачных отправок для повторной попытки',
                'retried_count': 0,
                'broadcast_id': broadcast.id,
            }

        # Обновить статус на повторную отправку
        broadcast.status = Broadcast.Status.SENDING
        broadcast.save()

        # Запустить асинхронную задачу повторной отправки
        from .broadcast import send_broadcast_async
        task = send_broadcast_async.delay(broadcast_id, only_failed=True)

        retried_count = failed_recipients.count()
        logger.info(
            f"[retry_failed] Broadcast {broadcast_id}: "
            f"queued {retried_count} failed recipients for retry (task_id: {task.id})"
        )

        return {
            'success': True,
            'message': f'Повторная отправка запущена для {retried_count} получателей',
            'retried_count': retried_count,
            'broadcast_id': broadcast.id,
            'task_id': task.id,
        }

    @staticmethod
    @transaction.atomic
    def update_progress(broadcast_id: int, sent_count: int, failed_count: int) -> None:
        """
        Обновить прогресс рассылки

        Args:
            broadcast_id: ID рассылки
            sent_count: количество успешно отправленных
            failed_count: количество неудачных отправок
        """
        from notifications.models import Broadcast

        try:
            broadcast = Broadcast.objects.select_for_update().get(id=broadcast_id)
        except Broadcast.DoesNotExist:
            logger.warning(f"[update_progress] Broadcast {broadcast_id} not found")
            return

        # Обновить счетчики
        broadcast.sent_count = sent_count
        broadcast.failed_count = failed_count

        # Проверить, завершена ли рассылка
        total_processed = sent_count + failed_count
        if total_processed >= broadcast.recipient_count:
            broadcast.status = Broadcast.Status.COMPLETED
            broadcast.completed_at = timezone.now()

            # Если все неудачно - отметить как FAILED
            if sent_count == 0 and failed_count > 0:
                broadcast.status = Broadcast.Status.FAILED

        broadcast.save()
        logger.debug(
            f"[update_progress] Broadcast {broadcast_id}: "
            f"sent={sent_count}, failed={failed_count}"
        )

    @staticmethod
    def send_to_group_batch(
        broadcast_id: int,
        target_group: str,
        target_filter: Optional[Dict] = None,
        batch_size: int = None
    ) -> Dict:
        """
        Отправить рассылку целевой группе с пакетной обработкой

        Args:
            broadcast_id: ID рассылки
            target_group: Целевая группа
            target_filter: Фильтры
            batch_size: Размер пакета

        Returns:
            Словарь с результатом
        """
        try:
            return BroadcastBatchProcessor.send_to_group_batch(
                broadcast_id,
                target_group,
                target_filter,
                batch_size
            )
        except Exception as e:
            logger.error(
                f"[send_to_group_batch] Error: {str(e)}",
                exc_info=True
            )
            return {'success': False, 'error': str(e)}

    @staticmethod
    def send_to_role_batch(
        broadcast_id: int,
        role: str,
        batch_size: int = None
    ) -> Dict:
        """
        Отправить рассылку пользователям определенной роли

        Args:
            broadcast_id: ID рассылки
            role: Роль пользователя
            batch_size: Размер пакета

        Returns:
            Словарь с результатом
        """
        try:
            return BroadcastBatchProcessor.send_to_role_batch(
                broadcast_id,
                role,
                batch_size
            )
        except Exception as e:
            logger.error(
                f"[send_to_role_batch] Error: {str(e)}",
                exc_info=True
            )
            return {'success': False, 'error': str(e)}

    @staticmethod
    def send_to_custom_list_batch(
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
        try:
            return BroadcastBatchProcessor.send_to_custom_list_batch(
                broadcast_id,
                user_ids,
                batch_size
            )
        except Exception as e:
            logger.error(
                f"[send_to_custom_list_batch] Error: {str(e)}",
                exc_info=True
            )
            return {'success': False, 'error': str(e)}

    @staticmethod
    def create_batch_recipients(
        broadcast_id: int,
        recipient_ids: List[int],
        batch_size: int = None
    ) -> Dict:
        """
        Создать BroadcastRecipient записи в батчах

        Args:
            broadcast_id: ID рассылки
            recipient_ids: Список ID получателей
            batch_size: Размер пакета

        Returns:
            Словарь с результатом
        """
        try:
            return BroadcastBatchProcessor.create_broadcast_recipients_batch(
                broadcast_id,
                recipient_ids,
                batch_size
            )
        except Exception as e:
            logger.error(
                f"[create_batch_recipients] Error: {str(e)}",
                exc_info=True
            )
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_batch_status(broadcast_id: int) -> Dict:
        """
        Получить статус пакетной обработки рассылки

        Args:
            broadcast_id: ID рассылки

        Returns:
            Словарь со статусом
        """
        try:
            return BroadcastBatchProcessor.get_batch_status(broadcast_id)
        except ValueError as e:
            logger.warning(f"[get_batch_status] {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"[get_batch_status] Error: {str(e)}",
                exc_info=True
            )
            raise


# ============= CELERY TASKS =============

@shared_task(bind=True, max_retries=3)
def send_broadcast_async(self, broadcast_id: int, only_failed: bool = False) -> Dict:
    """
    Асинхронная задача для отправки рассылки через Celery

    Args:
        broadcast_id: ID рассылки
        only_failed: если True, отправить только неудачных получателей

    Returns:
        Словарь с результатом отправки
    """
    from notifications.models import Broadcast, BroadcastRecipient

    try:
        broadcast = Broadcast.objects.select_for_update().get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        logger.error(f"[send_broadcast_async] Broadcast {broadcast_id} not found")
        return {'success': False, 'error': f'Broadcast {broadcast_id} not found'}

    # Проверить, не отменена ли рассылка
    if broadcast.status == Broadcast.Status.CANCELLED:
        logger.info(f"[send_broadcast_async] Broadcast {broadcast_id} cancelled, skipping")
        return {'success': True, 'message': 'Broadcast cancelled, task skipped'}

    try:
        # Обновить статус на "отправляется"
        if broadcast.status == Broadcast.Status.DRAFT:
            broadcast.status = Broadcast.Status.SENDING
            broadcast.sent_at = timezone.now()
            broadcast.save()

        # Получить получателей для отправки
        if only_failed:
            recipients = BroadcastRecipient.objects.filter(
                broadcast=broadcast,
                telegram_sent=False
            ).select_related('recipient')
        else:
            recipients = BroadcastRecipient.objects.filter(
                broadcast=broadcast,
                telegram_sent=False
            ).select_related('recipient')

        if not recipients.exists():
            logger.info(f"[send_broadcast_async] No recipients to send for broadcast {broadcast_id}")
            BroadcastService.update_progress(broadcast_id, broadcast.sent_count, broadcast.failed_count)
            return {'success': True, 'message': 'No recipients to send'}

        # Отправить через Telegram
        from notifications.telegram_broadcast_service import TelegramBroadcastService
        service = TelegramBroadcastService()
        result = service.send_broadcast(broadcast, broadcast.message)

        # Обновить прогресс
        BroadcastService.update_progress(
            broadcast_id,
            result.get('sent', broadcast.sent_count),
            result.get('failed', broadcast.failed_count)
        )

        logger.info(
            f"[send_broadcast_async] Broadcast {broadcast_id} processed: "
            f"sent={result.get('sent')}, failed={result.get('failed')}"
        )

        return {
            'success': True,
            'broadcast_id': broadcast_id,
            'sent': result.get('sent', 0),
            'failed': result.get('failed', 0),
        }

    except Exception as exc:
        logger.error(
            f"[send_broadcast_async] Error sending broadcast {broadcast_id}: {str(exc)}",
            exc_info=True
        )

        # Обновить статус на FAILED если это последняя попытка
        if self.request.retries >= self.max_retries:
            broadcast.status = Broadcast.Status.FAILED
            broadcast.completed_at = timezone.now()
            broadcast.save()
            return {'success': False, 'error': str(exc)}

        # Иначе повторить с экспоненциальной задержкой
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True)
def process_scheduled_broadcasts(self) -> Dict:
    """
    Задача для обработки запланированных рассылок
    Запускается периодически через Celery Beat

    Returns:
        Словарь с результатом обработки
    """
    from notifications.models import Broadcast

    now = timezone.now()

    # Получить все рассылки, которые должны быть отправлены
    scheduled_broadcasts = Broadcast.objects.filter(
        status=Broadcast.Status.SCHEDULED,
        scheduled_at__lte=now
    )

    if not scheduled_broadcasts.exists():
        logger.debug("[process_scheduled_broadcasts] No scheduled broadcasts to process")
        return {'success': True, 'processed': 0}

    processed_count = 0
    for broadcast in scheduled_broadcasts:
        try:
            send_broadcast_async.delay(broadcast.id)
            processed_count += 1
            logger.info(
                f"[process_scheduled_broadcasts] Queued broadcast {broadcast.id} for sending"
            )
        except Exception as e:
            logger.error(
                f"[process_scheduled_broadcasts] Error processing broadcast {broadcast.id}: {str(e)}"
            )

    logger.info(
        f"[process_scheduled_broadcasts] Processed {processed_count} scheduled broadcasts"
    )

    return {
        'success': True,
        'processed': processed_count,
    }
