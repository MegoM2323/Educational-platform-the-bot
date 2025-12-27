"""
In-App Notification Service

Сервис для создания и доставки уведомлений через WebSocket в реальном времени.
Поддерживает управление уведомлениями (прочтение, удаление, архивирование).
"""

import logging
from typing import Dict, List, Optional, Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification, NotificationSettings
from .serializers import NotificationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class InAppNotificationService:
    """
    Сервис управления in-app уведомлениями с доставкой через WebSocket
    """

    @staticmethod
    def create_notification(
        recipient: User,
        title: str,
        message: str,
        notification_type: str = Notification.Type.SYSTEM,
        priority: str = Notification.Priority.NORMAL,
        related_object_type: str = '',
        related_object_id: Optional[int] = None,
        data: Optional[Dict] = None,
        delivery_method: str = 'websocket'
    ) -> Optional[Notification]:
        """
        Создать в-приложение уведомление с опциональной доставкой через WebSocket

        Args:
            recipient: Получатель уведомления
            title: Заголовок уведомления
            message: Текст уведомления
            notification_type: Тип уведомления (по умолчанию SYSTEM)
            priority: Приоритет (low, normal, high, urgent)
            related_object_type: Тип связанного объекта (опционально)
            related_object_id: ID связанного объекта (опционально)
            data: Дополнительные данные в формате JSON
            delivery_method: Метод доставки ('websocket' или 'queue')

        Returns:
            Созданный объект Notification или None в случае ошибки
        """
        try:
            # Проверяем настройки пользователя
            if not InAppNotificationService._should_send_notification(
                recipient, notification_type
            ):
                logger.info(
                    f'Notification blocked by user settings: '
                    f'recipient={recipient.id}, type={notification_type}'
                )
                return None

            # Создаем уведомление
            notification = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                type=notification_type,
                priority=priority,
                related_object_type=related_object_type,
                related_object_id=related_object_id,
                data=data or {},
                is_sent=True,
                sent_at=timezone.now()
            )

            logger.info(
                f'Notification created: notification_id={notification.id}, '
                f'recipient={recipient.id}, type={notification_type}'
            )

            # Отправляем через WebSocket в реальном времени
            if delivery_method == 'websocket':
                InAppNotificationService._send_via_websocket(notification)

            return notification

        except Exception as e:
            logger.error(
                f'Error creating notification for recipient={recipient.id}: {str(e)}'
            )
            return None

    @staticmethod
    def create_bulk_notifications(
        recipients: List[User],
        title: str,
        message: str,
        notification_type: str = Notification.Type.SYSTEM,
        priority: str = Notification.Priority.NORMAL,
        related_object_type: str = '',
        related_object_id: Optional[int] = None,
        data: Optional[Dict] = None
    ) -> List[int]:
        """
        Создать уведомления для нескольких пользователей

        Args:
            recipients: Список получателей
            title: Заголовок уведомления
            message: Текст уведомления
            notification_type: Тип уведомления
            priority: Приоритет
            related_object_type: Тип связанного объекта
            related_object_id: ID связанного объекта
            data: Дополнительные данные

        Returns:
            Список ID созданных уведомлений
        """
        try:
            notifications = []
            notification_ids = []

            for recipient in recipients:
                try:
                    # Проверяем настройки
                    if not InAppNotificationService._should_send_notification(
                        recipient, notification_type
                    ):
                        continue

                    notification = Notification.objects.create(
                        recipient=recipient,
                        title=title,
                        message=message,
                        type=notification_type,
                        priority=priority,
                        related_object_type=related_object_type,
                        related_object_id=related_object_id,
                        data=data or {},
                        is_sent=True,
                        sent_at=timezone.now()
                    )

                    notifications.append(notification)
                    notification_ids.append(notification.id)

                except Exception as e:
                    logger.error(
                        f'Error creating notification for recipient={recipient.id}: {str(e)}'
                    )

            # Отправляем все через WebSocket
            for notification in notifications:
                InAppNotificationService._send_via_websocket(notification)

            logger.info(
                f'Bulk notifications created: count={len(notifications)}, '
                f'type={notification_type}'
            )

            return notification_ids

        except Exception as e:
            logger.error(f'Error in create_bulk_notifications: {str(e)}')
            return []

    @staticmethod
    def mark_as_read(notification_id: int, user: User) -> bool:
        """
        Отметить уведомление как прочитанное

        Args:
            notification_id: ID уведомления
            user: Пользователь, отмечающий уведомление

        Returns:
            True если успешно, False иначе
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.mark_as_read()

            logger.info(
                f'Notification marked as read: '
                f'notification_id={notification_id}, user={user.id}'
            )

            return True

        except Notification.DoesNotExist:
            logger.warning(
                f'Notification not found: notification_id={notification_id}, user={user.id}'
            )
            return False
        except Exception as e:
            logger.error(f'Error marking notification as read: {str(e)}')
            return False

    @staticmethod
    def mark_multiple_as_read(notification_ids: List[int], user: User) -> int:
        """
        Отметить несколько уведомлений как прочитанные

        Args:
            notification_ids: Список ID уведомлений
            user: Пользователь

        Returns:
            Количество обновленных уведомлений
        """
        try:
            updated_count = Notification.objects.filter(
                id__in=notification_ids,
                recipient=user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())

            logger.info(
                f'Multiple notifications marked as read: '
                f'count={updated_count}, user={user.id}'
            )

            return updated_count

        except Exception as e:
            logger.error(f'Error marking multiple notifications as read: {str(e)}')
            return 0

    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """
        Отметить все уведомления пользователя как прочитанные

        Args:
            user: Пользователь

        Returns:
            Количество обновленных уведомлений
        """
        try:
            updated_count = Notification.objects.filter(
                recipient=user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())

            logger.info(
                f'All notifications marked as read for user={user.id}, count={updated_count}'
            )

            return updated_count

        except Exception as e:
            logger.error(f'Error marking all notifications as read: {str(e)}')
            return 0

    @staticmethod
    def delete_notification(notification_id: int, user: User) -> bool:
        """
        Удалить уведомление

        Args:
            notification_id: ID уведомления
            user: Пользователь

        Returns:
            True если успешно, False иначе
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.delete()

            logger.info(
                f'Notification deleted: '
                f'notification_id={notification_id}, user={user.id}'
            )

            return True

        except Notification.DoesNotExist:
            logger.warning(
                f'Notification not found for deletion: '
                f'notification_id={notification_id}, user={user.id}'
            )
            return False
        except Exception as e:
            logger.error(f'Error deleting notification: {str(e)}')
            return False

    @staticmethod
    def archive_notification(notification_id: int, user: User) -> bool:
        """
        Архивировать уведомление

        Args:
            notification_id: ID уведомления
            user: Пользователь

        Returns:
            True если успешно, False иначе
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.is_archived = True
            notification.archived_at = timezone.now()
            notification.save()

            logger.info(
                f'Notification archived: '
                f'notification_id={notification_id}, user={user.id}'
            )

            return True

        except Notification.DoesNotExist:
            logger.warning(
                f'Notification not found for archiving: '
                f'notification_id={notification_id}, user={user.id}'
            )
            return False
        except Exception as e:
            logger.error(f'Error archiving notification: {str(e)}')
            return False

    @staticmethod
    def unarchive_notification(notification_id: int, user: User) -> bool:
        """
        Восстановить архивированное уведомление

        Args:
            notification_id: ID уведомления
            user: Пользователь

        Returns:
            True если успешно, False иначе
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.is_archived = False
            notification.archived_at = None
            notification.save()

            logger.info(
                f'Notification unarchived: '
                f'notification_id={notification_id}, user={user.id}'
            )

            return True

        except Notification.DoesNotExist:
            logger.warning(
                f'Notification not found for unarchiving: '
                f'notification_id={notification_id}, user={user.id}'
            )
            return False
        except Exception as e:
            logger.error(f'Error unarchiving notification: {str(e)}')
            return False

    @staticmethod
    def get_unread_count(user: User) -> int:
        """
        Получить количество непрочитанных уведомлений

        Args:
            user: Пользователь

        Returns:
            Количество непрочитанных уведомлений
        """
        try:
            return Notification.objects.filter(
                recipient=user,
                is_read=False,
                is_archived=False
            ).count()
        except Exception as e:
            logger.error(f'Error getting unread count: {str(e)}')
            return 0

    @staticmethod
    def get_notifications(
        user: User,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """
        Получить уведомления пользователя

        Args:
            user: Пользователь
            include_archived: Включать архивированные уведомления
            limit: Лимит уведомлений
            offset: Смещение для пагинации

        Returns:
            Список уведомлений
        """
        try:
            queryset = Notification.objects.filter(recipient=user)

            if not include_archived:
                queryset = queryset.filter(is_archived=False)

            return list(
                queryset.order_by('-created_at')[offset:offset + limit]
            )
        except Exception as e:
            logger.error(f'Error getting notifications: {str(e)}')
            return []

    @staticmethod
    def _should_send_notification(
        user: User,
        notification_type: str
    ) -> bool:
        """
        Проверить, должно ли отправляться уведомление согласно настройкам пользователя

        Args:
            user: Пользователь
            notification_type: Тип уведомления

        Returns:
            True если уведомление должно быть отправлено
        """
        try:
            # Получаем или создаем настройки пользователя
            settings, _ = NotificationSettings.objects.get_or_create(user=user)

            # Проверяем общие настройки in-app уведомлений
            # (в приложении уведомления всегда включены)

            # Проверяем настройки по типам
            if notification_type == Notification.Type.ASSIGNMENT_NEW:
                return settings.assignment_notifications
            elif notification_type == Notification.Type.ASSIGNMENT_DUE:
                return settings.assignment_notifications
            elif notification_type == Notification.Type.ASSIGNMENT_GRADED:
                return settings.assignment_notifications
            elif notification_type == Notification.Type.MATERIAL_NEW:
                return settings.material_notifications
            elif notification_type == Notification.Type.MESSAGE_NEW:
                return settings.message_notifications
            elif notification_type == Notification.Type.REPORT_READY:
                return settings.report_notifications
            elif notification_type == Notification.Type.PAYMENT_SUCCESS:
                return settings.payment_notifications
            elif notification_type == Notification.Type.PAYMENT_FAILED:
                return settings.payment_notifications
            elif notification_type == Notification.Type.PAYMENT_PROCESSED:
                return settings.payment_notifications
            elif notification_type == Notification.Type.INVOICE_SENT:
                return settings.invoice_notifications
            elif notification_type == Notification.Type.INVOICE_PAID:
                return settings.invoice_notifications
            elif notification_type == Notification.Type.INVOICE_OVERDUE:
                return settings.invoice_notifications
            elif notification_type == Notification.Type.INVOICE_VIEWED:
                return settings.invoice_notifications

            # Системные уведомления проверяют системные настройки
            return settings.system_notifications

        except Exception as e:
            logger.error(f'Error checking notification settings: {str(e)}')
            # По умолчанию отправляем, если не удается проверить
            return True

    @staticmethod
    def _send_via_websocket(notification: Notification) -> None:
        """
        Отправить уведомление через WebSocket в реальном времени

        Args:
            notification: Уведомление для отправки
        """
        try:
            channel_layer = get_channel_layer()
            user_group_name = f'notifications_user_{notification.recipient.id}'

            # Сериализуем уведомление
            serializer = NotificationSerializer(notification)

            # Отправляем асинхронно через channel layer
            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {
                    'type': 'user_notification',
                    'notification': serializer.data
                }
            )

            logger.info(
                f'Notification sent via WebSocket: '
                f'notification_id={notification.id}, '
                f'recipient={notification.recipient.id}'
            )

        except Exception as e:
            logger.error(
                f'Error sending notification via WebSocket: {str(e)}'
            )
