"""
Сигналы для автоматических действий при изменении счетов

ПРИМЕЧАНИЕ:
WebSocket broadcasts УЖЕ реализованы в InvoiceService (services.py).
Этот файл signals.py предназначен для дополнительных signal-based действий,
которые могут потребоваться в будущем (например, аудит, интеграции с внешними системами).

Текущая архитектура:
- WebSocket broadcasts вызываются явно из service layer (InvoiceService)
- Это обеспечивает лучший контроль транзакций и тестирование
- Telegram уведомления отправляются автоматически через сигналы
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Invoice, InvoiceStatusHistory
from .telegram_service import InvoiceTelegramService

logger = logging.getLogger(__name__)
User = get_user_model()


# Сигналы для дополнительного функционала (если потребуется)
# Не используются для WebSocket - это уже сделано в InvoiceService

@receiver(pre_save, sender=Invoice)
def track_invoice_status_change(sender, instance, **kwargs):
    """
    Отслеживает изменение статуса счета для корректной обработки в post_save.

    Устанавливает флаг _status_changed если статус изменился.
    Это необходимо для различения создания и обновления счета в post_save.
    """
    if instance.pk:
        try:
            old_instance = Invoice.objects.get(pk=instance.pk)
            instance._status_changed = old_instance.status != instance.status
        except Invoice.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False


@receiver(post_save, sender=Invoice)
def invoice_post_save(sender, instance, created, **kwargs):
    """
    Обработчик post_save для Invoice

    Функциональность:
    1. Логирование создания/обновления (аудит)
    2. Отправка Telegram уведомлений о счетах

    Используется только для дополнительных действий, НЕ для WebSocket broadcasts.
    WebSocket broadcasts вызываются явно из InvoiceService:
    - broadcast_invoice_created()
    - broadcast_invoice_status_change()
    - broadcast_invoice_paid()

    Этот сигнал используется для:
    - Дополнительного логирования
    - Telegram уведомлений
    - Аудита на уровне БД
    """
    # Логирование для аудита
    if created:
        logger.info(
            f'[Invoice Signal] Invoice #{instance.id} created: '
            f'tutor={instance.tutor.id}, student={instance.student.id}, '
            f'amount={instance.amount}, status={instance.status}'
        )
    else:
        logger.debug(
            f'[Invoice Signal] Invoice #{instance.id} updated: '
            f'status={instance.status}'
        )

    # Отправка Telegram уведомлений
    send_invoice_telegram_notification(instance, created)


@receiver(post_save, sender=InvoiceStatusHistory)
def invoice_status_history_post_save(sender, instance, created, **kwargs):
    """
    Обработчик post_save для InvoiceStatusHistory

    Логирует все изменения статусов для аудита
    """
    if created:
        logger.info(
            f'[Invoice Status History] Invoice #{instance.invoice.id}: '
            f'{instance.old_status} → {instance.new_status} '
            f'(changed by user #{instance.changed_by.id})'
        )


# ============================================================================
# TELEGRAM УВЕДОМЛЕНИЯ
# ============================================================================

def send_invoice_telegram_notification(invoice: Invoice, created: bool) -> None:
    """
    Отправить Telegram уведомление при создании или изменении статуса счета.

    Сценарии:
    1. Создан новый счет со статусом SENT → отправить уведомление родителю
    2. Счет оплачен (PAID) → отправить подтверждение родителю + уведомить тьютора
    3. Статус изменен (любой) → обновить существующее сообщение

    Args:
        invoice: Invoice объект
        created: True если счет только создан
    """
    try:
        service = InvoiceTelegramService()

        # Сценарий 1: Новый счет создан и уже отправлен
        if created and invoice.status == Invoice.Status.SENT:
            # Отправляем уведомление родителю
            if _has_telegram_id(invoice.parent):
                message_id = service.send_invoice_notification(invoice)

                if message_id:
                    # Сохраняем message_id для последующих обновлений
                    Invoice.objects.filter(pk=invoice.pk).update(telegram_message_id=message_id)
                    logger.info(
                        f"[Telegram] Уведомление отправлено для счета #{invoice.id} "
                        f"родителю {invoice.parent.get_full_name()} (message_id: {message_id})"
                    )

            return

        # Сценарий 2: Счет оплачен
        if not created and invoice.status == Invoice.Status.PAID:
            # Проверяем что это свежая оплата (защита от повторной отправки)
            if hasattr(invoice, '_status_changed') and invoice._status_changed:
                # Обновляем существующее сообщение родителю
                if invoice.telegram_message_id and _has_telegram_id(invoice.parent):
                    success = service.update_invoice_message(invoice)
                    if success:
                        logger.info(
                            f"[Telegram] Сообщение о счете #{invoice.id} обновлено после оплаты"
                        )

                # Отправляем подтверждение родителю
                if _has_telegram_id(invoice.parent):
                    confirmation_message_id = service.send_payment_confirmation(invoice)
                    if confirmation_message_id:
                        logger.info(
                            f"[Telegram] Подтверждение оплаты отправлено родителю "
                            f"{invoice.parent.get_full_name()} для счета #{invoice.id}"
                        )

                # Отправляем уведомление тьютору
                if _has_telegram_id(invoice.tutor):
                    _send_tutor_payment_notification(invoice, service)

            return

        # Сценарий 3: Статус изменен (не создание, не оплата)
        if not created and hasattr(invoice, '_status_changed') and invoice._status_changed:
            # Обновляем существующее сообщение если есть message_id
            if invoice.telegram_message_id and _has_telegram_id(invoice.parent):
                success = service.update_invoice_message(invoice)
                if success:
                    logger.info(
                        f"[Telegram] Сообщение о счете #{invoice.id} обновлено "
                        f"(новый статус: {invoice.get_status_display()})"
                    )

    except Exception as e:
        # Критично: ошибка при отправке уведомления
        logger.error(
            f"[Telegram] Ошибка при отправке уведомления для счета #{invoice.id}: {str(e)}",
            exc_info=True,
            extra={
                'invoice_id': invoice.id,
                'invoice_status': invoice.status,
                'error_type': type(e).__name__,
                'error': str(e)
            }
        )
        # Не прокидываем ошибку - логируем, но позволяем сохранению счета завершиться


def _has_telegram_id(user: User) -> bool:
    """
    Проверяет наличие telegram_id в профиле пользователя.

    Args:
        user: User объект

    Returns:
        True если у пользователя есть telegram_id
    """
    profile = None

    if user.role == 'parent' and hasattr(user, 'parent_profile'):
        profile = user.parent_profile
    elif user.role == 'tutor' and hasattr(user, 'tutor_profile'):
        profile = user.tutor_profile
    elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
        profile = user.teacher_profile
    elif user.role == 'student' and hasattr(user, 'student_profile'):
        profile = user.student_profile

    return profile is not None and bool(getattr(profile, 'telegram_id', None))


def _send_tutor_payment_notification(invoice: Invoice, service: InvoiceTelegramService) -> None:
    """
    Отправляет уведомление тьютору об оплате счета.

    Args:
        invoice: Оплаченный Invoice объект
        service: InvoiceTelegramService экземпляр
    """
    if not hasattr(invoice.tutor, 'tutor_profile'):
        logger.warning(f"[Telegram] У тьютора {invoice.tutor.id} нет профиля TutorProfile")
        return

    tutor_telegram_id = invoice.tutor.tutor_profile.telegram_id
    if not tutor_telegram_id:
        logger.info(
            f"[Telegram] У тьютора {invoice.tutor.id} не указан telegram_id, пропускаем отправку"
        )
        return

    # Форматируем сообщение для тьютора
    paid_date_str = invoice.paid_at.strftime('%d.%m.%Y в %H:%M') if invoice.paid_at else ''

    message = f"""
✅ <b>Счет оплачен</b>

🆔 <b>Номер счета:</b> #{invoice.id}
👤 <b>Студент:</b> {invoice.student.get_full_name()}
👨‍👩‍👦 <b>Родитель:</b> {invoice.parent.get_full_name()}
💰 <b>Сумма:</b> {invoice.amount} руб.
📅 <b>Дата оплаты:</b> {paid_date_str}

📝 <b>Описание:</b> {invoice.description}
"""

    # Добавляем информацию о предмете если есть
    if invoice.enrollment:
        message += f"\n📚 <b>Предмет:</b> {invoice.enrollment.subject.name}"

    message = message.strip()

    # Отправляем сообщение через низкоуровневый API
    import requests
    from django.conf import settings
    from core.json_utils import safe_json_response

    if service.disabled:
        logger.debug("[Telegram] Notifications disabled in test environment")
        return

    if not service.bot_token:
        logger.error("[Telegram] Bot token не настроен")
        return

    url = f"{service.base_url}/sendMessage"
    data = {
        'chat_id': tutor_telegram_id,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()

        result = safe_json_response(response)
        if result and result.get('ok'):
            message_id = str(result['result']['message_id'])
            logger.info(
                f"[Telegram] Уведомление об оплате счета #{invoice.id} отправлено тьютору "
                f"{invoice.tutor.get_full_name()} (message_id: {message_id})"
            )
        else:
            error_msg = result.get('description', 'Неизвестная ошибка') if result else 'Не удалось распарсить ответ'
            logger.error(f"[Telegram] Ошибка отправки уведомления тьютору: {error_msg}")

    except requests.exceptions.RequestException as e:
        logger.error(f"[Telegram] Ошибка при отправке уведомления тьютору: {e}")
    except Exception as e:
        logger.error(f"[Telegram] Неожиданная ошибка при отправке уведомления тьютору: {e}")
