import logging
from typing import Optional

from django.db.models import Q, Prefetch, Count, F, Max, QuerySet
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied

from ..models import ChatRoom, ChatParticipant, Message
from ..permissions import can_initiate_chat, invalidate_permission_cache

User = get_user_model()
logger = logging.getLogger("chat")


class ChatService:
    """Сервис для управления чатами и сообщениями"""

    PERMISSION_CACHE_TTL = 60

    @staticmethod
    def get_user_chats(user, page=1, page_size=20) -> QuerySet:
        """
        Получить все чаты пользователя с аннотациями.

        Args:
            user: User instance
            page: номер страницы (не используется в текущей версии)
            page_size: размер страницы (не используется в текущей версии)

        Returns:
            QuerySet чатов с аннотациями и сортировкой по последнему сообщению
        """
        chats = (
            ChatRoom.objects.filter(participants__user=user, is_active=True)
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(
                        messages__is_deleted=False,
                        messages__created_at__gt=Coalesce(
                            F("participants__last_read_at"), timezone.now()
                        ),
                    )
                    & ~Q(messages__sender=user),
                )
            )
            .prefetch_related(
                Prefetch(
                    "participants",
                    queryset=ChatParticipant.objects.select_related("user").exclude(
                        user=user
                    ),
                ),
                Prefetch(
                    "messages",
                    queryset=Message.objects.filter(is_deleted=False).order_by(
                        "-created_at"
                    )[:1],
                ),
            )
            .order_by("-updated_at")
            .distinct()
        )

        return chats

    @staticmethod
    def can_access_chat(user, chat_room) -> bool:
        """
        Проверить доступ пользователя к чату.

        Args:
            user: User instance
            chat_room: ChatRoom instance

        Returns:
            True если пользователь участник чата, False иначе
        """
        return ChatParticipant.objects.filter(room=chat_room, user=user).exists()

    @staticmethod
    def get_or_create_direct_chat(user1, user2) -> ChatRoom:
        """
        Получить существующий или создать новый direct чат.

        Args:
            user1: инициатор чата
            user2: получатель чата

        Returns:
            ChatRoom instance

        Raises:
            PermissionDenied: если нельзя инициировать чат
        """
        if not can_initiate_chat(user1, user2):
            raise PermissionDenied(
                f"User {user1.id} cannot initiate chat with {user2.id}"
            )

        existing_chat = (
            ChatRoom.objects.filter(
                participants__user__in=[user1, user2], is_active=True
            )
            .annotate(participant_count=Count("participants"))
            .filter(participant_count=2)
            .distinct()
            .first()
        )

        if existing_chat:
            return existing_chat

        chat_room = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat_room, user=user1)
        ChatParticipant.objects.create(room=chat_room, user=user2)

        logger.info(
            f"Created new direct chat {chat_room.id} between {user1.id} and {user2.id}"
        )
        return chat_room

    @staticmethod
    def mark_messages_as_read(user, chat_room) -> None:
        """
        Отметить все сообщения как прочитанные.

        Args:
            user: User instance
            chat_room: ChatRoom instance

        Updates ChatParticipant.last_read_at = now()
        """
        participant, created = ChatParticipant.objects.get_or_create(
            room=chat_room, user=user
        )
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["last_read_at"])

        logger.info(
            f"Marked messages as read for user {user.id} in chat {chat_room.id}"
        )

    @staticmethod
    def get_unread_count(user, chat_room) -> int:
        """
        Получить количество непрочитанных сообщений для пользователя в чате.

        Args:
            user: User instance
            chat_room: ChatRoom instance

        Returns:
            количество непрочитанных сообщений
        """
        try:
            participant = ChatParticipant.objects.get(room=chat_room, user=user)
        except ChatParticipant.DoesNotExist:
            return 0

        if not participant.last_read_at:
            return (
                Message.objects.filter(room=chat_room, is_deleted=False)
                .exclude(sender=user)
                .count()
            )

        return (
            Message.objects.filter(
                room=chat_room,
                is_deleted=False,
                created_at__gt=participant.last_read_at,
            )
            .exclude(sender=user)
            .count()
        )

    @staticmethod
    def get_chat_messages(
        chat_room, limit: int = 50, before_id: Optional[int] = None
    ) -> QuerySet:
        """
        Получить сообщения чата с cursor-based pagination.

        Args:
            chat_room: ChatRoom instance
            limit: количество сообщений
            before_id: ID сообщения (возвращать сообщения ПЕРЕД этим)

        Returns:
            QuerySet сообщений, отсортированных по created_at DESC
        """
        queryset = (
            Message.objects.filter(room=chat_room, is_deleted=False)
            .select_related("sender")
            .order_by("-created_at")
        )

        if before_id:
            try:
                before_message = Message.objects.get(id=before_id)
                queryset = queryset.filter(created_at__lt=before_message.created_at)
            except Message.DoesNotExist:
                pass

        return queryset[:limit]

    @staticmethod
    def create_message(
        user, chat_room, content: str, message_type: str = "text"
    ) -> Message:
        """
        Создать новое сообщение.

        Args:
            user: автор сообщения
            chat_room: ChatRoom instance
            content: текст сообщения
            message_type: тип (text, image, file, system)

        Returns:
            Message instance
        """
        message = Message.objects.create(
            room=chat_room, sender=user, content=content, message_type=message_type
        )

        chat_room.updated_at = timezone.now()
        chat_room.save(update_fields=["updated_at"])

        logger.info(
            f"Created message {message.id} in chat {chat_room.id} by user {user.id}"
        )
        return message

    @staticmethod
    def update_message(user, message: Message) -> Message:
        """
        Отредактировать сообщение (только автор).

        Args:
            user: текущий пользователь
            message: Message instance с новым content

        Returns:
            Message instance

        Raises:
            PermissionDenied: если не автор сообщения
        """
        if message.sender_id != user.id:
            raise PermissionDenied("Only author can edit message")

        message.is_edited = True
        message.save(update_fields=["content", "is_edited", "updated_at"])

        logger.info(f"Edited message {message.id} by user {user.id}")
        return message

    @staticmethod
    def delete_message(user, message: Message) -> Message:
        """
        Удалить сообщение (soft delete, только автор или админ).

        Args:
            user: текущий пользователь
            message: Message instance

        Returns:
            Message instance

        Raises:
            PermissionDenied: если не автор и не админ
        """
        if message.sender_id != user.id and not user.is_staff:
            raise PermissionDenied("Only author or admin can delete message")

        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=["is_deleted", "deleted_at"])

        logger.info(f"Deleted message {message.id} by user {user.id}")
        return message

    @staticmethod
    def invalidate_permission_cache(user1_id: int, user2_id: int) -> None:
        """
        Инвалидировать кэш пермиссий между двумя пользователями.

        Args:
            user1_id: ID первого пользователя
            user2_id: ID второго пользователя
        """
        invalidate_permission_cache(user1_id, user2_id)
