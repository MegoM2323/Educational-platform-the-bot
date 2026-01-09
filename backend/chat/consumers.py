import json
import logging
import asyncio
import time
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken

from .models import ChatRoom, Message
from .services.chat_service import ChatService
from .services.message_service import MessageService
from .signals import register_consumer, unregister_consumer
from config.throttling import ChatMessageThrottle, ChatRoomThrottle

User = get_user_model()
logger = logging.getLogger("chat.websocket")


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для real-time чатов"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache settings values at initialization to avoid repeated lookups
        self.heartbeat_interval = settings.WEBSOCKET_CONFIG["HEARTBEAT_INTERVAL"]
        self.heartbeat_timeout = settings.WEBSOCKET_CONFIG["HEARTBEAT_TIMEOUT"]
        self.auth_timeout = settings.WEBSOCKET_CONFIG["AUTH_TIMEOUT"]
        self.message_size_limit = settings.WEBSOCKET_CONFIG["MESSAGE_SIZE_LIMIT"]

    async def connect(self):
        """При подключении WebSocket"""
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = None
        self.authenticated = False
        self.heartbeat_task = None
        self.last_pong_time = time.time()

        logger.info(f"WebSocket connect attempt: room_id={self.room_id}, user=anonymous")
        await self.accept()

        register_consumer(self)

        try:
            await asyncio.wait_for(self._wait_for_auth(), timeout=float(self.auth_timeout))
        except asyncio.TimeoutError:
            logger.warning(f"Auth timeout: room_id={self.room_id}, timeout={self.auth_timeout}s")
            await self.close(code=4001)

    async def graceful_shutdown(self):
        """Gracefully shutdown WebSocket connection before server shutdown"""
        user_id = self.user.id if self.user else "unknown"

        try:
            logger.info(f"Graceful shutdown initiated: user_id={user_id}, room_id={self.room_id}")

            await self.send(
                text_data=json.dumps(
                    {
                        "type": "server_shutdown",
                        "message": "Server is shutting down, please refresh page",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

            await asyncio.sleep(0.5)

            if self.user and self.room_id:
                logger.info(f"Graceful shutdown: user_id={user_id}, room_id={self.room_id}")

            await self.close(code=1001, reason="Server shutdown")

        except Exception as e:
            logger.error(
                f"Error during graceful shutdown: user_id={user_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def receive(self, text_data):
        """При получении сообщения от клиента"""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning(
                f"Invalid JSON received: room_id={self.room_id}, user_id={self.user.id if self.user else 'unknown'}"
            )
            await self._send_error("INVALID_REQUEST", "Invalid JSON")
            return

        message_type = data.get("type")
        user_id = self.user.id if self.user else "unknown"
        logger.debug(
            f"WebSocket message received: type={message_type}, room_id={self.room_id}, user_id={user_id}"
        )

        if message_type == "pong":
            await self.handle_pong(data)
            return

        if message_type == "auth":
            await self._handle_auth(data)
        elif not self.authenticated:
            logger.warning(
                f"Unauthenticated message: type={message_type}, room_id={self.room_id}, user_id={user_id}"
            )
            await self._send_error("UNAUTHORIZED", "Not authenticated")
        elif message_type == "message":
            await self._handle_message(data)
        elif message_type == "typing":
            await self._handle_typing()
        elif message_type == "read":
            await self._handle_read()

    async def disconnect(self, close_code):
        """При отключении WebSocket"""
        user_id = self.user.id if self.user else "unknown"

        if close_code == 1001:
            logger.info(
                f"Server shutdown disconnect: user_id={user_id}, room_id={self.room_id}, code={close_code}"
            )
        elif close_code == 1000:
            logger.info(
                f"Normal disconnect: user_id={user_id}, room_id={self.room_id}, code={close_code}"
            )
        else:
            logger.warning(
                f"Unexpected disconnect: user_id={user_id}, room_id={self.room_id}, code={close_code}"
            )

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                logger.debug(f"Heartbeat task cancelled: user_id={user_id}")

        if self.authenticated:
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                logger.debug(
                    f"WebSocket disconnected: user_id={user_id}, room_id={self.room_id}, code={close_code}"
                )
            except Exception as e:
                logger.error(
                    f"Error in disconnect cleanup: user_id={user_id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                    exc_info=True,
                )

        unregister_consumer(self)

    async def _wait_for_auth(self):
        """Ждать auth сообщение (используется в connect с timeout)"""
        while not self.authenticated:
            await asyncio.sleep(0.1)

    async def _handle_auth(self, data):
        """Обработать аутентификацию"""
        logger.info(f"Auth started: room_id={self.room_id}")

        token = data.get("token")
        if not token:
            logger.warning(f"Auth failed: missing token, room_id={self.room_id}")
            await self.close(code=4001)
            return

        user = await self._validate_token(token)
        if not user:
            logger.warning(f"Auth failed: invalid token, room_id={self.room_id}")
            await self.close(code=4001)
            return

        has_access = await self._check_access(user)
        if not has_access:
            logger.warning(
                f"Auth failed: permission denied, user_id={user.id}, room_id={self.room_id}"
            )
            await self.close(code=4003)
            return

        if not await self._check_room_limit(user):
            logger.warning(f"Room limit exceeded: user_id={user.id}, room_id={self.room_id}")
            await self.close(code=4029)
            return

        self.user = user
        self.authenticated = True

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        logger.info(f"Auth successful: user_id={user.id}, room_id={self.room_id}")

        await self.send(text_data=json.dumps({"type": "auth_success", "user_id": user.id}))

        await self.start_heartbeat()

    async def _handle_message(self, data):
        """Обработать отправку сообщения с валидацией через DRF Serializer"""

        if not self.user.is_active:
            logger.warning(
                f"Permission denied: inactive user, user_id={self.user.id}, room_id={self.room_id}"
            )
            await self._send_error("UNAUTHORIZED", "User is inactive")
            return

        has_permission = await self._check_current_permissions(self.user)
        if not has_permission:
            logger.warning(
                f"Permission denied: no access to chat, user_id={self.user.id}, room_id={self.room_id}"
            )
            await self._send_error(
                "PERMISSION_DENIED", "You no longer have permission to access this chat"
            )
            await self.close(code=4003)
            return

        if not await self._check_message_rate_limit(self.user):
            logger.warning(f"Rate limit exceeded: user_id={self.user.id}, scope=chat_message")
            await self._send_error(
                "RATE_LIMIT_EXCEEDED",
                "Rate limit exceeded. Please wait before sending more messages.",
                retry_after=60,
            )
            return

        message_data = {
            "content": data.get("content", "").strip(),
        }

        from .serializers import MessageCreateSerializer

        serializer = MessageCreateSerializer(data=message_data)

        if not serializer.is_valid():
            logger.warning(
                f"Message validation failed: user_id={self.user.id}, room_id={self.room_id}, errors={serializer.errors}"
            )
            await self._send_error(4000, "Invalid message format", errors=serializer.errors)
            return

        validated_data = serializer.validated_data
        content = validated_data["content"]

        logger.debug(
            f"Message validation passed: user_id={self.user.id}, room_id={self.room_id}, content_length={len(content)}"
        )

        try:
            message = await self._save_message(content)
            logger.info(
                f"Message saved: message_id={message['id']}, user_id={self.user.id}, room_id={self.room_id}, content_length={len(content)}"
            )
        except Exception as e:
            logger.error(
                f"Error saving message: user_id={self.user.id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            await self._send_error("ERROR", str(e))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": message},
        )

    async def _handle_typing(self):
        """Обработать индикатор печати"""
        logger.debug(f"Typing indicator sent: user_id={self.user.id}, room_id={self.room_id}")

        if not self.user.is_active:
            logger.warning(
                f"Typing from inactive user: user_id={self.user.id}, room_id={self.room_id}"
            )
            await self._send_error("UNAUTHORIZED", "User is inactive")
            await self.close(code=4003)
            return

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
        logger.debug(f"Chat marked as read: user_id={self.user.id}, room_id={self.room_id}")

        if not self.user.is_active:
            logger.warning(
                f"Read mark from inactive user: user_id={self.user.id}, room_id={self.room_id}"
            )
            await self._send_error("UNAUTHORIZED", "User is inactive")
            await self.close(code=4003)
            return

        try:
            await self._mark_as_read()
            logger.info(f"Chat marked as read: user_id={self.user.id}, room_id={self.room_id}")
        except Exception as e:
            logger.error(
                f"Error marking chat as read: user_id={self.user.id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def chat_message(self, event):
        """Broadcast сообщения клиентам"""
        try:
            await self.send(text_data=json.dumps({"type": "message", "message": event["message"]}))
        except Exception as e:
            logger.error(
                f"Error broadcasting message: user_id={self.user.id if self.user else 'unknown'}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def chat_typing(self, event):
        """Broadcast typing индикатора"""
        if event.get("user_id") == self.user.id:
            return

        try:
            user_data = await self._get_user_data(event["user_id"])
            await self.send(text_data=json.dumps({"type": "typing", "user": user_data}))
        except Exception as e:
            logger.error(
                f"Error broadcasting typing: user_id={self.user.id}, room_id={self.room_id}, typing_user_id={event.get('user_id')}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def chat_message_edited(self, event):
        """Broadcast редактирования сообщения"""
        try:
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
        except Exception as e:
            logger.error(
                f"Error broadcasting message edit: user_id={self.user.id if self.user else 'unknown'}, room_id={self.room_id}, message_id={event.get('message_id')}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def chat_message_deleted(self, event):
        """Broadcast удаления сообщения"""
        try:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "message_deleted",
                        "message_id": event["message_id"],
                    }
                )
            )
        except Exception as e:
            logger.error(
                f"Error broadcasting message deletion: user_id={self.user.id if self.user else 'unknown'}, room_id={self.room_id}, message_id={event.get('message_id')}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def start_heartbeat(self):
        """Запускает периодическую отправку ping сообщений"""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.debug(
            f"Heartbeat started: room_id={self.room_id}, user_id={self.user.id if self.user else 'unknown'}"
        )

    async def _heartbeat_loop(self):
        """Основной loop для отправки ping каждые N секунд"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                current_time = time.time()
                if current_time - self.last_pong_time > self.heartbeat_timeout:
                    logger.warning(
                        f"Heartbeat timeout: room_id={self.room_id}, user_id={self.user.id if self.user else 'unknown'}, last_pong_delta={current_time - self.last_pong_time:.1f}s"
                    )
                    await self.close(code=1000, reason="Heartbeat timeout")
                    break
                await self.send(text_data=json.dumps({"type": "ping", "timestamp": current_time}))
            except asyncio.CancelledError:
                logger.debug(
                    f"Heartbeat loop cancelled: room_id={self.room_id}, user_id={self.user.id if self.user else 'unknown'}"
                )
                break
            except Exception as e:
                logger.error(
                    f"Heartbeat error: room_id={self.room_id}, user_id={self.user.id if self.user else 'unknown'}, error={type(e).__name__}: {str(e)}",
                    exc_info=True,
                )
                break

    async def handle_pong(self, event):
        """Обработка pong ответа от клиента"""
        self.last_pong_time = time.time()
        logger.debug(
            f"Pong received: room_id={self.room_id}, user_id={self.user.id if self.user else 'unknown'}"
        )

    @database_sync_to_async
    def _check_current_permissions(self, user):
        """
        Проверить актуальные permissions для доступа к чату.

        CRITICAL: Вызывается при каждом action для проверки что permissions
        всё ещё актуальны (enrollment не стал INACTIVE, tutor не изменился, и т.д.)

        Returns:
            bool: True если permission актуален
        """
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            service = ChatService()
            return service.can_access_chat(user, room)
        except Exception as e:
            logger.error(
                f"Permission check error: user_id={user.id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            return False

    async def _send_error(self, code, message, errors=None, retry_after=None):
        """Отправить ошибку клиенту

        Args:
            code: Error code (str or int):
                - 4000: Validation error
                - 4001: Authentication error
                - 4002: Access denied
                - 4003: Forbidden (no access to room)
                - 4029: Rate limit exceeded
            message: Error message (str)
            errors: Validation errors dict (optional)
            retry_after: Seconds to wait before retry (optional)
        """
        logger.debug(
            f"Error sent to client: code={code}, user_id={self.user.id if self.user else 'unknown'}, room_id={self.room_id}"
        )
        try:
            error_data = {"type": "error", "code": code, "message": message}
            if errors is not None:
                error_data["errors"] = errors
            if retry_after is not None:
                error_data["retry_after"] = retry_after
            await self.send(text_data=json.dumps(error_data))
        except Exception as e:
            logger.error(
                f"Error sending error message: code={code}, user_id={self.user.id if self.user else 'unknown'}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    async def _check_message_rate_limit(self, user):
        """
        Проверить rate limit на сообщения через DRF ChatMessageThrottle.

        DRF Throttle использует cache под капотом, безопасно в async контексте.
        Returns: True если request разрешен, False если exceeded.
        """
        throttle = ChatMessageThrottle()

        class FakeRequest:
            """Fake request object для DRF Throttle интерфейса"""

            def __init__(self, user):
                self.user = user
                self.META = {
                    "REMOTE_ADDR": "127.0.0.1",
                    "HTTP_X_FORWARDED_FOR": None,
                }

        fake_request = FakeRequest(user)
        allowed = throttle.throttle(fake_request, None)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded: user_id={user.id}, scope=chat_message, threshold=60/minute"
            )
        else:
            logger.debug(f"Rate limit check passed: user_id={user.id}, scope=chat_message")

        return allowed

    async def _check_room_limit(self, user):
        """
        Проверить лимит на количество разных комнат через DRF ChatRoomThrottle.

        DRF Throttle использует cache под капотом, безопасно в async контексте.
        Returns: True если request разрешен, False если exceeded.
        """
        throttle = ChatRoomThrottle()

        class FakeRequest:
            """Fake request object для DRF Throttle интерфейса"""

            def __init__(self, user):
                self.user = user
                self.META = {
                    "REMOTE_ADDR": "127.0.0.1",
                    "HTTP_X_FORWARDED_FOR": None,
                }

        fake_request = FakeRequest(user)
        allowed = throttle.throttle(fake_request, None)

        if not allowed:
            logger.warning(
                f"Room limit exceeded: user_id={user.id}, scope=chat_room, threshold=5/minute"
            )
        else:
            logger.debug(f"Room limit check passed: user_id={user.id}, scope=chat_room")

        return allowed

    @database_sync_to_async
    def _validate_token(self, token):
        """Проверить JWT токен"""
        try:
            decoded = AccessToken(token)
            user_id = decoded["user_id"]
            user = User.objects.get(id=user_id, is_active=True)
            logger.debug(f"Token validated: user_id={user_id}")
            return user
        except Exception as e:
            logger.debug(f"Token validation failed: error={type(e).__name__}")
            return None

    @database_sync_to_async
    def _check_access(self, user):
        """Проверить доступ к комнате"""
        try:
            if not user.is_active:
                logger.debug(
                    f"Access check failed: inactive user, user_id={user.id}, room_id={self.room_id}"
                )
                return False

            room = ChatRoom.objects.get(id=self.room_id)
            service = ChatService()
            has_access = service.can_access_chat(user, room)
            logger.debug(
                f"Access check: user_id={user.id}, room_id={self.room_id}, has_access={has_access}"
            )
            return has_access
        except Exception as e:
            logger.error(
                f"Access check error: user_id={user.id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            return False

    @database_sync_to_async
    def _save_message(self, content):
        """Сохранить сообщение и вернуть данные для broadcast.
        Messages are filtered at DB level (is_deleted=False in Message model)."""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            service = MessageService()
            message = service.send_message(self.user, room, content)

            logger.debug(
                f"Message saved: message_id={message.id}, user_id={self.user.id}, room_id={self.room_id}, content_length={len(content)}"
            )

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
        except Exception as e:
            logger.error(
                f"Message save failed: user_id={self.user.id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    @database_sync_to_async
    def _mark_as_read(self):
        """Отметить чат как прочитанный"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            service = ChatService()
            service.mark_chat_as_read(self.user, room)
            logger.debug(f"Chat marked as read: user_id={self.user.id}, room_id={self.room_id}")
        except Exception as e:
            logger.error(
                f"Mark as read failed: user_id={self.user.id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    @database_sync_to_async
    def _get_user_data(self, user_id):
        """Получить данные пользователя"""
        try:
            user = User.objects.get(id=user_id)
            return {
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
            }
        except Exception as e:
            logger.error(
                f"Get user data failed: user_id={user_id}, room_id={self.room_id}, error={type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            raise
