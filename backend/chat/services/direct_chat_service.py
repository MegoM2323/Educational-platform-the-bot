"""
Сервис для управления личными (direct) чатами.
"""
import logging
from django.db import transaction
from django.db.models import Count, Subquery, OuterRef
from django.contrib.auth import get_user_model
from ..models import ChatRoom, ChatParticipant

logger = logging.getLogger(__name__)
User = get_user_model()


class DirectChatService:
    """
    Сервис для создания и получения личных чатов между двумя пользователями.
    """

    @staticmethod
    def get_or_create_direct_chat(user1, user2) -> tuple[ChatRoom, bool]:
        """
        Получить существующий или создать новый direct чат между двумя пользователями.

        Args:
            user1: Первый пользователь
            user2: Второй пользователь

        Returns:
            tuple[ChatRoom, bool]: (комната, created)
                - created=True если чат был создан
                - created=False если найден существующий
        """
        if user1.id == user2.id:
            raise ValueError("Cannot create direct chat with yourself")

        existing_room = DirectChatService._find_existing_direct_chat(user1, user2)
        if existing_room:
            return existing_room, False

        with transaction.atomic():
            existing_room = DirectChatService._find_existing_direct_chat(
                user1, user2, for_update=True
            )
            if existing_room:
                return existing_room, False

            room = DirectChatService._create_direct_chat(user1, user2)
            return room, True

    @staticmethod
    def _find_existing_direct_chat(user1, user2, for_update: bool = False) -> ChatRoom | None:
        """
        Найти существующий direct чат между двумя пользователями.

        Args:
            user1: Первый пользователь
            user2: Второй пользователь
            for_update: Если True, использует select_for_update() для блокировки строки
        """
        # Подзапрос для подсчета участников чата
        # Используем Subquery вместо annotate с Count, т.к. двойная фильтрация
        # по ManyToMany полю participants приводит к неверному подсчету
        participant_count_subquery = (
            ChatRoom.objects.filter(id=OuterRef("id"))
            .annotate(cnt=Count("participants"))
            .values("cnt")[:1]
        )

        room_id = (
            ChatRoom.objects.filter(type=ChatRoom.Type.DIRECT, participants=user1, is_active=True)
            .filter(participants=user2)
            .annotate(participant_count=Subquery(participant_count_subquery))
            .filter(participant_count=2)
            .values_list("id", flat=True)
            .first()
        )

        if room_id is None:
            return None

        # Если нужна блокировка, получаем комнату по ID с select_for_update
        if for_update:
            return ChatRoom.objects.select_for_update().get(id=room_id)

        return ChatRoom.objects.get(id=room_id)

    @staticmethod
    def _create_direct_chat(user1, user2) -> ChatRoom:
        """
        Создать новый direct чат.
        """
        user1_name = user1.get_full_name() or user1.email
        user2_name = user2.get_full_name() or user2.email
        room_name = f"{user1_name} - {user2_name}"

        room = ChatRoom.objects.create(
            name=room_name, type=ChatRoom.Type.DIRECT, created_by=user1, is_active=True
        )

        room.participants.add(user1, user2)

        ChatParticipant.objects.bulk_create(
            [
                ChatParticipant(room=room, user=user1, is_admin=True),
                ChatParticipant(room=room, user=user2, is_admin=False),
            ],
            ignore_conflicts=True,
        )

        logger.info(f"Created direct chat {room.id} between users {user1.id} and {user2.id}")

        return room
