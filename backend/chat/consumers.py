import json
import logging
import asyncio
import time
from collections import deque
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.tokens import AccessToken

from .models import ChatRoom, Message, ChatParticipant
from .services.chat_service import ChatService
from .services.message_service import MessageService

User = get_user_model()
logger = logging.getLogger(__name__)

CHAT_RATE_LIMIT = 10
CHAT_RATE_WINDOW = 60
CHAT_ROOMS_LIMIT = 5


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для real-time чатов"""

    async def connect(self):
        """При подключении WebSocket"""
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = None
        self.authenticated = False

        await self.accept()

        try:
            await asyncio.wait_for(self._wait_for_auth(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"[ChatConsumer] Auth timeout for room {self.room_id}")
            await self.close(code=4001)

    async def receive(self, text_data):
        """При получении сообщения от клиента"""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("INVALID_REQUEST", "Invalid JSON")
            return

        message_type = data.get("type")

        if message_type == "auth":
            await self._handle_auth(data)
        elif not self.authenticated:
            await self._send_error("UNAUTHORIZED", "Not authenticated")
        elif message_type == "message":
            await self._handle_message(data)
        elif message_type == "typing":
            await self._handle_typing()
        elif message_type == "read":
            await self._handle_read()

    async def disconnect(self, close_code):
        """При отключении WebSocket"""
        if self.authenticated:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def _wait_for_auth(self):
        """Ждать auth сообщение (используется в connect с timeout)"""
        while not self.authenticated:
            await asyncio.sleep(0.1)

    async def _handle_auth(self, data):
        """Обработать аутентификацию"""
        token = data.get("token")
        if not token:
            await self.close(code=4001)
            return

        user = await self._validate_token(token)
        if not user:
            await self.close(code=4001)
            return

        has_access = await self._check_access(user)
        if not has_access:
            await self.close(code=4003)
            return

        if not await self._check_room_limit(user):
            logger.warning(
                f"[ChatConsumer] Room limit exceeded for user {user.id} (room {self.room_id})"
            )
            await self.close(code=4029)
            return

        self.user = user
        self.authenticated = True

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.send(text_data=json.dumps({"type": "auth_success", "user_id": user.id}))

    async def _handle_message(self, data):
        """Обработать отправку сообщения"""
        content = data.get("content", "").strip()
        if not content:
            await self._send_error("EMPTY_MESSAGE", "Message cannot be empty")
            return

        if not await self._check_message_rate_limit(self.user):
            await self._send_error(
                "RATE_LIMIT_EXCEEDED",
                f"Too many messages. Max {CHAT_RATE_LIMIT} per minute.",
            )
            return

        try:
            message = await self._save_message(content)
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            await self._send_error("ERROR", str(e))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": message},
        )

    async def _handle_typing(self):
        """Обработать индикатор печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_typing",
                "user_id": self.user.id,
                "exclude_user": self.user.id,
            },
        )

    async def _handle_read(self):
        """Обработать отметку чата как прочитанного"""
        await self._mark_as_read()

    async def chat_message(self, event):
        """Broadcast сообщения клиентам"""
        await self.send(text_data=json.dumps({"type": "message", "message": event["message"]}))

    async def chat_typing(self, event):
        """Broadcast typing индикатора"""
        if event.get("user_id") == self.user.id:
            return

        user_data = await self._get_user_data(event["user_id"])
        await self.send(text_data=json.dumps({"type": "typing", "user": user_data}))

    async def chat_message_edited(self, event):
        """Broadcast редактирования сообщения"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edited",
                    "message_id": event["message_id"],
                    "content": event["content"],
                    "updated_at": event["updated_at"],
                }
            )
        )

    async def chat_message_deleted(self, event):
        """Broadcast удаления сообщения"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_deleted",
                    "message_id": event["message_id"],
                }
            )
        )

    async def _send_error(self, code, message):
        """Отправить ошибку клиенту"""
        await self.send(text_data=json.dumps({"type": "error", "code": code, "message": message}))

    async def _check_message_rate_limit(self, user):
        """Проверить rate limit на сообщения (Redis-based, per-user)"""
        rate_key = f"chat_rate_limit:{user.id}"
        current_count = cache.get(rate_key, 0)

        if current_count >= CHAT_RATE_LIMIT:
            return False

        cache.set(rate_key, current_count + 1, CHAT_RATE_WINDOW)
        return True

    async def _check_room_limit(self, user):
        """Проверить лимит на количество разных чатов в минуту (Redis-based)"""
        rooms_key = f"chat_rooms_limit:{user.id}"
        current_count = cache.get(rooms_key, 0)

        if current_count >= CHAT_ROOMS_LIMIT:
            return False

        cache.set(rooms_key, current_count + 1, CHAT_RATE_WINDOW)
        return True

    @database_sync_to_async
    def _validate_token(self, token):
        """Проверить JWT токен"""
        try:
            decoded = AccessToken(token)
            user_id = decoded["user_id"]
            return User.objects.get(id=user_id, is_active=True)
        except Exception:
            return None

    @database_sync_to_async
    def _check_access(self, user):
        """Проверить доступ к комнате"""
        try:
            if not user.is_active:
                return False

            room = ChatRoom.objects.get(id=self.room_id)
            service = ChatService()
            return service.can_access_chat(user, room)
        except Exception:
            return False

    @database_sync_to_async
    def _save_message(self, content):
        """Сохранить сообщение и вернуть данные для broadcast"""
        room = ChatRoom.objects.get(id=self.room_id)
        service = MessageService()
        message = service.send_message(self.user, room, content)

        return {
            "id": message.id,
            "sender": {
                "id": self.user.id,
                "full_name": f"{self.user.first_name} {self.user.last_name}".strip(),
                "role": getattr(self.user, "role", "unknown"),
            },
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }

    @database_sync_to_async
    def _mark_as_read(self):
        """Отметить чат как прочитанный"""
        room = ChatRoom.objects.get(id=self.room_id)
        service = ChatService()
        service.mark_chat_as_read(self.user, room)

    @database_sync_to_async
    def _get_user_data(self, user_id):
        """Получить данные пользователя"""
        user = User.objects.get(id=user_id)
        return {
            "id": user.id,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
        }
