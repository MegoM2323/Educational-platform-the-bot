"""
Сервис для админской панели чата.
Предоставляет read-only доступ ко всем чат-комнатам и сообщениям.
"""
from django.db.models import Prefetch, Count, Q
from django.contrib.auth import get_user_model
import logging
from ..models import ChatRoom, Message

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminChatService:
    """
    Сервис для управления чатами в админской панели.
    Все методы read-only - никаких модификаций.
    """

    @staticmethod
    def get_all_rooms():
        """
        Получить все чат-комнаты с оптимизированными запросами.

        Оптимизация:
        - prefetch_related('participants') - загрузка всех участников
        - prefetch_related('messages') - последние сообщения
        - select_related('created_by') - создатель комнаты
        - select_related('enrollment__subject') - предмет для forum_subject

        Returns:
            QuerySet[ChatRoom]: Все комнаты с prefetch данными
        """
        return ChatRoom.objects.select_related(
            'created_by',
            'enrollment',
            'enrollment__subject',
            'enrollment__student',
            'enrollment__teacher'
        ).prefetch_related(
            'participants',
            Prefetch(
                'messages',
                queryset=Message.objects.select_related('sender').order_by('-created_at')[:1],
                to_attr='prefetched_last_message'
            )
        ).annotate(
            participants_count=Count('participants', distinct=True),
            messages_count=Count('messages', distinct=True)
        ).order_by('-updated_at')

    @staticmethod
    def get_room_messages(room_id: int, limit: int = 100, offset: int = 0):
        """
        Получить сообщения конкретной комнаты.

        Args:
            room_id (int): ID чат-комнаты
            limit (int): Максимум сообщений (по умолчанию 100)
            offset (int): Смещение для пагинации (по умолчанию 0)

        Returns:
            QuerySet[Message]: Сообщения с prefetch sender

        Raises:
            ChatRoom.DoesNotExist: Если комната не найдена
        """
        # Проверяем существование комнаты
        room = ChatRoom.objects.get(id=room_id)

        messages = Message.objects.filter(
            room=room
        ).select_related(
            'sender',
            'reply_to',
            'reply_to__sender',
            'thread'
        ).prefetch_related(
            'read_by',
            'replies'
        ).order_by('-created_at')[offset:offset + limit]

        return messages

    @staticmethod
    def get_room_by_id(room_id: int):
        """
        Получить конкретную комнату с полными данными.

        Args:
            room_id (int): ID чат-комнаты

        Returns:
            ChatRoom: Комната с prefetch данными

        Raises:
            ChatRoom.DoesNotExist: Если комната не найдена
        """
        return ChatRoom.objects.select_related(
            'created_by',
            'enrollment',
            'enrollment__subject',
            'enrollment__student',
            'enrollment__teacher'
        ).prefetch_related(
            'participants',
            'room_participants',
            'room_participants__user'
        ).annotate(
            participants_count=Count('participants', distinct=True),
            messages_count=Count('messages', distinct=True)
        ).get(id=room_id)

    @staticmethod
    def get_chat_stats():
        """
        Получить общую статистику по чатам для админской панели.

        Returns:
            dict: Статистика
                - total_rooms: Всего комнат
                - active_rooms: Активных комнат
                - total_messages: Всего сообщений
                - forum_subject_rooms: Комнат типа forum_subject
                - direct_rooms: Комнат типа direct
                - group_rooms: Комнат типа group
        """
        total_rooms = ChatRoom.objects.count()
        active_rooms = ChatRoom.objects.filter(is_active=True).count()
        total_messages = Message.objects.count()

        # Статистика по типам комнат
        forum_subject_rooms = ChatRoom.objects.filter(type=ChatRoom.Type.FORUM_SUBJECT).count()
        direct_rooms = ChatRoom.objects.filter(type=ChatRoom.Type.DIRECT).count()
        group_rooms = ChatRoom.objects.filter(type=ChatRoom.Type.GROUP).count()

        return {
            'total_rooms': total_rooms,
            'active_rooms': active_rooms,
            'total_messages': total_messages,
            'forum_subject_rooms': forum_subject_rooms,
            'direct_rooms': direct_rooms,
            'group_rooms': group_rooms,
        }
