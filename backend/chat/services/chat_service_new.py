"""
Сервис для управления чатами (новая архитектура).
Работает с моделями из models.py
"""
import logging
from typing import Tuple, Optional

from django.db import transaction
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import ChatRoom, ChatParticipant

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatServiceNew:
    """
    Сервис для управления чатами (новая архитектура).
    Инкапсулирует бизнес-логику работы с чат-комнатами и участниками.
    """

    @staticmethod
    def get_or_create_chat(user1: User, user2: User) -> Tuple[ChatRoom, bool]:
        """
        Получить существующий или создать новый чат между двумя пользователями.

        Args:
            user1: Первый пользователь
            user2: Второй пользователь

        Returns:
            tuple[ChatRoom, bool]: (room, created)
                - created=True если чат был только что создан
                - created=False если найден существующий

        Raises:
            ValueError: Если user1 == user2 или один из пользователей неактивен
        """
        if user1.id == user2.id:
            raise ValueError("Cannot create direct chat with yourself")

        if not user1.is_active or not user2.is_active:
            raise ValueError("Both users must be active")

        existing_room = ChatServiceNew._find_existing_chat(user1, user2)
        if existing_room:
            logger.debug(
                f"Found existing chat {existing_room.id} for users {user1.id}, {user2.id}"
            )
            return existing_room, False

        with transaction.atomic():
            existing_room = ChatServiceNew._find_existing_chat(
                user1, user2, for_update=True
            )
            if existing_room:
                logger.debug(f"Found existing chat {existing_room.id} after lock")
                return existing_room, False

            room = ChatServiceNew._create_chat(user1, user2)
            logger.info(
                f"Created new chat {room.id} between users {user1.id} and {user2.id}"
            )
            return room, True

    @staticmethod
    def _find_existing_chat(
        user1: User, user2: User, for_update: bool = False
    ) -> Optional[ChatRoom]:
        """
        Найти существующий direct чат между двумя пользователями.

        SQL: SELECT room_id FROM chatparticipant
             WHERE user_id IN (user1.id, user2.id)
             GROUP BY room_id
             HAVING COUNT(DISTINCT user_id) = 2

        Args:
            user1: Первый пользователь
            user2: Второй пользователь
            for_update: Если True, использует select_for_update() для блокировки

        Returns:
            ChatRoom или None
        """
        qs = (
            ChatRoom.objects.filter(participants__user=user1, is_active=True)
            .filter(participants__user=user2)
            .annotate(participant_count=Count("participants", distinct=True))
            .filter(participant_count=2)
        )

        if for_update:
            qs = qs.select_for_update()

        return qs.first()

    @staticmethod
    def _create_chat(user1: User, user2: User) -> ChatRoom:
        """
        Создать новый direct чат в транзакции.

        Операции:
        1. Создание ChatRoom
        2. Создание двух ChatParticipant записей

        Args:
            user1: Первый пользователь
            user2: Второй пользователь

        Returns:
            ChatRoom: Созданная комната
        """
        room = ChatRoom.objects.create(is_active=True)

        ChatParticipant.objects.bulk_create(
            [
                ChatParticipant(room=room, user=user1),
                ChatParticipant(room=room, user=user2),
            ],
            ignore_conflicts=True,
        )

        return room

    @staticmethod
    def get_user_chats(user: User):
        """
        Получить все чаты пользователя.

        Логика:
        1. Если user.role == 'admin' → все активные чаты
        2. Иначе → чаты где user в ChatParticipant

        Сортировка: по updated_at DESC

        Args:
            user: Пользователь

        Returns:
            QuerySet[ChatRoom]: Оптимизированный queryset
        """
        if hasattr(user, "role") and user.role == "admin":
            qs = ChatRoom.objects.filter(is_active=True)
        else:
            qs = ChatRoom.objects.filter(participants__user=user, is_active=True)

        qs = (
            qs.prefetch_related("participants__user", "messages")
            .distinct()
            .order_by("-updated_at")
        )

        return qs

    @staticmethod
    def can_access_chat(user: User, room: ChatRoom) -> bool:
        """
        Проверить может ли пользователь получить доступ к чату.

        Логика:
        1. Если user.role == 'admin' → True (админы видят все)
        2. Если user в ChatParticipant.objects.filter(room=room, user=user) → True
        3. Иначе → False

        Args:
            user: Пользователь
            room: Чат-комната

        Returns:
            bool: True если доступ разрешен
        """
        if hasattr(user, "role") and user.role == "admin":
            logger.debug(f"Admin user {user.id} has access to chat {room.id}")
            return True

        has_access = ChatParticipant.objects.filter(room=room, user=user).exists()

        logger.debug(f"User {user.id} access to chat {room.id}: {has_access}")
        return has_access

    @staticmethod
    def mark_chat_as_read(user: User, room: ChatRoom) -> None:
        """
        Пометить чат как прочитанный для пользователя.

        Обновляет ChatParticipant.last_read_at = now().
        Если ChatParticipant не существует → молча игнорирует.

        Args:
            user: Пользователь
            room: Чат-комната
        """
        try:
            participant = ChatParticipant.objects.get(room=room, user=user)
            participant.last_read_at = timezone.now()
            participant.save(update_fields=["last_read_at"])
            logger.debug(f"Marked chat {room.id} as read for user {user.id}")
        except ChatParticipant.DoesNotExist:
            logger.debug(
                f"No ChatParticipant found for user {user.id} in chat {room.id}"
            )
            pass
