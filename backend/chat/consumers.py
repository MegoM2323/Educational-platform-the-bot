import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db import transaction
from rest_framework.authtoken.models import Token
from .models import ChatRoom, Message, MessageRead, ChatParticipant, MessageThread
from .serializers import MessageSerializer
from .permissions import check_parent_access_to_room
from accounts.models import User as UserModel

User = get_user_model()
logger = logging.getLogger(__name__)

# WebSocket message size limit (default 1MB)
WEBSOCKET_MESSAGE_MAX_LENGTH = getattr(settings, "WEBSOCKET_MESSAGE_MAX_LENGTH", 1048576)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для чат-комнат
    """

    @database_sync_to_async
    def _validate_token(self, token_key):
        """
        Validate token from query string.
        Returns authenticated user if token is valid, None otherwise.
        """
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            if token.user.is_active:
                return token.user
        except Token.DoesNotExist:
            pass
        return None

    async def _authenticate_token_from_query_string(self):
        """
        Попытается аутентифицировать пользователя через токен в query string.
        Поддерживает форматы:
        - ws://host/ws/chat/room_id/?token=abc123
        - ws://host/ws/chat/room_id/?authorization=Bearer%20abc123
        """
        try:
            query_string = self.scope.get("query_string", b"").decode()
            if not query_string:
                return False

            token = None

            if "token=" in query_string:
                token = query_string.split("token=")[1].split("&")[0]
            elif "authorization=" in query_string:
                auth_header = query_string.split("authorization=")[1].split("&")[0]
                if auth_header.startswith("Bearer%20"):
                    token = auth_header[9:]

            if not token:
                return False

            user = await self._validate_token(token)
            if user:
                self.scope["user"] = user
                logger.info(f"[ChatConsumer] User {user.id} authenticated via token for room {self.room_id}")
                return True

            logger.warning(f"[ChatConsumer] Token validation failed for room {self.room_id}")
            return False

        except Exception as e:
            logger.error(f"[ChatConsumer] Token authentication error: {e}")
            return False

    async def connect(self):
        # 1. Try to get room_id from URL path parameter
        self.room_id = self.scope["url_route"]["kwargs"].get("room_id")

        # 2. If not in path, check query string ?room_id=123
        if not self.room_id:
            query_string = self.scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)
            room_ids = query_params.get("room_id", [])
            if room_ids:
                self.room_id = room_ids[0]

        # 3. If still no room_id, get first available room for user
        if not self.room_id:
            first_room = await self.get_first_available_room()
            if first_room:
                self.room_id = str(first_room.id)
            else:
                user = self.scope.get("user")
                user_id = user.id if user and getattr(user, "is_authenticated", False) else "unauthenticated"
                logger.warning(f"[ChatConsumer] No room_id provided and no rooms available for user {user_id}")
                await self.close(code=4003)
                return

        self.room_group_name = f"chat_{self.room_id}"

        user = self.scope.get("user")
        if not user:
            logger.warning("[ChatConsumer] No user object in scope")
            await self.close(code=4001)
            return

        logger.debug(
            f"[ChatConsumer] Connection attempt: room={self.room_id}, user={user}, authenticated={user.is_authenticated}"
        )

        is_authenticated = user.is_authenticated
        if not is_authenticated:
            is_authenticated = await self._authenticate_token_from_query_string()

        logger.debug(f"[ChatConsumer] After token check: authenticated={is_authenticated}")

        # Проверяем, что пользователь аутентифицирован
        if not is_authenticated:
            logger.warning(f"[ChatConsumer] Connection rejected: user not authenticated")
            await self.close(code=4001)
            return

        # Проверяем, что пользователь имеет доступ к комнате
        has_access = await self.check_room_access()
        logger.debug(f"[ChatConsumer] Room access check: {has_access}")
        if not has_access:
            logger.warning(f"[ChatConsumer] Connection rejected: no room access")
            await self.close(code=4002)
            return

        # Присоединяемся к группе комнаты
        user = self.scope["user"]
        user_role = getattr(user, "role", "unknown")
        logger.debug(
            f"[GroupAdd] BEFORE: Room={self.room_id}, User={user.username} (role={user_role}), Channel={self.channel_name}"
        )

        try:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            logger.debug(
                f"[GroupAdd] SUCCESS: Room={self.room_id}, Group={self.room_group_name}, Channel={self.channel_name}, User={user.username} (role={user_role})"
            )
        except Exception as e:
            logger.error(
                f"[GroupAdd] FAILED to add to group: Room={self.room_id}, User={user.username}, Error={e}",
                exc_info=True,
            )
            raise

        await self.accept()

        # Добавляем родителя в participants после успешного подключения (если нужно)
        await self.add_parent_to_participants_if_needed()

        # Очищаем счётчик непрочитанных сообщений для этого пользователя
        await self.clear_unread_count()

        # Отправляем историю сообщений
        await self.send_room_history()

        # Уведомляем других участников о подключении
        user = self.scope["user"]
        if not user.is_authenticated:
            logger.warning("[ChatConsumer] Cannot broadcast user_joined for unauthenticated user")
        else:
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_joined",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                        },
                    },
                )
                logger.debug(f"[ChatConsumer] Broadcasting user_joined to {self.room_group_name}")
            except Exception as e:
                logger.error(
                    f"Channel layer error broadcasting user_joined in room {self.room_id}: {e}",
                    exc_info=True,
                )

    async def disconnect(self, close_code):
        # Безопасное получение user из scope
        user = self.scope.get("user")

        # Проверяем, что user существует и аутентифицирован
        if not user or not getattr(user, "is_authenticated", False):
            # Если пользователь не аутентифицирован, просто покидаем группу
            if hasattr(self, "room_group_name") and self.room_group_name:
                try:
                    await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                except Exception as e:
                    logger.error(
                        f"Error leaving group on disconnect (unauthenticated): {e}",
                        exc_info=True,
                    )
            return

        # Безопасное получение room_id
        room_id = getattr(self, "room_id", None)

        if hasattr(self, "room_group_name") and self.room_group_name:
            # Очищаем индикатор печати для отключающегося пользователя
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "typing_stop",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                        },
                    },
                )
            except Exception as e:
                room_info = f"room {room_id}" if room_id else "unknown room"
                logger.error(
                    f"Error clearing typing on disconnect in {room_info}: {e}",
                    exc_info=True,
                )

            # Уведомляем других участников об отключении
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_left",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                        },
                    },
                )
            except Exception as e:
                room_info = f"room {room_id}" if room_id else "unknown room"
                logger.error(
                    f"Channel layer error broadcasting user_left in {room_info}: {e}",
                    exc_info=True,
                )

            # Покидаем группу комнаты
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                logger.debug(f"[GroupDiscard] Group={self.room_group_name}, Channel={self.channel_name}")
            except Exception as e:
                logger.error(f"Error leaving group {self.room_group_name}: {e}", exc_info=True)

    async def receive(self, text_data):
        # Проверяем размер сообщения для защиты от DoS
        if len(text_data) > WEBSOCKET_MESSAGE_MAX_LENGTH:
            logger.debug(f"WebSocket message size exceeds limit: {len(text_data)} > {WEBSOCKET_MESSAGE_MAX_LENGTH}")
            await self.send(text_data=json.dumps({"type": "error", "message": "Message too large"}))
            return

        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "chat_message":
                await self.handle_chat_message(data)
            elif message_type == "message_edit":
                await self.handle_message_edit(data)
            elif message_type == "message_delete":
                await self.handle_message_delete(data)
            elif message_type == "typing":
                await self.handle_typing(data)
            elif message_type == "mark_read":
                await self.handle_mark_read(data)
            elif message_type == "typing_stop":
                await self.handle_typing_stop(data)
            elif message_type == "pin_message":
                await self.handle_pin_message(data)
            elif message_type == "lock_chat":
                await self.handle_lock_chat(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({"type": "error", "message": "Internal server error"}))

    async def handle_chat_message(self, data):
        """Обработка нового сообщения"""
        content = data.get("content", "").strip()
        if not content:
            # Отправляем ошибку валидации отправителю
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message content required",
                        "code": "validation_error",
                    }
                )
            )
            return

        # Проверяем, что пользователь является участником комнаты (защита от IDOR)
        if not await self.check_user_is_participant(self.room_id):
            logger.debug(
                f'[HandleChatMessage] Access denied: user {self.scope["user"].id} is not a participant in room {self.room_id}'
            )
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "You are not a participant in this room",
                        "code": "access_denied",
                    }
                )
            )
            return

        # Создаем сообщение
        message = await self.create_message(content)
        logger.debug(f"[HandleChatMessage] Created message: {message}")
        if message:
            # Подтверждаем отправителю, что сообщение сохранено (с полным объектом)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "message_sent",
                        "message": message,
                        "status": "delivered",
                    }
                )
            )

            # Убедиться, что все участники находятся в группе перед трансляцией
            participant_count = await self.verify_all_participants_in_group()

            # Отправляем сообщение всем участникам группы
            logger.debug(
                f'[HandleChatMessage] Broadcasting to group {self.room_group_name}, message_id={message.get("id", "unknown")}, participant_count={participant_count}'
            )
            try:
                await self.channel_layer.group_send(self.room_group_name, {"type": "chat_message", "message": message})
                logger.debug(
                    f'[HandleChatMessage] Broadcast completed for message_id={message.get("id", "unknown")} to {participant_count} participants'
                )
            except Exception as e:
                logger.error(f"Channel layer error in room {self.room_id}: {e}", exc_info=True)
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "message": "Message delivery failed",
                            "code": "channel_error",
                        }
                    )
                )
        else:
            # Сообщаем отправителю об ошибке сохранения
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Failed to save message",
                        "code": "save_error",
                    }
                )
            )

    async def handle_typing(self, data):
        """Обработка индикатора печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing",
                "user": {
                    "id": self.scope["user"].id,
                    "username": self.scope["user"].username,
                    "first_name": self.scope["user"].first_name,
                    "last_name": self.scope["user"].last_name,
                },
            },
        )

    async def handle_typing_stop(self, data):
        """Обработка остановки печати"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_stop",
                "user": {
                    "id": self.scope["user"].id,
                    "username": self.scope["user"].username,
                },
            },
        )

    async def handle_mark_read(self, data):
        """Обработка отметки о прочтении"""
        message_id = data.get("message_id")
        if message_id:
            try:
                await self.mark_message_read(message_id)
            except Exception as e:
                # Не распространяем ошибку клиенту - silent fail для отметок о прочтении
                logger.error(f"Error marking message as read: {e}", exc_info=True)

    async def handle_message_edit(self, data):
        """Обработка редактирования сообщения"""
        message_id = data.get("message_id")
        new_content = data.get("content", "").strip()

        if not message_id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message ID required",
                        "code": "validation_error",
                    }
                )
            )
            return

        if not new_content:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message content required",
                        "code": "validation_error",
                    }
                )
            )
            return

        # IDOR Check 1: Пользователь должен быть участником комнаты
        if not await self.check_user_is_participant(self.room_id):
            logger.warning(
                f"[HandleMessageEdit] Non-participant {self.scope['user'].id} tried to edit message in room {self.room_id}"
            )
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "You are not a participant in this room",
                        "code": "access_denied",
                    }
                )
            )
            return

        # Редактируем сообщение в БД
        result = await self.edit_message(message_id, new_content)

        if result.get("error"):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": result["error"],
                        "code": result.get("code", "edit_error"),
                    }
                )
            )
            return

        # Подтверждаем редактору успешное редактирование
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edit_confirmed",
                    "message_id": message_id,
                    "status": "edited",
                }
            )
        )

        # Рассылаем обновление всем участникам комнаты
        logger.info(f"[HandleMessageEdit] Broadcasting edit to group {self.room_group_name}, message_id={message_id}")
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "message_edited",
                    "message_id": message_id,
                    "content": new_content,
                    "is_edited": True,
                    "edited_at": result["edited_at"],
                },
            )
        except Exception as e:
            logger.error(
                f"Channel layer error broadcasting message_edited in room {self.room_id}: {e}",
                exc_info=True,
            )

    async def chat_message(self, event):
        """Отправка сообщения клиенту"""
        message_id = event["message"].get("id", "unknown")
        user = self.scope["user"]
        if not user.is_authenticated:
            logger.warning(f"[ChatMessage Handler] Cannot send to unauthenticated user, message_id={message_id}")
            return

        user_role = getattr(user, "role", "unknown")
        logger.debug(
            f"[ChatMessage Handler] CALLED! message_id={message_id}, recipient={user.username} (role={user_role}), room={self.room_id}"
        )

        try:
            await self.send(text_data=json.dumps({"type": "chat_message", "message": event["message"]}))
            logger.debug(
                f"[ChatMessage Handler] SENT to client! message_id={message_id}, recipient={user.username} (role={user_role})"
            )
        except Exception as e:
            logger.error(
                f"[ChatMessage Handler] FAILED to send! message_id={message_id}, recipient={user.username}, Error={e}",
                exc_info=True,
            )

    async def typing(self, event):
        """Отправка индикатора печати клиенту"""
        await self.send(text_data=json.dumps({"type": "typing", "user": event["user"]}))

    async def typing_stop(self, event):
        """Отправка остановки печати клиенту"""
        await self.send(text_data=json.dumps({"type": "typing_stop", "user": event["user"]}))

    async def user_joined(self, event):
        """Уведомление о присоединении пользователя"""
        await self.send(text_data=json.dumps({"type": "user_joined", "user": event["user"]}))

    async def user_left(self, event):
        """Уведомление об уходе пользователя"""
        await self.send(text_data=json.dumps({"type": "user_left", "user": event["user"]}))

    async def message_edited(self, event):
        """Отправка уведомления о редактировании сообщения клиенту"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edited",
                    "message_id": event["message_id"],
                    "content": event["content"],
                    "is_edited": event["is_edited"],
                    "edited_at": event["edited_at"],
                }
            )
        )

    async def message_deleted(self, event):
        """Отправка уведомления об удалении сообщения клиенту"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_deleted",
                    "message_id": event["message_id"],
                    "deleted_by": event.get("deleted_by"),
                    "deleted_by_role": event.get("deleted_by_role"),
                }
            )
        )

    async def message_pinned(self, event):
        """Отправка уведомления о закреплении сообщения клиенту"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_pinned",
                    "data": {
                        "message_id": event["message_id"],
                        "is_pinned": event["is_pinned"],
                        "thread_id": event.get("thread_id"),
                    },
                }
            )
        )

    async def chat_locked(self, event):
        """Отправка уведомления о блокировке чата клиенту"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_locked",
                    "data": {
                        "chat_id": event["chat_id"],
                        "is_active": event["is_active"],
                    },
                }
            )
        )

    async def handle_message_delete(self, data):
        """Обработка удаления сообщения"""
        message_id = data.get("message_id")

        if not message_id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message ID required",
                        "code": "validation_error",
                    }
                )
            )
            return

        # IDOR Check 1: Пользователь должен быть участником комнаты
        if not await self.check_user_is_participant(self.room_id):
            logger.warning(
                f"[HandleMessageDelete] Non-participant {self.scope['user'].id} tried to delete message in room {self.room_id}"
            )
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "You are not a participant in this room",
                        "code": "access_denied",
                    }
                )
            )
            return

        result = await self.delete_message(message_id)

        if result.get("error"):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": result["error"],
                        "code": result.get("code", "delete_error"),
                    }
                )
            )
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_delete_confirmed",
                    "message_id": message_id,
                    "status": "deleted",
                }
            )
        )

        user = self.scope["user"]
        if not user.is_authenticated:
            logger.warning(
                f"[HandleMessageDelete] Cannot broadcast delete for unauthenticated user, message_id={message_id}"
            )
            return

        logger.info(
            f"[HandleMessageDelete] Broadcasting delete to group {self.room_group_name}, message_id={message_id}"
        )
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "message_deleted",
                    "message_id": message_id,
                    "deleted_by": user.id,
                    "deleted_by_role": result.get("deleted_by_role", "author"),
                },
            )
        except Exception as e:
            logger.error(
                f"Channel layer error broadcasting message_deleted in room {self.room_id}: {e}",
                exc_info=True,
            )

    async def handle_pin_message(self, data):
        """Обработка закрепления сообщения"""
        message_id = data.get("message_id")

        if not message_id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message ID required",
                        "code": "validation_error",
                    }
                )
            )
            return

        result = await self.pin_message(message_id)

        if result.get("error"):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": result["error"],
                        "code": result.get("code", "pin_error"),
                    }
                )
            )
            return

        logger.info(f"[HandlePinMessage] Broadcasting pin to group {self.room_group_name}, message_id={message_id}")
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "message_pinned",
                    "message_id": message_id,
                    "is_pinned": result["is_pinned"],
                    "thread_id": result.get("thread_id"),
                },
            )
        except Exception as e:
            logger.error(
                f"Channel layer error broadcasting message_pinned in room {self.room_id}: {e}",
                exc_info=True,
            )

    async def handle_lock_chat(self, data):
        """Обработка блокировки чата"""
        result = await self.lock_chat()

        if result.get("error"):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": result["error"],
                        "code": result.get("code", "lock_error"),
                    }
                )
            )
            return

        logger.info(f"[HandleLockChat] Broadcasting lock to group {self.room_group_name}")
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_locked",
                    "chat_id": self.room_id,
                    "is_active": result["is_active"],
                },
            )
        except Exception as e:
            logger.error(
                f"Channel layer error broadcasting chat_locked in room {self.room_id}: {e}",
                exc_info=True,
            )

    @database_sync_to_async
    def delete_message(self, message_id):
        """
        Удаление сообщения (soft delete).

        Проверяет:
        - Существование сообщения
        - Принадлежность сообщения текущей комнате
        - Что пользователь является автором или модератором

        Возвращает dict с результатом или error.
        """
        from django.utils import timezone

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            logger.warning(f"[delete_message] Message {message_id} not found")
            return {"error": "Message not found", "code": "not_found"}

        user = self.scope["user"]

        if str(message.room_id) != str(self.room_id):
            logger.warning(
                f"[delete_message] IDOR attempt: user {user.id} tried to delete message {message_id} from different room {message.room_id}"
            )
            return {
                "error": "Message does not belong to this room",
                "code": "access_denied",
            }

        is_author = message.sender_id == user.id
        is_moderator = user.is_staff or user.is_superuser or user.role in ["teacher", "admin"]

        if not is_author and not is_moderator:
            logger.warning(
                f"[delete_message] Access denied: user {user.id} tried to delete message {message_id} from author {message.sender_id}"
            )
            return {
                "error": "You can only delete your own messages",
                "code": "access_denied",
            }

        if message.is_deleted:
            logger.debug(f"[delete_message] Message {message_id} already deleted")
            return {"error": "Message already deleted", "code": "validation_error"}

        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.deleted_by = user
        message.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        role_type = "author" if is_author else "moderator"
        logger.debug(f"[delete_message] Message {message_id} deleted by {role_type} user {user.id}")
        return {"deleted_by_role": role_type}

    @database_sync_to_async
    def pin_message(self, message_id):
        """
        Закрепление/открепление сообщения.

        Только для модераторов (teacher, tutor, admin, staff).

        Возвращает dict с is_pinned или error.
        """
        try:
            message = Message.objects.get(id=message_id, room_id=self.room_id, is_deleted=False)
        except Message.DoesNotExist:
            return {"error": "Message not found", "code": "not_found"}

        user = self.scope["user"]
        is_moderator = user.is_staff or user.is_superuser or user.role in ["teacher", "tutor", "admin"]

        if not is_moderator:
            return {
                "error": "Permission denied. Moderation rights required.",
                "code": "access_denied",
            }

        if not message.thread:
            thread = MessageThread.objects.create(
                room_id=self.room_id,
                title=message.content[:100] if message.content else f"Thread #{message.id}",
                created_by=message.sender,
            )
            message.thread = thread
            message.save(update_fields=["thread"])

        thread = message.thread
        thread.is_pinned = not thread.is_pinned
        thread.save(update_fields=["is_pinned", "updated_at"])

        logger.info(
            f'[pin_message] Message {message_id} {"pinned" if thread.is_pinned else "unpinned"} by user {user.id}'
        )
        return {"is_pinned": thread.is_pinned, "thread_id": str(thread.id)}

    @database_sync_to_async
    def lock_chat(self):
        """
        Блокировка/разблокировка чата.

        Только для модераторов (teacher, tutor, admin, staff).

        Возвращает dict с is_active или error.
        """
        try:
            room = ChatRoom.objects.get(id=self.room_id)
        except ChatRoom.DoesNotExist:
            return {"error": "Chat not found", "code": "not_found"}

        user = self.scope["user"]
        is_moderator = user.is_staff or user.is_superuser or user.role in ["teacher", "tutor", "admin"]

        if not is_moderator:
            return {
                "error": "Permission denied. Moderation rights required.",
                "code": "access_denied",
            }

        room.is_active = not room.is_active
        room.save(update_fields=["is_active", "updated_at"])

        logger.info(f'[lock_chat] Room {self.room_id} {"unlocked" if room.is_active else "locked"} by user {user.id}')
        return {"is_active": room.is_active}

    @database_sync_to_async
    def check_room_access(self):
        """
        Проверка доступа к комнате.

        Проверяет доступ через:
        1. Admin/Staff bypass для форумных чатов (read-only)
        2. M2M participants (ChatRoom.participants)
        3. ChatParticipant записи (для обратной совместимости)
        4. Родительский доступ: если пользователь - родитель и его ребёнок является участником

        Дополнительная проверка для teacher:
        - Teacher может подключаться к FORUM_SUBJECT чатам (через enrollment или как participant)
        - Teacher может подключаться к FORUM_TUTOR чатам если явно добавлен как participant
        """
        try:
            room = ChatRoom.objects.select_related("enrollment").get(id=self.room_id)
            user = self.scope["user"]
            user_id = user.id

            logger.debug(
                f"check_room_access: user={user_id}, room={self.room_id}, "
                f"participants_count={room.participants.count()}"
            )

            # Admin/Staff bypass - read-only access to all chats
            if user.is_staff or user.is_superuser:
                logger.info(f"[check_room_access] Admin {user_id} granted access to room {self.room_id}")
                return True

            if user.role == UserModel.Role.TEACHER:
                from django.db.models import Q

                if room.type in [
                    ChatRoom.Type.FORUM_SUBJECT,
                    ChatRoom.Type.FORUM_TUTOR,
                ]:
                    has_access = room.participants.filter(id=user_id).exists()
                    if not has_access and room.enrollment and room.enrollment.teacher_id == user_id:
                        has_access = True
                    if has_access:
                        logger.info(f"[check_room_access] Teacher {user_id} accessing room {self.room_id}")
                        return True
                    logger.debug(f"[check_room_access] Access denied for teacher {user_id} to room {self.room_id}")
                    return False
                # For other room types (CLASS, etc), check M2M participants
                if room.participants.filter(id=user_id).exists():
                    logger.info(f"[check_room_access] Teacher {user_id} accessing room {self.room_id} via participants")
                    return True
                logger.debug(f"[check_room_access] Access denied for teacher {user_id} to room {self.room_id}")
                return False

            # Дополнительная проверка для tutor
            if user.role == UserModel.Role.TUTOR:
                # Tutor has access to FORUM_TUTOR chats
                if room.type == ChatRoom.Type.FORUM_TUTOR:
                    # Check if tutor is participant
                    if room.participants.filter(id=user_id).exists():
                        logger.debug(
                            f"[check_room_access] Tutor {user_id} has access to FORUM_TUTOR room {self.room_id} via M2M"
                        )
                        return True

                    # Check via enrollment relationship (if FORUM_TUTOR is linked to enrollment)
                    if room.enrollment:
                        from materials.models import SubjectEnrollment

                        # Check if tutor is linked to the student in enrollment
                        try:
                            enrollment = SubjectEnrollment.objects.select_related(
                                "student", "student__student_profile"
                            ).get(id=room.enrollment.id)
                            student = enrollment.student

                            # Check if tutor is linked to student via StudentProfile.tutor OR created the student
                            is_student_tutor = (
                                student.student_profile and student.student_profile.tutor_id == user_id
                            ) or (student.created_by_tutor_id == user_id)

                            if is_student_tutor:
                                logger.info(
                                    f"[check_room_access] Tutor {user_id} verified via enrollment.student relationship, adding to room {self.room_id}"
                                )
                                # Add tutor to participants for faster future access
                                with transaction.atomic():
                                    room.participants.add(user)
                                    ChatParticipant.objects.get_or_create(room=room, user=user)
                                self.tutor_added_to_participants = True
                                return True
                            else:
                                logger.debug(
                                    f"[check_room_access] Tutor {user_id} is not linked to student in enrollment {room.enrollment.id}"
                                )
                        except ObjectDoesNotExist:
                            logger.warning(
                                f"[check_room_access] Enrollment {room.enrollment.id} not found for tutor {user_id}"
                            )

                    # Check via student's tutor relationship (without enrollment)
                    from accounts.models import StudentProfile

                    student_ids = room.participants.filter(role=UserModel.Role.STUDENT).values_list("id", flat=True)

                    if student_ids:
                        related_students = StudentProfile.objects.filter(user_id__in=student_ids, tutor=user)

                        if related_students.exists():
                            logger.info(
                                f"[check_room_access] Tutor {user_id} verified via StudentProfile.tutor relationship, adding to room {self.room_id}"
                            )
                            # Add tutor to participants for faster future access
                            with transaction.atomic():
                                room.participants.add(user)
                                ChatParticipant.objects.get_or_create(room=room, user=user)
                            self.tutor_added_to_participants = True
                            return True
                        else:
                            logger.debug(
                                f"[check_room_access] Tutor {user_id} has no StudentProfile.tutor matches in room {self.room_id}"
                            )
                    else:
                        logger.debug(f"[check_room_access] No student participants found in room {self.room_id}")

                    logger.debug(
                        f"[check_room_access] Access denied for tutor {user_id} to FORUM_TUTOR room {self.room_id} - not linked to students"
                    )
                    return False

                # Tutor can also access FORUM_SUBJECT if explicitly added as participant
                elif room.type == ChatRoom.Type.FORUM_SUBJECT:
                    if room.participants.filter(id=user_id).exists():
                        logger.info(
                            f"[check_room_access] Tutor {user_id} accessing FORUM_SUBJECT room {self.room_id} as participant"
                        )
                        return True

                    logger.debug(
                        f"[check_room_access] Access denied for tutor {user_id} to FORUM_SUBJECT room {self.room_id} - not a participant"
                    )
                    return False

                # Access denied for other room types
                logger.debug(
                    f"[check_room_access] Access denied for tutor {user_id} to room {self.room_id} (type={room.type})"
                )
                return False

            # Проверка 1: M2M participants
            if room.participants.filter(id=user_id).exists():
                logger.debug(f"[check_room_access] User {user_id} has access via M2M participants")
                return True

            # Проверка 2: ChatParticipant (fallback для старых чатов)
            if ChatParticipant.objects.filter(room=room, user=user).exists():
                # Синхронизируем: добавляем в M2M атомарно
                with transaction.atomic():
                    # M2M add безопасен для дубликатов, не вызывает IntegrityError
                    room.participants.add(user)
                logger.info(f"[check_room_access] User {user_id} synced from ChatParticipant to M2M")
                return True

            # Проверка 3: Родительский доступ к чатам детей
            # Родители могут просматривать FORUM_SUBJECT и FORUM_TUTOR чаты своих детей
            # Используем централизованную функцию из permissions.py БЕЗ побочных эффектов
            # (добавление в participants будет после успешного accept)
            if user.role == UserModel.Role.PARENT:
                if check_parent_access_to_room(user, room, add_to_participants=False):
                    logger.info(f"[check_room_access] Parent {user_id} has child participant in room {self.room_id}")
                    # Сохраняем флаг для добавления родителя в participants после успешного connect
                    self.parent_needs_participant_add = True
                    self.parent_user_id = user_id
                    return True

            logger.debug(
                f"[check_room_access] Access denied: user {user_id} (role={user.role}) "
                f"is not a participant in room {self.room_id} (type={room.type})"
            )
            return False
        except ObjectDoesNotExist:
            logger.debug(f"[check_room_access] Room {self.room_id} does not exist")
            return False

    @database_sync_to_async
    def get_first_available_room(self):
        """
        Get first available room for authenticated user.

        Returns first room where user is a participant.
        Used as fallback when room_id is not provided in URL or query string.
        """
        user = self.scope["user"]
        if not user.is_authenticated:
            return None

        try:
            # Get first room where user is participant (M2M)
            room = ChatRoom.objects.filter(participants=user).first()

            if room:
                logger.info(f"[get_first_available_room] Found room {room.id} for user {user.id}")
            else:
                logger.debug(f"[get_first_available_room] No rooms found for user {user.id}")

            return room
        except Exception as e:
            logger.error(f"[get_first_available_room] Error: {e}", exc_info=True)
            return None

    @database_sync_to_async
    def add_parent_to_participants_if_needed(self):
        """
        Добавляет родителя в participants комнаты после успешного WebSocket подключения.
        Вызывается только если self.parent_needs_participant_add = True (установлен в check_room_access).
        """
        if not getattr(self, "parent_needs_participant_add", False):
            return

        try:
            room = ChatRoom.objects.get(id=self.room_id)
            user = User.objects.get(id=self.parent_user_id)
            with transaction.atomic():
                room.participants.add(user)
                ChatParticipant.objects.get_or_create(room=room, user=user)
            logger.info(f"[add_parent_to_participants] Added parent {self.parent_user_id} to room {self.room_id}")
            self.parent_needs_participant_add = False
        except Exception as e:
            logger.error(f"[add_parent_to_participants] Error adding parent to participants: {e}")

    @database_sync_to_async
    def check_user_is_participant(self, room_id):
        """
        Проверка, что текущий пользователь является участником комнаты.

        Проверяет в двух местах для обратной совместимости:
        1. ChatParticipant (предпочтительно)
        2. ChatRoom.participants M2M (fallback для старых чатов)

        Дополнительные проверки для ролей:
        - Teacher может быть участником FORUM_SUBJECT и FORUM_TUTOR чатов (если добавлен как participant)
        - Tutor может быть участником FORUM_TUTOR и FORUM_SUBJECT чатов (если добавлен как participant)
        """
        user = self.scope["user"]

        try:
            room = ChatRoom.objects.select_related("enrollment").get(id=room_id)
        except ChatRoom.DoesNotExist:
            return False

        # Проверка типа чата для teacher
        # Teacher can access FORUM_SUBJECT and FORUM_TUTOR (if participant)
        if user.role == UserModel.Role.TEACHER:
            if room.type not in [
                ChatRoom.Type.FORUM_SUBJECT,
                ChatRoom.Type.FORUM_TUTOR,
            ]:
                return False

        # Проверка типа чата для tutor
        if user.role == UserModel.Role.TUTOR:
            # Tutor can access FORUM_TUTOR and FORUM_SUBJECT (if participant)
            if room.type not in [
                ChatRoom.Type.FORUM_TUTOR,
                ChatRoom.Type.FORUM_SUBJECT,
            ]:
                return False

        # Сначала проверяем ChatParticipant (быстрее и надежнее)
        if ChatParticipant.objects.filter(room_id=room_id, user=user).exists():
            return True

        # Fallback: проверяем M2M participants для обратной совместимости
        if room.participants.filter(id=user.id).exists():
            # Создаем ChatParticipant атомарно для будущих проверок
            try:
                with transaction.atomic():
                    ChatParticipant.objects.get_or_create(room=room, user=user)
            except Exception as e:
                # Игнорируем ошибки создания (возможен race condition), участник уже есть в M2M
                logger.debug(f"[check_user_is_participant] ChatParticipant sync skipped: {e}")
            return True

        return False

    @database_sync_to_async
    def verify_all_participants_in_group(self):
        """
        Убедиться, что все участники комнаты находятся в WebSocket группе.

        Проверяет всех участников комнаты и убеждается, что они в группе.
        Возвращает количество участников.

        Примечание: На уровне WebSocket мы не можем напрямую добавить других пользователей в группу,
        но мы можем логировать отсутствующих участников для отладки.
        """
        try:
            room = ChatRoom.objects.get(id=self.room_id)

            # Получаем всех участников комнаты
            participants = list(room.participants.all().values_list("id", "username", "role"))

            if participants:
                logger.info(
                    f"[verify_all_participants_in_group] Room {self.room_id} has {len(participants)} participants: {[p[1] for p in participants]}"
                )

            return len(participants)
        except ObjectDoesNotExist:
            logger.warning(f"[verify_all_participants_in_group] Room {self.room_id} not found")
            return 0
        except Exception as e:
            logger.error(
                f"[verify_all_participants_in_group] Error verifying participants in room {self.room_id}: {e}",
                exc_info=True,
            )
            return 0

    @database_sync_to_async
    def create_message(self, content):
        """Создание нового сообщения с защитой от race condition"""
        try:
            with transaction.atomic():
                room = ChatRoom.objects.select_for_update().get(id=self.room_id)

                is_participant = ChatParticipant.objects.filter(room=room, user=self.scope["user"]).exists()

                if not is_participant:
                    if room.participants.filter(id=self.scope["user"].id).exists():
                        ChatParticipant.objects.get_or_create(room=room, user=self.scope["user"])
                        is_participant = True

                if not is_participant:
                    logger.debug(
                        f'[CreateMessage] Access denied: user {self.scope["user"].id} is not a participant in room {self.room_id}'
                    )
                    return None

                message = Message.objects.create(room=room, sender=self.scope["user"], content=content)
                return MessageSerializer(message).data
        except ObjectDoesNotExist:
            return None

    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Отметка сообщения как прочитанного"""
        try:
            message = Message.objects.get(id=message_id)
            MessageRead.objects.get_or_create(message=message, user=self.scope["user"])
        except ObjectDoesNotExist:
            pass

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """
        Редактирование сообщения в БД.

        Проверяет:
        - Существование сообщения
        - Что пользователь является автором сообщения
        - Что сообщение принадлежит текущей комнате
        - Что сообщение не удалено

        Возвращает dict с edited_at или error.
        """
        from django.utils import timezone

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            logger.warning(f"[edit_message] Message {message_id} not found")
            return {"error": "Message not found", "code": "not_found"}

        user = self.scope["user"]

        if str(message.room_id) != str(self.room_id):
            logger.warning(
                f"[edit_message] IDOR attempt: user {user.id} tried to edit message {message_id} from different room {message.room_id}"
            )
            return {
                "error": "Message does not belong to this room",
                "code": "access_denied",
            }

        if message.sender_id != user.id:
            logger.warning(
                f"[edit_message] Access denied: user {user.id} tried to edit message {message_id} from author {message.sender_id}"
            )
            return {
                "error": "You can only edit your own messages",
                "code": "access_denied",
            }

        if message.is_deleted:
            logger.debug(f"[edit_message] Cannot edit deleted message {message_id}")
            return {"error": "Cannot edit deleted message", "code": "validation_error"}

        message.content = new_content
        message.is_edited = True
        message.save(update_fields=["content", "is_edited", "updated_at"])

        logger.debug(f"[edit_message] Message {message_id} edited by user {user.id}")
        return {"edited_at": message.updated_at.isoformat()}

    @database_sync_to_async
    def clear_unread_count(self):
        """
        Очистка счётчика непрочитанных сообщений при открытии чата.
        Обновляет last_read_at в ChatParticipant на текущее время.
        """
        from django.utils import timezone

        try:
            room = ChatRoom.objects.get(id=self.room_id)
            user = self.scope["user"]

            # Обновляем или создаём запись ChatParticipant с текущим временем прочтения
            participant, created = ChatParticipant.objects.get_or_create(room=room, user=user)
            participant.last_read_at = timezone.now()
            participant.save(update_fields=["last_read_at"])

            logger.debug(f"[clear_unread_count] Cleared unread count for user {user.id} in room {self.room_id}")
        except ObjectDoesNotExist:
            logger.warning(f"[clear_unread_count] Room {self.room_id} not found")
        except Exception as e:
            logger.error(f"[clear_unread_count] Error clearing unread count: {e}")

    @database_sync_to_async
    def get_room_history(self):
        """Получение истории сообщений комнаты из БД"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            # Получаем ID последних 50 сообщений
            latest_ids = room.messages.filter(is_deleted=False).order_by("-created_at").values("id")[:50]
            # Получаем эти сообщения в хронологическом порядке (старые первые)
            messages = room.messages.filter(id__in=latest_ids).select_related("sender").order_by("created_at")
            return [MessageSerializer(msg).data for msg in messages]
        except ObjectDoesNotExist:
            return []

    async def send_room_history(self):
        """Отправка истории сообщений клиенту"""
        messages = await self.get_room_history()
        await self.send(text_data=json.dumps({"type": "room_history", "messages": messages}))


class GeneralChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для общего чата
    """

    @database_sync_to_async
    def _validate_token(self, token_key):
        """
        Validate token from query string.
        Returns authenticated user if token is valid, None otherwise.
        """
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            if token.user.is_active:
                return token.user
        except Token.DoesNotExist:
            pass
        return None

    async def _authenticate_token_from_query_string(self):
        """
        Попытается аутентифицировать пользователя через токен в query string.
        Поддерживает форматы:
        - ws://host/ws/general_chat/?token=abc123
        - ws://host/ws/general_chat/?authorization=Bearer%20abc123
        """
        try:
            query_string = self.scope.get("query_string", b"").decode()
            if not query_string:
                return False

            token = None

            if "token=" in query_string:
                token = query_string.split("token=")[1].split("&")[0]
            elif "authorization=" in query_string:
                auth_header = query_string.split("authorization=")[1].split("&")[0]
                if auth_header.startswith("Bearer%20"):
                    token = auth_header[9:]

            if not token:
                return False

            user = await self._validate_token(token)
            if user:
                self.scope["user"] = user
                logger.info(f"[GeneralChatConsumer] User {user.id} authenticated via token")
                return True

            logger.warning(f"[GeneralChatConsumer] Token validation failed")
            return False

        except Exception as e:
            logger.error(f"[GeneralChatConsumer] Token authentication error: {e}")
            return False

    async def connect(self):
        self.room_group_name = "general_chat"

        is_authenticated = self.scope["user"].is_authenticated
        if not is_authenticated:
            is_authenticated = await self._authenticate_token_from_query_string()

        # Проверяем, что пользователь аутентифицирован
        if not is_authenticated:
            await self.close(code=4001)
            return

        # Присоединяемся к группе общего чата
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Очищаем счётчик непрочитанных сообщений для общего чата
        await self.clear_general_unread_count()

        # Отправляем историю сообщений
        await self.send_general_chat_history()

    async def disconnect(self, close_code):
        # Безопасное получение user из scope
        user = self.scope.get("user")

        # Проверяем, что user существует и аутентифицирован
        if not user or not getattr(user, "is_authenticated", False):
            # Если пользователь не аутентифицирован, просто покидаем группу
            if hasattr(self, "room_group_name") and self.room_group_name:
                try:
                    await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                except Exception as e:
                    logger.error(
                        f"Error leaving general chat group on disconnect (unauthenticated): {e}",
                        exc_info=True,
                    )
            return

        if hasattr(self, "room_group_name") and self.room_group_name:
            # Очищаем индикатор печати для отключающегося пользователя
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "typing_stop",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                        },
                    },
                )
            except Exception as e:
                logger.error(
                    f"Error clearing typing on disconnect in general chat: {e}",
                    exc_info=True,
                )

            # Покидаем группу общего чата
            try:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            except Exception as e:
                logger.error(f"Error leaving general chat group: {e}", exc_info=True)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "chat_message":
                await self.handle_chat_message(data)
            elif message_type == "message_edit":
                await self.handle_message_edit(data)
            elif message_type == "typing":
                await self.handle_typing(data)
            elif message_type == "typing_stop":
                await self.handle_typing_stop(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
        except Exception as e:
            logger.error(f"Error in general chat receive: {e}")
            await self.send(text_data=json.dumps({"type": "error", "message": "Internal server error"}))

    async def handle_chat_message(self, data):
        """Обработка нового сообщения в общем чате"""
        content = data.get("content", "").strip()
        if not content:
            # Отправляем ошибку валидации отправителю
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message content required",
                        "code": "validation_error",
                    }
                )
            )
            return

        # Создаем сообщение в общем чате
        message = await self.create_general_message(content)
        if message:
            # Подтверждаем отправителю, что сообщение сохранено (с полным объектом)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "message_sent",
                        "message": message,
                        "status": "delivered",
                    }
                )
            )
            # Отправляем сообщение всем участникам группы
            try:
                await self.channel_layer.group_send(self.room_group_name, {"type": "chat_message", "message": message})
            except Exception as e:
                logger.error(f"Channel layer error in general chat: {e}", exc_info=True)
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "message": "Message delivery failed",
                            "code": "channel_error",
                        }
                    )
                )
        else:
            # Сообщаем отправителю об ошибке сохранения
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Failed to save message",
                        "code": "save_error",
                    }
                )
            )

    async def handle_typing(self, data):
        """Обработка индикатора печати"""
        user = self.scope["user"]
        if not user.is_authenticated:
            logger.warning("[GeneralChatConsumer] Cannot broadcast typing for unauthenticated user")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
        )

    async def handle_typing_stop(self, data):
        """Обработка остановки печати"""
        user = self.scope["user"]
        if not user.is_authenticated:
            logger.warning("[GeneralChatConsumer] Cannot broadcast typing_stop for unauthenticated user")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_stop",
                "user": {
                    "id": user.id,
                    "username": user.username,
                },
            },
        )

    async def chat_message(self, event):
        """Отправка сообщения клиенту"""
        await self.send(text_data=json.dumps({"type": "chat_message", "message": event["message"]}))

    async def typing(self, event):
        """Отправка индикатора печати клиенту"""
        await self.send(text_data=json.dumps({"type": "typing", "user": event["user"]}))

    async def typing_stop(self, event):
        """Отправка остановки печати клиенту"""
        await self.send(text_data=json.dumps({"type": "typing_stop", "user": event["user"]}))

    async def handle_message_edit(self, data):
        """Обработка редактирования сообщения в общем чате"""
        message_id = data.get("message_id")
        new_content = data.get("content", "").strip()

        if not message_id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message ID required",
                        "code": "validation_error",
                    }
                )
            )
            return

        if not new_content:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Message content required",
                        "code": "validation_error",
                    }
                )
            )
            return

        # Редактируем сообщение в БД
        result = await self.edit_general_message(message_id, new_content)

        if result.get("error"):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": result["error"],
                        "code": result.get("code", "edit_error"),
                    }
                )
            )
            return

        # Подтверждаем редактору успешное редактирование
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edit_confirmed",
                    "message_id": message_id,
                    "status": "edited",
                }
            )
        )

        # Рассылаем обновление всем участникам общего чата
        logger.info(f"[HandleMessageEdit] Broadcasting edit to general chat, message_id={message_id}")
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "message_edited",
                    "message_id": message_id,
                    "content": new_content,
                    "is_edited": True,
                    "edited_at": result["edited_at"],
                },
            )
        except Exception as e:
            logger.error(
                f"Channel layer error broadcasting message_edited in general chat: {e}",
                exc_info=True,
            )

    async def message_edited(self, event):
        """Отправка уведомления о редактировании сообщения клиенту"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_edited",
                    "message_id": event["message_id"],
                    "content": event["content"],
                    "is_edited": event["is_edited"],
                    "edited_at": event["edited_at"],
                }
            )
        )

    @database_sync_to_async
    def edit_general_message(self, message_id, new_content):
        """
        Редактирование сообщения в общем чате.

        Проверяет:
        - Существование сообщения
        - Что сообщение принадлежит общему чату
        - Что пользователь является автором сообщения
        - Что сообщение не удалено

        Возвращает dict с edited_at или error.
        """
        from django.utils import timezone

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return {"error": "Message not found", "code": "not_found"}

        # Проверяем что сообщение принадлежит общему чату
        if message.room.type != ChatRoom.Type.GENERAL:
            logger.debug(f"[edit_general_message] Access denied: message {message_id} does not belong to general chat")
            return {
                "error": "Message does not belong to general chat",
                "code": "access_denied",
            }

        # Проверяем что пользователь является автором
        if message.sender_id != self.scope["user"].id:
            logger.debug(
                f'[edit_general_message] Access denied: user {self.scope["user"].id} is not the sender of message {message_id}'
            )
            return {
                "error": "You can only edit your own messages",
                "code": "access_denied",
            }

        # Проверяем что сообщение не удалено
        if message.is_deleted:
            return {"error": "Cannot edit deleted message", "code": "validation_error"}

        # Обновляем сообщение
        message.content = new_content
        message.is_edited = True
        message.save(update_fields=["content", "is_edited", "updated_at"])

        logger.info(f'[edit_general_message] Message {message_id} edited by user {self.scope["user"].id}')
        return {"edited_at": message.updated_at.isoformat()}

    @database_sync_to_async
    def create_general_message(self, content):
        """Создание нового сообщения в общем чате"""
        try:
            # Получаем или создаем общую комнату
            room, created = ChatRoom.objects.get_or_create(
                type=ChatRoom.Type.GENERAL,
                defaults={
                    "name": "Общий форум",
                    "description": "Общий чат для всех пользователей",
                    "created_by": self.scope["user"],
                },
            )

            message = Message.objects.create(room=room, sender=self.scope["user"], content=content)
            return MessageSerializer(message).data
        except Exception as e:
            logger.error(f"Error creating general message: {e}")
            return None

    async def send_general_chat_history(self):
        """Отправка истории сообщений общего чата"""
        messages = await self.get_general_chat_history()
        await self.send(text_data=json.dumps({"type": "room_history", "messages": messages}))

    @database_sync_to_async
    def get_general_chat_history(self):
        """Получение истории сообщений общего чата"""
        try:
            room = ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).first()
            if not room:
                return []

            messages = room.messages.filter(is_deleted=False).select_related("sender").order_by("-created_at")[:50]
            return [MessageSerializer(msg).data for msg in reversed(messages)]
        except Exception as e:
            logger.error(f"Error getting general chat history: {e}")
            return []

    @database_sync_to_async
    def clear_general_unread_count(self):
        """
        Очистка счётчика непрочитанных сообщений для общего чата.
        Обновляет last_read_at в ChatParticipant на текущее время.
        """
        from django.utils import timezone

        try:
            room = ChatRoom.objects.filter(type=ChatRoom.Type.GENERAL).first()
            if not room:
                return

            user = self.scope["user"]

            # Обновляем или создаём запись ChatParticipant с текущим временем прочтения
            participant, created = ChatParticipant.objects.get_or_create(room=room, user=user)
            participant.last_read_at = timezone.now()
            participant.save(update_fields=["last_read_at"])

            logger.debug(f"[clear_general_unread_count] Cleared unread count for user {user.id} in general chat")
        except Exception as e:
            logger.error(f"[clear_general_unread_count] Error clearing unread count: {e}")


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для уведомлений пользователя
    """

    @database_sync_to_async
    def _validate_token(self, token_key):
        """
        Validate token from query string.
        Returns authenticated user if token is valid, None otherwise.
        """
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            if token.user.is_active:
                return token.user
        except Token.DoesNotExist:
            pass
        return None

    async def _authenticate_token_from_query_string(self):
        """
        Попытается аутентифицировать пользователя через токен в query string.
        Поддерживает форматы:
        - ws://host/ws/notifications/user_id/?token=abc123
        - ws://host/ws/notifications/user_id/?authorization=Bearer%20abc123
        """
        try:
            query_string = self.scope.get("query_string", b"").decode()
            if not query_string:
                return False

            token = None

            if "token=" in query_string:
                token = query_string.split("token=")[1].split("&")[0]
            elif "authorization=" in query_string:
                auth_header = query_string.split("authorization=")[1].split("&")[0]
                if auth_header.startswith("Bearer%20"):
                    token = auth_header[9:]

            if not token:
                return False

            user = await self._validate_token(token)
            if user:
                self.scope["user"] = user
                logger.info(f"[NotificationConsumer] User {user.id} authenticated via token")
                return True

            logger.warning(f"[NotificationConsumer] Token validation failed")
            return False

        except Exception as e:
            logger.error(f"[NotificationConsumer] Token authentication error: {e}")
            return False

    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.notification_group_name = f"notifications_{self.user_id}"

        is_authenticated = self.scope["user"].is_authenticated
        if not is_authenticated:
            is_authenticated = await self._authenticate_token_from_query_string()

        # Проверяем, что пользователь аутентифицирован
        if not is_authenticated:
            await self.close(code=4001)
            return

        # Проверяем, что пользователь запрашивает свои уведомления
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("[NotificationConsumer] User is not authenticated after token validation")
            await self.close(code=4001)
            return

        if str(user.id) != self.user_id:
            await self.close(code=4002)
            return

        # Присоединяемся к группе уведомлений пользователя
        await self.channel_layer.group_add(self.notification_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.notification_group_name, self.channel_name)

    async def receive(self, text_data):
        # Уведомления обычно только отправляются, не принимаются
        pass

    async def notification(self, event):
        """Отправка уведомления клиенту"""
        await self.send(text_data=json.dumps({"type": "notification", "data": event["data"]}))


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для обновлений дашборда пользователя
    """

    @database_sync_to_async
    def _validate_token(self, token_key):
        """
        Validate token from query string.
        Returns authenticated user if token is valid, None otherwise.
        """
        try:
            token = Token.objects.select_related("user").get(key=token_key)
            if token.user.is_active:
                return token.user
        except Token.DoesNotExist:
            pass
        return None

    async def _authenticate_token_from_query_string(self):
        """
        Попытается аутентифицировать пользователя через токен в query string.
        Поддерживает форматы:
        - ws://host/ws/dashboard/user_id/?token=abc123
        - ws://host/ws/dashboard/user_id/?authorization=Bearer%20abc123
        """
        try:
            query_string = self.scope.get("query_string", b"").decode()
            if not query_string:
                return False

            token = None

            if "token=" in query_string:
                token = query_string.split("token=")[1].split("&")[0]
            elif "authorization=" in query_string:
                auth_header = query_string.split("authorization=")[1].split("&")[0]
                if auth_header.startswith("Bearer%20"):
                    token = auth_header[9:]

            if not token:
                return False

            user = await self._validate_token(token)
            if user:
                self.scope["user"] = user
                logger.info(f"[DashboardConsumer] User {user.id} authenticated via token")
                return True

            logger.warning(f"[DashboardConsumer] Token validation failed")
            return False

        except Exception as e:
            logger.error(f"[DashboardConsumer] Token authentication error: {e}")
            return False

    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.dashboard_group_name = f"dashboard_{self.user_id}"

        user = self.scope.get("user")
        if not user:
            logger.warning("[DashboardConsumer] No user object in scope")
            await self.close(code=4001)
            return

        is_authenticated = user.is_authenticated
        if not is_authenticated:
            is_authenticated = await self._authenticate_token_from_query_string()

        # Проверяем, что пользователь аутентифицирован
        if not is_authenticated:
            await self.close(code=4001)
            return

        # Проверяем, что пользователь запрашивает свои обновления
        user = self.scope.get("user")
        if not user:
            logger.warning("[DashboardConsumer] No user object in scope")
            await self.close(code=4001)
            return

        if str(user.id) != self.user_id:
            await self.close(code=4002)
            return

        # Присоединяемся к группе обновлений дашборда пользователя
        await self.channel_layer.group_add(self.dashboard_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.dashboard_group_name, self.channel_name)

    async def receive(self, text_data):
        # Обновления дашборда обычно только отправляются, не принимаются
        pass

    async def dashboard_update(self, event):
        """Отправка обновления дашборда клиенту"""
        await self.send(text_data=json.dumps({"type": "dashboard_update", "data": event["data"]}))
