"""
Celery Tasks для Invoice Notification System
Асинхронная отправка уведомлений с retry механизмом
"""
import logging
from typing import Optional
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 минута
    autoretry_for=(Exception,),
    retry_backoff=True,  # Экспоненциальная задержка
    retry_backoff_max=600,  # Максимум 10 минут
    retry_jitter=True  # Случайная задержка для избежания thundering herd
)
def send_invoice_notification(self, invoice_id: int, notification_type: str):
    """
    Основная задача отправки уведомлений о счетах

    Args:
        invoice_id: ID счета
        notification_type: Тип уведомления (sent, paid, overdue, viewed)

    Raises:
        Retry on failure
    """
    from invoices.models import Invoice
    from notifications.notification_service import NotificationService
    from applications.telegram_service import telegram_service

    try:
        # Получаем счет с оптимизированными запросами
        invoice = Invoice.objects.select_related(
            'tutor', 'student', 'parent',
            'tutor__tutor_profile',
            'student__student_profile',
            'parent__parent_profile'
        ).get(id=invoice_id)

        logger.info(f"Processing {notification_type} notification for invoice #{invoice_id}")

        # Создаем in-app уведомление через NotificationService
        ns = NotificationService()

        notification = None
        if notification_type == 'sent':
            notification = ns.notify_invoice_sent(invoice)
            recipient = invoice.parent
            email_template = 'invoice_sent'
            telegram_text = _format_telegram_invoice_sent(invoice)
        elif notification_type == 'paid':
            notification = ns.notify_invoice_paid(invoice)
            recipient = invoice.tutor
            email_template = 'invoice_paid'
            telegram_text = _format_telegram_invoice_paid(invoice)
        elif notification_type == 'overdue':
            notification = ns.notify_invoice_overdue(invoice)
            recipient = invoice.parent
            email_template = 'invoice_overdue'
            telegram_text = _format_telegram_invoice_overdue(invoice)
        elif notification_type == 'viewed':
            notification = ns.notify_invoice_viewed(invoice)
            recipient = invoice.tutor
            email_template = 'invoice_viewed'
            telegram_text = _format_telegram_invoice_viewed(invoice)
        else:
            logger.error(f"Unknown notification type: {notification_type}")
            return

        # Проверяем настройки пользователя
        if not hasattr(recipient, 'notification_settings'):
            logger.warning(f"User {recipient.id} has no notification settings, creating defaults")
            from notifications.models import NotificationSettings
            NotificationSettings.objects.get_or_create(user=recipient)

        settings_obj = getattr(recipient, 'notification_settings', None)

        # Отправляем email если разрешено
        if settings_obj and settings_obj.email_notifications and recipient.email:
            send_invoice_email.delay(invoice_id, recipient.id, email_template)

        # Отправляем Telegram если разрешено
        # Telegram настройки проверяются внутри telegram_service
        send_invoice_telegram.delay(invoice_id, recipient.id, telegram_text)

        logger.info(f"Successfully queued notifications for invoice #{invoice_id}, type={notification_type}")

        return {
            'invoice_id': invoice_id,
            'notification_type': notification_type,
            'notification_id': notification.id if notification else None,
            'status': 'success'
        }

    except Invoice.DoesNotExist:
        logger.error(f"Invoice #{invoice_id} not found")
        # Не повторяем если счет не найден
        return {'error': 'Invoice not found', 'invoice_id': invoice_id}

    except Exception as e:
        logger.error(f"Failed to send notification for invoice #{invoice_id}: {e}", exc_info=True)
        # Celery автоматически повторит задачу
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,  # 2 минуты
    autoretry_for=(Exception,),
    retry_backoff=True
)
def send_invoice_email(self, invoice_id: int, recipient_id: int, template_name: str):
    """
    Отправка email уведомления о счете

    Args:
        invoice_id: ID счета
        recipient_id: ID получателя
        template_name: Имя шаблона (invoice_sent, invoice_paid, etc.)
    """
    from invoices.models import Invoice

    try:
        invoice = Invoice.objects.select_related(
            'tutor', 'student', 'parent', 'enrollment__subject'
        ).get(id=invoice_id)

        recipient = User.objects.get(id=recipient_id)

        if not recipient.email:
            logger.warning(f"User {recipient_id} has no email, skipping email notification")
            return {'status': 'skipped', 'reason': 'no_email'}

        # Формируем контекст для шаблона
        context = {
            'invoice': invoice,
            'recipient': recipient,
            'tutor': invoice.tutor,
            'student': invoice.student,
            'parent': invoice.parent,
            'amount': invoice.amount,
            'due_date': invoice.due_date,
            'description': invoice.description,
            'payment_url': _get_payment_url(invoice),
            'invoice_url': _get_invoice_url(invoice),
            'current_year': timezone.now().year,
        }

        # Рендерим HTML шаблон
        html_content = render_to_string(
            f'emails/invoices/{template_name}.html',
            context
        )

        # Определяем тему письма
        subject = _get_email_subject(template_name, invoice)

        # Отправляем email
        send_mail(
            subject=subject,
            message='',  # Plain text version (можно добавить позже)
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            html_message=html_content,
            fail_silently=False
        )

        logger.info(f"Email sent to {recipient.email} for invoice #{invoice_id}, template={template_name}")

        return {
            'invoice_id': invoice_id,
            'recipient_id': recipient_id,
            'template': template_name,
            'status': 'sent'
        }

    except Invoice.DoesNotExist:
        logger.error(f"Invoice #{invoice_id} not found for email notification")
        return {'error': 'Invoice not found'}

    except User.DoesNotExist:
        logger.error(f"User #{recipient_id} not found for email notification")
        return {'error': 'User not found'}

    except Exception as e:
        logger.error(f"Failed to send email for invoice #{invoice_id}: {e}", exc_info=True)
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def send_invoice_telegram(self, invoice_id: int, recipient_id: int, message_text: str):
    """
    Отправка Telegram уведомления о счете

    Args:
        invoice_id: ID счета
        recipient_id: ID получателя
        message_text: Текст сообщения (уже отформатированный)
    """
    from applications.telegram_service import telegram_service
    from invoices.models import Invoice

    try:
        recipient = User.objects.select_related(
            'parent_profile', 'tutor_profile', 'student_profile'
        ).get(id=recipient_id)

        # Получаем telegram_id из профиля
        telegram_id = None
        if hasattr(recipient, 'parent_profile') and recipient.parent_profile.telegram:
            telegram_id = recipient.parent_profile.telegram
        elif hasattr(recipient, 'tutor_profile') and recipient.tutor_profile.telegram:
            telegram_id = recipient.tutor_profile.telegram
        elif hasattr(recipient, 'student_profile') and recipient.student_profile.telegram:
            telegram_id = recipient.student_profile.telegram

        if not telegram_id:
            logger.info(f"User {recipient_id} has no telegram_id, skipping telegram notification")
            return {'status': 'skipped', 'reason': 'no_telegram_id'}

        # Очищаем telegram_id от @ если есть
        telegram_id = telegram_id.lstrip('@')

        # Отправляем через TelegramService
        result = telegram_service.send_message(
            text=message_text,
            parse_mode='HTML',
            chat_id=telegram_id
        )

        if result and result.get('ok'):
            logger.info(f"Telegram notification sent to {telegram_id} for invoice #{invoice_id}")

            # Сохраняем message_id в счете для последующего обновления
            if result.get('result', {}).get('message_id'):
                invoice = Invoice.objects.get(id=invoice_id)
                invoice.telegram_message_id = str(result['result']['message_id'])
                invoice.save(update_fields=['telegram_message_id'])

            return {
                'invoice_id': invoice_id,
                'recipient_id': recipient_id,
                'telegram_id': telegram_id,
                'status': 'sent'
            }
        else:
            logger.warning(f"Telegram notification failed for invoice #{invoice_id}")
            return {'status': 'failed', 'reason': 'telegram_api_error'}

    except User.DoesNotExist:
        logger.error(f"User #{recipient_id} not found for telegram notification")
        return {'error': 'User not found'}

    except Exception as e:
        logger.error(f"Failed to send telegram for invoice #{invoice_id}: {e}", exc_info=True)
        raise


# Helper functions для форматирования сообщений

def _format_telegram_invoice_sent(invoice) -> str:
    """Форматирование Telegram сообщения о выставленном счете"""
    return f"""
💰 <b>Новый счет на оплату</b>

<b>Счет №:</b> {invoice.id}
<b>Сумма:</b> {invoice.amount} руб.
<b>Срок оплаты:</b> {invoice.due_date.strftime('%d.%m.%Y')}

<b>Ученик:</b> {invoice.student.get_full_name()}
<b>Тьютор:</b> {invoice.tutor.get_full_name()}

<b>Описание услуг:</b>
{invoice.description[:500]}

<a href="{_get_payment_url(invoice)}">Оплатить счет</a>
"""


def _format_telegram_invoice_paid(invoice) -> str:
    """Форматирование Telegram сообщения об оплате счета"""
    return f"""
✅ <b>Счет оплачен</b>

<b>Счет №:</b> {invoice.id}
<b>Сумма:</b> {invoice.amount} руб.
<b>Дата оплаты:</b> {invoice.paid_at.strftime('%d.%m.%Y %H:%M') if invoice.paid_at else 'Неизвестно'}

<b>Ученик:</b> {invoice.student.get_full_name()}
<b>Родитель:</b> {invoice.parent.get_full_name()}

Спасибо за оплату!
"""


def _format_telegram_invoice_overdue(invoice) -> str:
    """Форматирование Telegram сообщения о просроченном счете"""
    days_overdue = (timezone.now().date() - invoice.due_date).days
    return f"""
⚠️ <b>Просроченный счет</b>

<b>Счет №:</b> {invoice.id}
<b>Сумма:</b> {invoice.amount} руб.
<b>Срок оплаты был:</b> {invoice.due_date.strftime('%d.%m.%Y')}
<b>Просрочено дней:</b> {days_overdue}

<b>Ученик:</b> {invoice.student.get_full_name()}

Пожалуйста, оплатите счет как можно скорее.

<a href="{_get_payment_url(invoice)}">Оплатить сейчас</a>
"""


def _format_telegram_invoice_viewed(invoice) -> str:
    """Форматирование Telegram сообщения о просмотре счета"""
    return f"""
👁 <b>Счет просмотрен</b>

<b>Счет №:</b> {invoice.id}
<b>Сумма:</b> {invoice.amount} руб.
<b>Родитель:</b> {invoice.parent.get_full_name()}

Родитель просмотрел ваш счет.
"""


def _get_payment_url(invoice) -> str:
    """Получение URL для оплаты счета"""
    # TODO: Заменить на реальный URL после настройки фронтенда
    from core.env_config import EnvConfig
    env_config = EnvConfig()
    frontend_url = env_config.get_frontend_url()
    return f"{frontend_url}/dashboard/parent/invoices/{invoice.id}/pay"


def _get_invoice_url(invoice) -> str:
    """Получение URL для просмотра счета"""
    from core.env_config import EnvConfig
    env_config = EnvConfig()
    frontend_url = env_config.get_frontend_url()
    # URL зависит от роли пользователя (tutor/parent)
    return f"{frontend_url}/dashboard/invoices/{invoice.id}"


def _get_email_subject(template_name: str, invoice) -> str:
    """Получение темы письма по имени шаблона"""
    subjects = {
        'invoice_sent': f'Новый счет #{invoice.id} на сумму {invoice.amount} руб.',
        'invoice_paid': f'Счет #{invoice.id} оплачен',
        'invoice_overdue': f'Напоминание: счет #{invoice.id} просрочен',
        'invoice_viewed': f'Счет #{invoice.id} просмотрен родителем',
    }
    return subjects.get(template_name, f'Уведомление о счете #{invoice.id}')


# Периодические задачи

@shared_task
def check_overdue_invoices():
    """
    Периодическая задача проверки просроченных счетов
    Должна запускаться раз в день (например, в 10:00)

    Находит счета со статусом SENT или VIEWED, у которых due_date < сегодня,
    помечает их как OVERDUE и отправляет уведомления
    """
    from invoices.models import Invoice
    from django.db.models import Q

    today = timezone.now().date()

    # Находим просроченные счета
    overdue_invoices = Invoice.objects.select_related(
        'tutor', 'student', 'parent'
    ).filter(
        Q(status=Invoice.Status.SENT) | Q(status=Invoice.Status.VIEWED),
        due_date__lt=today
    )

    updated_count = 0
    notification_count = 0

    for invoice in overdue_invoices:
        # Помечаем как просроченный
        if invoice.mark_as_overdue():
            updated_count += 1

            # Отправляем уведомление
            try:
                send_invoice_notification.delay(invoice.id, 'overdue')
                notification_count += 1
            except Exception as e:
                logger.error(f"Failed to queue overdue notification for invoice #{invoice.id}: {e}")

    logger.info(
        f"Overdue invoices check completed: "
        f"{updated_count} invoices marked as overdue, "
        f"{notification_count} notifications queued"
    )

    return {
        'checked': overdue_invoices.count(),
        'updated': updated_count,
        'notifications_queued': notification_count,
        'date': today.isoformat()
    }
