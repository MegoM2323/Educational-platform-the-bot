"""
Основной сервис для управления чатами.
Предоставляет методы для получения, создания и управления чат-комнатами.
"""
import logging
from typing import Tuple, Optional

from django.db import transaction, models
from django.db.models import (
    Count,
    Q,
    OuterRef,
    Subquery,
    Prefetch,
    Max,
    IntegerField,
    Case,
    When,
    Value,
    F,
)
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import ChatRoom, ChatParticipant, Message

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatService:
    """
    Сервис для управления чатами.
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

        existing_room = ChatService._find_existing_chat(user1, user2)
        if existing_room:
            logger.debug(f"Found existing chat {existing_room.id} for users {user1.id}, {user2.id}")
            return existing_room, False

        with transaction.atomic():
            existing_room = ChatService._find_existing_chat(user1, user2, for_update=True)
            if existing_room:
                logger.debug(f"Found existing chat {existing_room.id} after lock")
                return existing_room, False

            room = ChatService._create_chat(user1, user2)
            logger.info(f"Created new chat {room.id} between users {user1.id} and {user2.id}")
            return room, True

    @staticmethod
    def _find_existing_chat(user1: User, user2: User, for_update: bool = False) -> Optional[ChatRoom]:
        """
        Найти существующий direct чат между двумя пользователями.

        Логика:
        1. Оба пользователя в ChatParticipant
        2. Проверка что ровно 2 участника (SQL: COUNT(DISTINCT user_id) = 2)
        3. Фильтр по is_active=True

        Args:
            user1: Первый пользователь
            user2: Второй пользователь
            for_update: Если True, использует select_for_update() для блокировки

        Returns:
            ChatRoom или None
        """
        participant_count_subquery = (
            ChatRoom.objects.filter(id=OuterRef("id"))
            .annotate(cnt=Count("participants", distinct=True))
            .values("cnt")[:1]
        )

        qs = (
            ChatRoom.objects.filter(participants__user=user1, is_active=True)
            .filter(participants__user=user2)
            .annotate(participant_count=Subquery(participant_count_subquery))
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
        1. Создание ChatRoom (только is_active)
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
        Получить все чаты пользователя с дополнительной информацией.

        Логика:
        1. Если user.role == 'admin' → все активные чаты
        2. Иначе → чаты где user в ChatParticipant

        Аннотации для каждого чата:
        - last_message: последнее неудалённое сообщение (содержит content для превью)
        - unread_count: кол-во непрочитанных сообщений
        - other_participant: User объект собеседника (для direct чатов)

        Сортировка: по updated_at DESC

        ВАЖНО: Пагинация должна делаться на уровне View через QuerySet slicing,
        а не в сервисе. Это позволяет правильно обрабатывать count() и offset.

        Args:
            user: Пользователь

        Returns:
            QuerySet[ChatRoom]: Оптимизированный queryset с аннотациями (БЕЗ слайсинга)
        """
        if hasattr(user, "role") and user.role == "admin":
            base_qs = ChatRoom.objects.filter(is_active=True)
        else:
            base_qs = ChatRoom.objects.filter(participants__user=user, is_active=True)

        last_message_subquery = (
            Message.objects.filter(room=OuterRef("id"), is_deleted=False).order_by("-created_at").values("content")[:1]
        )

        last_message_time_subquery = (
            Message.objects.filter(room=OuterRef("id"), is_deleted=False)
            .order_by("-created_at")
            .values("created_at")[:1]
        )

        participant_last_read_subquery = ChatParticipant.objects.filter(room=OuterRef("id"), user=user).values(
            "last_read_at"
        )[:1]

        is_admin = hasattr(user, "role") and user.role == "admin"

        if is_admin:
            unread_count_subquery = (
                Message.objects.filter(
                    room=OuterRef("id"),
                    is_deleted=False,
                )
                .exclude(sender=user)
                .values("room")
                .annotate(count=Count("id"))
                .values("count")
            )
        else:
            unread_count_subquery = (
                Message.objects.filter(
                    room=OuterRef("id"),
                    is_deleted=False,
                    created_at__gt=Subquery(participant_last_read_subquery),
                )
                .exclude(sender=user)
                .values("room")
                .annotate(count=Count("id"))
                .values("count")
            )

        qs = (
            base_qs.annotate(
                last_message_content=Subquery(last_message_subquery),
                last_message_time=Subquery(last_message_time_subquery),
                unread_count=Subquery(unread_count_subquery, output_field=IntegerField()),
            )
            .prefetch_related("participants__user")
            .distinct()
            .order_by("-updated_at")
        )

        return qs

    @staticmethod
    def can_access_chat(user: User, room: ChatRoom) -> bool:
        """
        Проверить может ли пользователь получить доступ к чату.

        Логика:
        1. Если user.is_active == False → False (неактивные пользователи не имеют доступа)
        2. Если user.role == 'admin' → True (админы видят все)
        3. Если user в ChatParticipant.objects.filter(room=room, user=user) → True
        4. Иначе → False

        Args:
            user: Пользователь
            room: Чат-комната

        Returns:
            bool: True если доступ разрешен
        """
        if not user.is_active:
            logger.debug(f"Inactive user {user.id} denied access to chat {room.id}")
            return False

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
            logger.debug(f"No ChatParticipant found for user {user.id} in chat {room.id}")
            pass

    @staticmethod
    def get_contacts(user):
        """
        Получить список пользователей, с которыми может общаться current user.

        Использует can_initiate_chat() из permissions для проверки прав.

        Returns:
            list[dict]: Список контактов с полями:
                - id, full_name, role
                - has_existing_chat, existing_chat_id
        """
        from chat.permissions import can_initiate_chat

        User = get_user_model()
        all_users = User.objects.filter(is_active=True).exclude(id=user.id)

        my_rooms = ChatParticipant.objects.filter(user=user).values_list("room_id", flat=True)
        existing_chats = {}

        for cp in ChatParticipant.objects.filter(
            user_id__in=all_users.values_list("id", flat=True), room_id__in=my_rooms
        ).select_related("room"):
            if cp.user_id not in existing_chats:
                existing_chats[cp.user_id] = cp.room_id

        contacts = []
        for other_user in all_users:
            if can_initiate_chat(user, other_user):
                contacts.append(
                    {
                        "id": other_user.id,
                        "full_name": f"{other_user.first_name} {other_user.last_name}".strip(),
                        "role": getattr(other_user, "role", "user"),
                        "has_existing_chat": other_user.id in existing_chats,
                        "existing_chat_id": existing_chats.get(other_user.id),
                    }
                )

        return contacts
