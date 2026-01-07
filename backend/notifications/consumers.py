import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для доставки уведомлений в реальном времени

    Подключение: ws://localhost:8000/ws/notifications/

    События:
    - user_notification: Отправляет уведомление пользователю
    - notification_read: Отмечает уведомление как прочитанное
    - notification_deleted: Отмечает уведомление как удаленное
    """

    async def connect(self):
        """Подключение к WebSocket каналу уведомлений"""
        self.user_group_name = None

        try:
            self.user = self.scope["user"]

            logger.info(
                f"[NotificationConsumer] Connection attempt: "
                f"user={self.user}, authenticated={self.user.is_authenticated}"
            )

            # Проверяем, что пользователь аутентифицирован
            if not self.user.is_authenticated:
                logger.warning(
                    f"[NotificationConsumer] Connection rejected: user not authenticated"
                )
                await self.close()
                return

            # Группа пользователя для отправки уведомлений
            self.user_group_name = f"notifications_user_{self.user.id}"

            # Присоединяемся к группе
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)

            logger.info(
                f"[NotificationConsumer] User connected: "
                f"user_id={self.user.id}, group={self.user_group_name}"
            )

            await self.accept()

            # Отправляем непрочитанные уведомления при подключении
            await self.send_unread_notifications()

        except Exception as e:
            logger.error(
                f"[NotificationConsumer] Error during connection: {str(e)}",
                exc_info=True,
            )
            try:
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": f"Connection failed: {str(e)}"}
                    )
                )
            except Exception:
                pass
            try:
                await self.close(code=1011)
            except Exception:
                pass

    async def disconnect(self, close_code):
        """Отключение от WebSocket канала"""
        user_group_name = getattr(self, "user_group_name", None)
        if user_group_name:
            await self.channel_layer.group_discard(user_group_name, self.channel_name)

        user = getattr(self, "user", None)
        if user:
            logger.info(
                f"[NotificationConsumer] User disconnected: "
                f"user_id={user.id}, close_code={close_code}"
            )
        else:
            logger.info(
                f"[NotificationConsumer] Connection disconnected before user set: "
                f"close_code={close_code}"
            )

    async def receive(self, text_data):
        """
        Получение сообщения от клиента

        Поддерживаемые действия:
        - mark_as_read: Отметить уведомление как прочитанное
        - delete: Удалить уведомление
        - archive: Архивировать уведомление
        """
        try:
            data = json.loads(text_data)
            action = data.get("action")
            notification_id = data.get("notification_id")

            logger.info(
                f"[NotificationConsumer] Received message: "
                f"user_id={self.user.id}, action={action}, notification_id={notification_id}"
            )

            if action == "mark_as_read":
                await self.mark_notification_read(notification_id)
            elif action == "delete":
                await self.delete_notification(notification_id)
            elif action == "archive":
                await self.archive_notification(notification_id)
            else:
                await self.send(
                    text_data=json.dumps(
                        {"type": "error", "message": f"Unknown action: {action}"}
                    )
                )

        except json.JSONDecodeError:
            logger.error(f"[NotificationConsumer] Invalid JSON: user_id={self.user.id}")
            await self.send(
                text_data=json.dumps({"type": "error", "message": "Invalid JSON"})
            )
        except Exception as e:
            logger.error(f"[NotificationConsumer] Error processing message: {str(e)}")
            await self.send(
                text_data=json.dumps({"type": "error", "message": f"Error: {str(e)}"})
            )

    async def user_notification(self, event):
        """
        Обработчик события user_notification
        Отправляет новое уведомление пользователю
        """
        notification = event.get("notification")

        logger.info(
            f"[NotificationConsumer] Sending notification: "
            f'user_id={self.user.id}, notification_id={notification.get("id")}'
        )

        await self.send(
            text_data=json.dumps({"type": "notification", "notification": notification})
        )

    async def notification_read(self, event):
        """
        Обработчик события notification_read
        Подтверждает прочтение уведомления
        """
        notification_id = event.get("notification_id")

        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification_read",
                    "notification_id": notification_id,
                    "message": "Notification marked as read",
                }
            )
        )

    async def notification_deleted(self, event):
        """
        Обработчик события notification_deleted
        Уведомляет об удалении
        """
        notification_id = event.get("notification_id")

        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification_deleted",
                    "notification_id": notification_id,
                    "message": "Notification deleted",
                }
            )
        )

    async def send_unread_notifications(self):
        """
        Отправляет все непрочитанные уведомления при подключении
        """
        try:
            unread_notifications = await self.get_unread_notifications()

            for notification in unread_notifications:
                serializer = NotificationSerializer(notification)
                await self.send(
                    text_data=json.dumps(
                        {"type": "notification", "notification": serializer.data}
                    )
                )

            logger.info(
                f"[NotificationConsumer] Sent {len(unread_notifications)} "
                f"unread notifications to user_id={self.user.id}"
            )
        except Exception as e:
            logger.error(
                f"[NotificationConsumer] Error sending unread notifications: {str(e)}",
                exc_info=True,
            )
            try:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "message": f"Failed to load notifications: {str(e)}",
                        }
                    )
                )
            except Exception:
                pass

    @database_sync_to_async
    def get_unread_notifications(self):
        """Получение непрочитанных уведомлений"""
        return list(
            Notification.objects.filter(
                recipient=self.user, is_read=False, is_archived=False
            ).order_by("-created_at")[
                :50
            ]  # Лимит 50 для производительности
        )

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Отметить уведомление как прочитанное"""
        try:
            notification = Notification.objects.get(
                id=notification_id, recipient=self.user
            )
            notification.mark_as_read()

            logger.info(
                f"[NotificationConsumer] Marked as read: "
                f"notification_id={notification_id}, user_id={self.user.id}"
            )

            return True
        except Notification.DoesNotExist:
            logger.warning(
                f"[NotificationConsumer] Notification not found: "
                f"notification_id={notification_id}, user_id={self.user.id}"
            )
            return False

    @database_sync_to_async
    def delete_notification(self, notification_id):
        """Удалить уведомление"""
        try:
            notification = Notification.objects.get(
                id=notification_id, recipient=self.user
            )
            notification.delete()

            logger.info(
                f"[NotificationConsumer] Deleted: "
                f"notification_id={notification_id}, user_id={self.user.id}"
            )

            return True
        except Notification.DoesNotExist:
            logger.warning(
                f"[NotificationConsumer] Notification not found for delete: "
                f"notification_id={notification_id}, user_id={self.user.id}"
            )
            return False

    @database_sync_to_async
    def archive_notification(self, notification_id):
        """Архивировать уведомление"""
        try:
            notification = Notification.objects.get(
                id=notification_id, recipient=self.user
            )
            notification.is_archived = True
            notification.archived_at = timezone.now()
            notification.save()

            logger.info(
                f"[NotificationConsumer] Archived: "
                f"notification_id={notification_id}, user_id={self.user.id}"
            )

            return True
        except Notification.DoesNotExist:
            logger.warning(
                f"[NotificationConsumer] Notification not found for archive: "
                f"notification_id={notification_id}, user_id={self.user.id}"
            )
            return False
