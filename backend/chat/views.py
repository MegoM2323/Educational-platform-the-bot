import logging
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count
from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import ChatRoom, Message, ChatParticipant
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    MessageSerializer,
)
from .services.chat_service import ChatService
from .permissions import can_initiate_chat

User = get_user_model()


class ChatListCreateView(APIView):
    """
    GET: Получить список всех чатов текущего пользователя
    POST: Создать новый прямой чат
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        GET /api/chat/ - список чатов пользователя

        Query params:
        - page: номер страницы (default: 1)
        - page_size: размер страницы (default: 20)

        Returns: список чатов с аннотациями (last_message, unread_count)
        """
        user = request.user

        # Получить чаты используя ChatService
        chats = ChatService.get_user_chats(user)

        # Пагинация
        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get("page_size", 20)
        page = paginator.paginate_queryset(chats, request)

        if page is not None:
            serializer = ChatRoomListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ChatRoomListSerializer(chats, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        POST /api/chat/ - создать новый direct чат

        Body:
        {
            "recipient_id": 123
        }

        Returns: созданный ChatRoom или existing если уже есть
        """
        user = request.user
        recipient_id = request.data.get("recipient_id")

        if not recipient_id:
            raise ValidationError({"recipient_id": "This field is required"})

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            raise ValidationError({"recipient_id": "User not found"})

        # Проверить права
        if not can_initiate_chat(user, recipient):
            raise PermissionDenied(
                f"You cannot initiate chat with this user. "
                f"Check enrollment status, tutor assignments, etc."
            )

        # Получить или создать чат
        try:
            chat_room = ChatService.get_or_create_direct_chat(user, recipient)
        except PermissionDenied:
            raise PermissionDenied("Cannot create chat with this user")

        serializer = ChatRoomListSerializer(chat_room)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatDetailDeleteView(APIView):
    """
    GET: Получить детали чата (все участники)
    DELETE: Удалить чат (soft delete - is_active=False)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_chat_or_404(self, pk, user):
        """Helper для получения чата с проверкой доступа"""
        try:
            chat = ChatRoom.objects.get(id=pk, is_active=True)
        except ChatRoom.DoesNotExist:
            raise ValidationError({"detail": "Chat not found"})

        # Проверить доступ
        if not ChatService.can_access_chat(user, chat):
            raise PermissionDenied("You do not have access to this chat")

        return chat

    def get(self, request, pk):
        """
        GET /api/chat/<id>/ - детали чата

        Returns: чат с информацией об всех участниках
        """
        chat = self.get_chat_or_404(pk, request.user)

        serializer = ChatRoomDetailSerializer(chat)
        return Response(serializer.data)

    def delete(self, request, pk):
        """
        DELETE /api/chat/<id>/ - удалить чат (soft delete)

        Только создатель или админ могут удалить чат
        """
        chat = self.get_chat_or_404(pk, request.user)

        # Мягкое удаление
        chat.is_active = False
        chat.save(update_fields=["is_active"])

        logger = logging.getLogger("chat")
        logger.info(f"Chat {chat.id} soft-deleted by user {request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageListCreateView(APIView):
    """
    GET: Получить список сообщений чата
    POST: Отправить новое сообщение в чат
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_chat_or_404(self, room_id, user):
        """Helper для получения чата с проверкой доступа"""
        try:
            chat = ChatRoom.objects.get(id=room_id, is_active=True)
        except ChatRoom.DoesNotExist:
            raise ValidationError({"detail": "Chat not found"})

        if not ChatService.can_access_chat(user, chat):
            raise PermissionDenied("You do not have access to this chat")

        return chat

    def get(self, request, room_id):
        """
        GET /api/chat/<room_id>/messages/ - список сообщений

        Query params:
        - limit: количество сообщений (default: 50)
        - before_id: ID сообщения для cursor-based pagination

        Returns: список сообщений (новые первыми, sorted old-to-new)
        """
        chat = self.get_chat_or_404(room_id, request.user)

        limit = int(request.query_params.get("limit", 50))
        before_id = request.query_params.get("before_id")

        messages = ChatService.get_chat_messages(chat, limit=limit, before_id=before_id)

        # Отсортировать по created_at (старые первыми)
        messages = list(reversed(messages))

        serializer = MessageSerializer(messages, many=True)
        return Response(
            {"count": chat.messages.filter(is_deleted=False).count(), "results": serializer.data}
        )

    def post(self, request, room_id):
        """
        POST /api/chat/<room_id>/send_message/ - отправить сообщение

        Body:
        {
            "content": "Hello there!"
        }

        Returns: созданное сообщение
        """
        chat = self.get_chat_or_404(room_id, request.user)
        user = request.user

        content = request.data.get("content", "").strip()

        if not content:
            raise ValidationError({"content": "Message content cannot be empty"})

        if len(content) > 10000:
            raise ValidationError({"content": "Message is too long (max 10000 chars)"})

        # Создать сообщение
        message = ChatService.create_message(user, chat, content, message_type="text")

        logger = logging.getLogger("chat")
        logger.info(f"Message {message.id} created by user {user.id} in chat {chat.id}")

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageDetailView(APIView):
    """
    PATCH: Редактировать сообщение (только автор)
    DELETE: Удалить сообщение (soft delete)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_message_or_404(self, room_id, message_id, user):
        """Helper для получения сообщения с проверками"""
        try:
            chat = ChatRoom.objects.get(id=room_id, is_active=True)
        except ChatRoom.DoesNotExist:
            raise ValidationError({"detail": "Chat not found"})

        if not ChatService.can_access_chat(user, chat):
            raise PermissionDenied("You do not have access to this chat")

        try:
            message = Message.objects.get(id=message_id, room=chat)
        except Message.DoesNotExist:
            raise ValidationError({"detail": "Message not found"})

        return message, chat

    def patch(self, request, room_id, message_id):
        """
        PATCH /api/chat/<room_id>/messages/<message_id>/ - редактировать сообщение

        Body:
        {
            "content": "Updated message text"
        }

        Только автор может редактировать
        """
        message, chat = self.get_message_or_404(room_id, message_id, request.user)

        if message.sender_id != request.user.id:
            raise PermissionDenied("You can only edit your own messages")

        content = request.data.get("content", "").strip()

        if not content:
            raise ValidationError({"content": "Message content cannot be empty"})

        if len(content) > 10000:
            raise ValidationError({"content": "Message is too long (max 10000 chars)"})

        message.content = content
        message = ChatService.update_message(request.user, message)

        logger = logging.getLogger("chat")
        logger.info(f"Message {message.id} edited by user {request.user.id}")

        serializer = MessageSerializer(message)
        return Response(serializer.data)

    def delete(self, request, room_id, message_id):
        """
        DELETE /api/chat/<room_id>/messages/<message_id>/ - удалить сообщение (soft delete)

        Только автор или админ могут удалить
        """
        message, chat = self.get_message_or_404(room_id, message_id, request.user)

        if message.sender_id != request.user.id and not request.user.is_staff:
            raise PermissionDenied("You can only delete your own messages")

        message = ChatService.delete_message(request.user, message)

        logger = logging.getLogger("chat")
        logger.info(f"Message {message.id} deleted by user {request.user.id}")

        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkAsReadView(APIView):
    """
    POST: Отметить все сообщения в чате как прочитанные
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        """
        POST /api/chat/<room_id>/mark_as_read/ - отметить как прочитанные

        Updates ChatParticipant.last_read_at = now()

        Returns: количество непрочитанных сообщений (должно быть 0)
        """
        user = request.user

        try:
            chat = ChatRoom.objects.get(id=room_id, is_active=True)
        except ChatRoom.DoesNotExist:
            raise ValidationError({"detail": "Chat not found"})

        if not ChatService.can_access_chat(user, chat):
            raise PermissionDenied("You do not have access to this chat")

        # Отметить как прочитанные
        ChatService.mark_messages_as_read(user, chat)

        unread_count = ChatService.get_unread_count(user, chat)

        logger = logging.getLogger("chat")
        logger.info(f"Marked messages as read for user {user.id} in chat {chat.id}")

        return Response({"chat_id": chat.id, "unread_count": unread_count})


class ContactsListView(APIView):
    """
    GET: Получить список доступных контактов для чата

    Возвращает всех пользователей, с которыми текущий пользователь
    может инициировать чат (по матрице доступа)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        GET /api/chat/contacts/ - список доступных контактов

        Returns: список контактов с информацией (id, name, role, has_existing_chat, chat_id)
        """
        user = request.user

        # Получить всех пользователей кроме текущего
        all_users = User.objects.exclude(id=user.id)

        contacts = []

        for contact in all_users:
            # Проверить можно ли инициировать чат
            if can_initiate_chat(user, contact):
                # Проверить есть ли existing чат
                existing_chat = (
                    ChatRoom.objects.filter(
                        participants__user__in=[user, contact],
                        is_active=True,
                    )
                    .annotate(participant_count=Count("participants"))
                    .filter(participant_count=2)
                    .first()
                )

                contact_data = {
                    "id": contact.id,
                    "full_name": contact.get_full_name() or contact.username,
                    "role": getattr(contact, "role", "unknown"),
                    "has_existing_chat": existing_chat is not None,
                    "chat_id": existing_chat.id if existing_chat else None,
                }
                contacts.append(contact_data)

        # Сортировать по имени
        contacts.sort(key=lambda x: x["full_name"])

        logger = logging.getLogger("chat")
        logger.info(
            f"User {user.id} requested contacts list - found {len(contacts)} available"
        )

        return Response({"count": len(contacts), "results": contacts})
