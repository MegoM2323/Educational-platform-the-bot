"""
Сервис для управления сообщениями в чатах.
"""
import logging
from typing import List, Optional
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from ..models import ChatRoom, Message

logger = logging.getLogger(__name__)
User = get_user_model()


class MessageService:
    """
    Сервис для работы с сообщениями.
    Инкапсулирует бизнес-логику отправки, редактирования и удаления сообщений.
    """

    @staticmethod
    def send_message(user: User, room: ChatRoom, content: str) -> Message:
        """
        Отправить сообщение в чат.

        RACE CONDITION PROTECTION:
        - Базовая проверка: user.is_active, room.is_active (быстрые проверки)
        - CRITICAL CHECK: повторная проверка can_access_chat() перед сохранением
        - Это предотвращает сценарий:
          1. View проверяет can_access_chat() → True
          2. Учитель меняет enrollment на INACTIVE
          3. Но Message.create() уже был вызван
        - С этой проверкой: Message.create() происходит только если access все еще активен

        Args:
            user: Пользователь, отправляющий сообщение
            room: Чат-комната
            content: Содержание сообщения

        Returns:
            Message: Созданное сообщение

        Raises:
            ValueError: Если сообщение пусто, пользователь неактивен или чат неактивен
            PermissionDenied: Если доступ был отозван (enrollment изменился, и т.д.)
        """
        if not user.is_active:
            raise ValueError("User is inactive")

        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")

        if not room.is_active:
            raise ValueError("Chat is inactive")

        # CRITICAL: Double-check permissions AT MESSAGE TIME
        # Prevents race condition between can_access_chat() check (in view)
        # and Message.save() (here). This is essential for security.
        from chat.services.chat_service import ChatService

        if not ChatService.can_access_chat(user, room):
            logger.warning(
                f"User {user.id} tried to send message to {room.id} but access was revoked"
            )
            raise PermissionDenied("Access to chat has been revoked")

        message = Message.objects.create(room=room, sender=user, content=content.strip())

        room.updated_at = timezone.now()
        room.save(update_fields=["updated_at"])

        logger.info(f"Message {message.id} sent by user {user.id} in room {room.id}")
        return message

    @staticmethod
    def get_messages(
        room: ChatRoom, before_id: Optional[int] = None, limit: int = 50
    ) -> List[Message]:
        """
        Получить сообщения из чата с cursor-based пагинацией.

        Args:
            room: Чат-комната
            before_id: ID сообщения, получить сообщения старше него
            limit: Максимальное количество сообщений

        Returns:
            list[Message]: Список сообщений (старые первыми)
        """
        qs = (
            Message.objects.filter(room=room, is_deleted=False)
            .select_related("sender")
            .order_by("-created_at")
        )

        if before_id:
            qs = qs.filter(id__lt=before_id)

        messages = list(qs[:limit])
        messages.reverse()

        return messages

    @staticmethod
    def edit_message(user: User, message: Message, new_content: str) -> Message:
        """
        Редактировать сообщение.

        Args:
            user: Пользователь, пытающийся редактировать
            message: Сообщение
            new_content: Новое содержание

        Returns:
            Message: Обновлённое сообщение

        Raises:
            ValueError: Если пользователь не автор или сообщение удалено
        """
        if message.sender_id != user.id:
            raise ValueError("Only author can edit message")

        if message.is_deleted:
            raise ValueError("Cannot edit deleted message")

        if not new_content or not new_content.strip():
            raise ValueError("Message content cannot be empty")

        message.content = new_content.strip()
        message.is_edited = True
        message.updated_at = timezone.now()
        message.save(update_fields=["content", "is_edited", "updated_at"])

        logger.info(f"Message {message.id} edited by user {user.id}")
        return message

    @staticmethod
    def delete_message(user: User, message: Message) -> None:
        """
        Удалить сообщение (soft delete).

        Args:
            user: Пользователь, пытающийся удалить
            message: Сообщение

        Raises:
            ValueError: Если пользователь не автор и не админ
        """
        is_author = message.sender_id == user.id
        is_admin = getattr(user, "role", None) == "admin"

        if not (is_author or is_admin):
            raise ValueError("Only author or admin can delete message")

        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=["is_deleted", "deleted_at"])

        logger.info(f"Message {message.id} deleted by user {user.id}")
