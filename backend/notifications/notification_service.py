import logging
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import requests

from .models import Notification, NotificationSettings


logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """
    Универсальный сервис уведомлений:
    - Создает запись Notification
    - Отправляет in-app (WebSocket) уведомление в группу `notifications_{user_id}`
    - Учитывает пользовательские настройки NotificationSettings для фильтрации типов
    - Может быть расширен для email/SMS/Telegram каналов
    """

    def __init__(self) -> None:
        self.channel_layer = get_channel_layer()

    def _is_allowed_by_settings(self, user: User, notif_type: str) -> bool:
        try:
            settings = getattr(user, 'notification_settings', None)
            if settings is None:
                return True
            if notif_type in (
                Notification.Type.ASSIGNMENT_NEW,
                Notification.Type.ASSIGNMENT_DUE,
                Notification.Type.ASSIGNMENT_GRADED,
                Notification.Type.HOMEWORK_SUBMITTED,
            ):
                return settings.assignment_notifications
            if notif_type in (
                Notification.Type.MATERIAL_NEW,
                Notification.Type.MATERIAL_PUBLISHED,
            ):
                return settings.material_notifications
            if notif_type in (
                Notification.Type.PAYMENT_SUCCESS,
                Notification.Type.PAYMENT_FAILED,
                Notification.Type.PAYMENT_PROCESSED,
            ):
                return settings.payment_notifications
            if notif_type in (
                Notification.Type.INVOICE_SENT,
                Notification.Type.INVOICE_PAID,
                Notification.Type.INVOICE_OVERDUE,
                Notification.Type.INVOICE_VIEWED,
            ):
                return settings.invoice_notifications
            if notif_type == Notification.Type.REPORT_READY:
                return settings.report_notifications
            if notif_type == Notification.Type.MESSAGE_NEW:
                return settings.message_notifications
            return settings.system_notifications
        except Exception:
            return True

    def _ws_send(self, user_id: int, payload: Dict[str, Any]) -> None:
        if not self.channel_layer:
            return
        group_name = f"notifications_{user_id}"
        try:
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'notification',
                    'data': payload,
                },
            )
        except Exception as e:
            logger.error(f"WS send failed for user {user_id}: {e}")

    def _telegram_send(self, text: str) -> None:
        try:
            if not getattr(settings, 'TELEGRAM_BOT_TOKEN', None):
                return
            # Все системные уведомления — в лог-канал
            chat_id = getattr(settings, 'TELEGRAM_LOG_CHAT_ID', None)
            if not chat_id:
                return
            base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            }
            requests.post(base_url, data=data, timeout=5)
        except Exception as e:
            logger.warning(f"Telegram send skipped: {e}")

    def send(self,
             recipient: User,
             notif_type: str,
             title: str,
             message: str,
             priority: str = Notification.Priority.NORMAL,
             related_object_type: str = '',
             related_object_id: Optional[int] = None,
             data: Optional[Dict[str, Any]] = None) -> Notification:
        if not self._is_allowed_by_settings(recipient, notif_type):
            # Создаем запись низкого приоритета как пропущенную отправку
            notification = Notification.objects.create(
                recipient=recipient,
                type=notif_type,
                title=title,
                message=message,
                priority=priority,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                data=data or {},
                is_sent=False,
            )
            return notification

        notification = Notification.objects.create(
            recipient=recipient,
            type=notif_type,
            title=title,
            message=message,
            priority=priority,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            data=data or {},
            is_sent=True,
            sent_at=timezone.now(),
        )

        payload = {
            'id': notification.id,
            'type': notif_type,
            'title': title,
            'message': message,
            'priority': priority,
            'related_object_type': related_object_type,
            'related_object_id': related_object_id,
            'data': data or {},
            'created_at': notification.created_at.isoformat(),
        }
        self._ws_send(recipient.id, payload)

        # optional Telegram broadcast for critical events
        if getattr(settings, 'TELEGRAM_NOTIFICATIONS_ENABLED', False):
            try:
                self._telegram_send(f"🔔 <b>{title}</b>\n{message}")
            except Exception:
                pass
        return notification

    # Специализированные методы под Requirements 7.x
    def notify_student_created(self, tutor: User, student: User) -> Notification:
        title = "Ученик создан"
        message = f"Ученик {student.get_full_name() or student.username} успешно создан."
        return self.send(
            recipient=tutor,
            notif_type=Notification.Type.STUDENT_CREATED,
            title=title,
            message=message,
            data={'student_id': student.id},
        )

    def notify_subject_assigned(self, student: User, subject_id: int, teacher: User) -> Notification:
        title = "Назначен предмет"
        message = f"Вам назначен предмет. Преподаватель: {teacher.get_full_name() or teacher.username}."
        return self.send(
            recipient=student,
            notif_type=Notification.Type.SUBJECT_ASSIGNED,
            title=title,
            message=message,
            data={'subject_id': subject_id, 'teacher_id': teacher.id},
        )

    def notify_material_published(self, student: User, material_id: int, subject_id: int) -> Notification:
        title = "Новый материал"
        message = "Опубликован новый материал по вашему предмету."
        return self.send(
            recipient=student,
            notif_type=Notification.Type.MATERIAL_PUBLISHED,
            title=title,
            message=message,
            data={'material_id': material_id, 'subject_id': subject_id},
        )

    def notify_homework_submitted(self, teacher: User, submission_id: int, student: User) -> Notification:
        title = "Новое домашнее задание"
        message = f"Студент {student.get_full_name() or student.username} отправил домашнее задание."
        return self.send(
            recipient=teacher,
            notif_type=Notification.Type.HOMEWORK_SUBMITTED,
            title=title,
            message=message,
            data={'submission_id': submission_id, 'student_id': student.id},
        )

    def notify_payment_processed(self, parent: User, status: str, amount: str, enrollment_id: int) -> Notification:
        title = "Статус платежа обновлен"
        status_text = "успешно" if status == "success" else "не прошел"
        message = f"Платеж на сумму {amount} {status_text}."
        notif_type = Notification.Type.PAYMENT_SUCCESS if status == 'success' else Notification.Type.PAYMENT_FAILED
        return self.send(
            recipient=parent,
            notif_type=notif_type,
            title=title,
            message=message,
            data={'enrollment_id': enrollment_id, 'status': status, 'amount': amount},
        )

    # Invoice notification methods
    def notify_invoice_sent(self, invoice) -> Notification:
        """
        Уведомление родителю о выставленном счете
        """
        title = "Новый счет на оплату"
        message = (
            f"Тьютор {invoice.tutor.get_full_name()} выставил счет на {invoice.amount} руб. "
            f"Ученик: {invoice.student.get_full_name()}. "
            f"Срок оплаты: {invoice.due_date.strftime('%d.%m.%Y')}."
        )
        return self.send(
            recipient=invoice.parent,
            notif_type=Notification.Type.INVOICE_SENT,
            title=title,
            message=message,
            priority=Notification.Priority.HIGH,
            related_object_type='invoice',
            related_object_id=invoice.id,
            data={
                'invoice_id': invoice.id,
                'amount': str(invoice.amount),
                'due_date': invoice.due_date.isoformat(),
                'student_name': invoice.student.get_full_name(),
                'tutor_name': invoice.tutor.get_full_name(),
                'description': invoice.description[:200],  # Первые 200 символов
            }
        )

    def notify_invoice_paid(self, invoice) -> Notification:
        """
        Уведомление тьютору об оплате счета
        """
        title = "Счет оплачен"
        message = (
            f"Родитель {invoice.parent.get_full_name()} оплатил счет #{invoice.id} "
            f"на сумму {invoice.amount} руб. "
            f"Ученик: {invoice.student.get_full_name()}."
        )
        return self.send(
            recipient=invoice.tutor,
            notif_type=Notification.Type.INVOICE_PAID,
            title=title,
            message=message,
            priority=Notification.Priority.NORMAL,
            related_object_type='invoice',
            related_object_id=invoice.id,
            data={
                'invoice_id': invoice.id,
                'amount': str(invoice.amount),
                'paid_at': invoice.paid_at.isoformat() if invoice.paid_at else None,
                'student_name': invoice.student.get_full_name(),
                'parent_name': invoice.parent.get_full_name(),
            }
        )

    def notify_invoice_overdue(self, invoice) -> Notification:
        """
        Напоминание родителю о просроченном счете
        """
        title = "Просроченный счет"
        message = (
            f"Счет #{invoice.id} на сумму {invoice.amount} руб. просрочен. "
            f"Срок оплаты был: {invoice.due_date.strftime('%d.%m.%Y')}. "
            f"Ученик: {invoice.student.get_full_name()}."
        )
        return self.send(
            recipient=invoice.parent,
            notif_type=Notification.Type.INVOICE_OVERDUE,
            title=title,
            message=message,
            priority=Notification.Priority.URGENT,
            related_object_type='invoice',
            related_object_id=invoice.id,
            data={
                'invoice_id': invoice.id,
                'amount': str(invoice.amount),
                'due_date': invoice.due_date.isoformat(),
                'days_overdue': (timezone.now().date() - invoice.due_date).days,
                'student_name': invoice.student.get_full_name(),
            }
        )

    def notify_invoice_viewed(self, invoice) -> Notification:
        """
        Уведомление тьютору о просмотре счета родителем
        """
        title = "Счет просмотрен"
        message = (
            f"Родитель {invoice.parent.get_full_name()} просмотрел счет #{invoice.id} "
            f"на сумму {invoice.amount} руб."
        )
        return self.send(
            recipient=invoice.tutor,
            notif_type=Notification.Type.INVOICE_VIEWED,
            title=title,
            message=message,
            priority=Notification.Priority.LOW,
            related_object_type='invoice',
            related_object_id=invoice.id,
            data={
                'invoice_id': invoice.id,
                'amount': str(invoice.amount),
                'viewed_at': invoice.viewed_at.isoformat() if invoice.viewed_at else None,
                'parent_name': invoice.parent.get_full_name(),
            }
        )


