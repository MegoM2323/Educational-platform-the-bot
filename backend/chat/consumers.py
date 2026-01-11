import json
import logging
from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from chat.models import ChatRoom, Message, ChatParticipant
from chat.services.chat_service import ChatService

User = get_user_model()
logger = logging.getLogger("chat.websocket")


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer для real-time чатов.

    URL: ws://host/ws/chat/<room_id>/

    Events:
    - message_send: {"type": "message_send", "content": "text"}
    - message_delete: {"type": "message_delete", "message_id": 123}
    - message_edit: {"type": "message_edit", "message_id": 123, "content": "new text"}
    - typing: {"type": "typing", "is_typing": true}
    - read: {"type": "read"} - отметить как прочитанное
    """

    async def connect(self):
        """
        Подключение к WebSocket.

        Проверяет:
        1. Аутентификация пользователя
        2. Доступ к чату (can_access_chat)
        """
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope.get("user")

        logger.info(f"User {self.user.id} attempting to connect to chat {self.room_id}")

        if not self.user or not self.user.is_authenticated:
            logger.warning(f"Unauthenticated connection attempt to chat {self.room_id}")
            await self.close()
            return

        has_access = await self._check_access()
        if not has_access:
            logger.warning(f"User {self.user.id} denied access to chat {self.room_id}")
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        logger.info(f"User {self.user.id} connected to chat {self.room_id}")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user_id": self.user.id,
                "username": self.user.get_full_name() or self.user.username,
            },
        )

    async def disconnect(self, close_code):
        """Отключение от WebSocket"""
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_left",
                    "user_id": self.user.id,
                },
            )

            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        logger.info(f"User {self.user.id} disconnected from chat {self.room_id}")

    async def receive(self, text_data):
        """
        Получить сообщение от фронтенда.

        Формат: JSON
        {
            "type": "message_send" | "message_delete" | "message_edit" | "typing" | "read",
            "data": {...}
        }
        """
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from user {self.user.id}: {text_data}")
            await self.send_error("Invalid JSON format")
            return

        event_type = data.get("type")

        if event_type == "message_send":
            await self._handle_message_send(data.get("data", {}))
        elif event_type == "message_delete":
            await self._handle_message_delete(data.get("data", {}))
        elif event_type == "message_edit":
            await self._handle_message_edit(data.get("data", {}))
        elif event_type == "typing":
            await self._handle_typing(data.get("data", {}))
        elif event_type == "read":
            await self._handle_read()
        else:
            logger.warning(f"Unknown event type: {event_type}")
            await self.send_error(f"Unknown event type: {event_type}")

    async def _handle_message_send(self, data):
        """Обработка отправки сообщения"""
        content = data.get("content", "").strip()

        if not content:
            await self.send_error("Message content cannot be empty")
            return

        if len(content) > 10000:
            await self.send_error("Message is too long (max 10000 chars)")
            return

        message = await self._create_message(content)

        if not message:
            await self.send_error("Failed to create message")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": message["id"],
                "sender_id": message["sender_id"],
                "sender_name": message["sender_name"],
                "content": message["content"],
                "created_at": message["created_at"],
                "is_edited": False,
            },
        )

    async def _handle_message_delete(self, data):
        """Обработка удаления сообщения (soft delete)"""
        message_id = data.get("message_id")

        if not message_id:
            await self.send_error("message_id is required")
            return

        success = await self._delete_message(message_id)

        if not success:
            await self.send_error("Failed to delete message or access denied")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_deleted",
                "message_id": message_id,
            },
        )

    async def _handle_message_edit(self, data):
        """Обработка редактирования сообщения"""
        message_id = data.get("message_id")
        content = data.get("content", "").strip()

        if not message_id:
            await self.send_error("message_id is required")
            return

        if not content:
            await self.send_error("New content cannot be empty")
            return

        if len(content) > 10000:
            await self.send_error("Message is too long (max 10000 chars)")
            return

        message = await self._update_message(message_id, content)

        if not message:
            await self.send_error("Failed to edit message or access denied")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_edited",
                "message_id": message_id,
                "content": content,
                "edited_at": message.get("updated_at"),
            },
        )

    async def _handle_typing(self, data):
        """Обработка индикатора печати"""
        is_typing = data.get("is_typing", False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_typing",
                "user_id": self.user.id,
                "username": self.user.get_full_name() or self.user.username,
                "is_typing": is_typing,
            },
        )

    async def _handle_read(self):
        """Обработка отметить как прочитанное"""
        await self._mark_as_read()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "messages_read",
                "user_id": self.user.id,
            },
        )

    async def chat_message(self, event):
        """Broadcast нового сообщения"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_new",
                    "data": {
                        "message_id": event["message_id"],
                        "sender_id": event["sender_id"],
                        "sender_name": event["sender_name"],
                        "content": event["content"],
                        "created_at": event["created_at"],
                        "is_edited": event["is_edited"],
                    },
                }
            )
        )

    async def message_deleted(self, event):
        """Broadcast удаления сообщения"""
        await self.send(
            text_data=json.dumps(
                {"type": "message_deleted", "data": {"message_id": event["message_id"]}}
            )
        )

    async def message_edited(self, event):
        """Broadcast редактирования сообщения"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edited",
                    "data": {
                        "message_id": event["message_id"],
                        "content": event["content"],
                    },
                }
            )
        )

    async def user_typing(self, event):
        """Broadcast typing индикатора"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_typing",
                    "data": {
                        "user_id": event["user_id"],
                        "username": event["username"],
                        "is_typing": event["is_typing"],
                    },
                }
            )
        )

    async def user_joined(self, event):
        """Broadcast присоединения пользователя"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_joined",
                    "data": {
                        "user_id": event["user_id"],
                        "username": event["username"],
                    },
                }
            )
        )

    async def user_left(self, event):
        """Broadcast отключения пользователя"""
        await self.send(
            text_data=json.dumps(
                {"type": "user_left", "data": {"user_id": event["user_id"]}}
            )
        )

    async def messages_read(self, event):
        """Broadcast прочитанных сообщений"""
        await self.send(
            text_data=json.dumps(
                {"type": "messages_read", "data": {"user_id": event["user_id"]}}
            )
        )

    @database_sync_to_async
    def _check_access(self):
        """Проверить доступ к чату"""
        try:
            chat = ChatRoom.objects.get(id=self.room_id, is_active=True)
            return ChatService.can_access_chat(self.user, chat)
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def _create_message(self, content):
        """Создать сообщение в БД"""
        try:
            chat = ChatRoom.objects.get(id=self.room_id, is_active=True)
            message = ChatService.create_message(
                self.user, chat, content, message_type="text"
            )
            return {
                "id": message.id,
                "sender_id": message.sender_id,
                "sender_name": message.sender.get_full_name()
                or message.sender.username,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            return None

    @database_sync_to_async
    def _delete_message(self, message_id):
        """Удалить сообщение (soft delete)"""
        try:
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            if message.sender_id != self.user.id and not self.user.is_staff:
                return False
            ChatService.delete_message(self.user, message)
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            return False

    @database_sync_to_async
    def _update_message(self, message_id, content):
        """Обновить сообщение"""
        try:
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            if message.sender_id != self.user.id:
                return None
            message.content = content
            message = ChatService.update_message(self.user, message)
            return {
                "id": message.id,
                "content": message.content,
                "updated_at": message.updated_at.isoformat(),
            }
        except Message.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Failed to update message: {e}")
            return None

    @database_sync_to_async
    def _mark_as_read(self):
        """Отметить сообщения как прочитанные"""
        try:
            chat = ChatRoom.objects.get(id=self.room_id, is_active=True)
            ChatService.mark_messages_as_read(self.user, chat)
            return True
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False

    async def send_error(self, error_message):
        """Отправить error сообщение фронтенду"""
        await self.send(
            text_data=json.dumps({"type": "error", "data": {"message": error_message}})
        )
