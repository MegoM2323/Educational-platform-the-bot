from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ChatRoom, Message, ChatParticipant
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    MessageSerializer,
)
from .services.chat_service import ChatService
from .services.message_service import MessageService
from .permissions import can_initiate_chat

User = get_user_model()


class ChatRoomViewSet(viewsets.ViewSet):
    """
    ViewSet для управления чат-комнатами.
    Endpoints:
    - GET /api/chat/ - список чатов
    - POST /api/chat/ - создать/получить чат
    - GET /api/chat/{id}/ - детали чата
    - GET /api/chat/{id}/messages/ - сообщения с cursor-based пагинацией
    - POST /api/chat/{id}/messages/ - отправить сообщение
    - PATCH /api/chat/{id}/messages/{msg_id}/ - редактировать сообщение
    - DELETE /api/chat/{id}/messages/{msg_id}/ - удалить сообщение
    - POST /api/chat/{id}/read/ - отметить как прочитанное
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        GET /api/chat/ - список чатов текущего пользователя с пагинацией
        Query params:
        - page (int, default=1)
        - page_size (int, default=20, max=50)
        """
        try:
            page = int(request.query_params.get("page", 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = int(request.query_params.get("page_size", 20))
            page_size = min(page_size, 50)
            if page_size < 1:
                page_size = 20
        except (ValueError, TypeError):
            page_size = 20

        service = ChatService()
        all_chats = service.get_user_chats(request.user)

        total_count = all_chats.count()
        offset = (page - 1) * page_size
        paginated = all_chats[offset : offset + page_size]

        serializer = ChatRoomListSerializer(
            paginated, many=True, context={"request": request}
        )

        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
                "results": serializer.data,
            }
        )

    def create(self, request):
        """
        POST /api/chat/ - создать или получить чат с пользователем
        Request body:
        {
            "recipient_id": 456
        }
        """
        recipient_id = request.data.get("recipient_id")

        if not recipient_id:
            return Response(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "recipient_id required",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            recipient = User.objects.get(id=recipient_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {
                    "error": {
                        "code": "USER_NOT_FOUND",
                        "message": "User not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not can_initiate_chat(request.user, recipient):
            return Response(
                {
                    "error": {
                        "code": "CANNOT_CHAT",
                        "message": "Cannot chat with this user",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        service = ChatService()
        try:
            room, created = service.get_or_create_chat(request.user, recipient)
        except ValueError as e:
            return Response(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": str(e),
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(
            {
                "id": room.id,
                "created": created,
                "other_participant": {
                    "id": recipient.id,
                    "full_name": f"{recipient.first_name} {recipient.last_name}".strip(),
                    "role": getattr(recipient, "role", "user"),
                },
            },
            status=http_status,
        )

    def retrieve(self, request, pk=None):
        """
        GET /api/chat/{id}/ - детали чата с участниками
        """
        try:
            room = ChatRoom.objects.prefetch_related("participants__user").get(id=pk)
        except ChatRoom.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "CHAT_NOT_FOUND",
                        "message": "Chat not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChatService()
        if not service.can_access_chat(request.user, room):
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ChatRoomDetailSerializer(room, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """
        GET /api/chat/{id}/messages/ - сообщения с cursor-based пагинацией
        Query params:
        - before (int, optional) - ID сообщения для получения более старых
        - limit (int, default=50, max=100)
        """
        try:
            room = ChatRoom.objects.get(id=pk)
        except ChatRoom.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "CHAT_NOT_FOUND",
                        "message": "Chat not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChatService()
        if not service.can_access_chat(request.user, room):
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        before_id = None
        try:
            before_param = request.query_params.get("before")
            if before_param:
                before_id = int(before_param)
        except (ValueError, TypeError):
            before_id = None

        try:
            limit = int(request.query_params.get("limit", 50))
            limit = min(limit, 100)
            if limit < 1:
                limit = 50
        except (ValueError, TypeError):
            limit = 50

        qs = Message.objects.filter(room=room, is_deleted=False).select_related(
            "sender"
        )

        if before_id:
            qs = qs.filter(id__lt=before_id)

        messages = list(qs.order_by("-created_at")[:limit])
        messages.reverse()

        oldest_id = messages[0].id if messages else None
        has_more = before_id is not None and len(messages) == limit

        serializer = MessageSerializer(messages, many=True)

        return Response(
            {
                "messages": serializer.data,
                "has_more": has_more,
                "oldest_id": oldest_id,
            }
        )

    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """
        POST /api/chat/{id}/messages/ - отправить сообщение
        Request body:
        {
            "content": "Текст сообщения"
        }
        """
        try:
            room = ChatRoom.objects.get(id=pk)
        except ChatRoom.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "CHAT_NOT_FOUND",
                        "message": "Chat not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChatService()
        if not service.can_access_chat(request.user, room):
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        content = request.data.get("content", "").strip()

        if not content:
            return Response(
                {
                    "error": {
                        "code": "EMPTY_MESSAGE",
                        "message": "Message content cannot be empty",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not room.is_active:
            return Response(
                {
                    "error": {
                        "code": "CHAT_INACTIVE",
                        "message": "Chat is inactive",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        message_service = MessageService()
        try:
            message = message_service.send_message(request.user, room, content)
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_REQUEST", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """
        POST /api/chat/{id}/read/ - отметить чат как прочитанный
        """
        try:
            room = ChatRoom.objects.get(id=pk)
        except ChatRoom.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "CHAT_NOT_FOUND",
                        "message": "Chat not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChatService()
        if not service.can_access_chat(request.user, room):
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        now = timezone.now()
        service.mark_chat_as_read(request.user, room)

        return Response({"last_read_at": now.isoformat()})


class MessageViewSet(viewsets.ViewSet):
    """
    ViewSet для управления сообщениями с path параметрами.
    Endpoints:
    - PATCH /api/chat/{room_id}/messages/{message_id}/ - редактировать сообщение
    - DELETE /api/chat/{room_id}/messages/{message_id}/ - удалить сообщение
    """

    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, room_id=None, pk=None):
        """
        PATCH /api/chat/{room_id}/messages/{message_id}/ - редактировать сообщение
        Request body:
        {
            "content": "Новый текст"
        }
        """
        try:
            room = ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "CHAT_NOT_FOUND",
                        "message": "Chat not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            message = Message.objects.get(id=pk, room=room, is_deleted=False)
        except Message.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "MESSAGE_NOT_FOUND",
                        "message": "Message not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChatService()
        if not service.can_access_chat(request.user, room):
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if message.sender_id != request.user.id:
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Only author can edit message",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        content = request.data.get("content", "").strip()

        if not content:
            return Response(
                {
                    "error": {
                        "code": "EMPTY_MESSAGE",
                        "message": "Message content cannot be empty",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        message_service = MessageService()
        try:
            message = message_service.edit_message(request.user, message, content)
        except PermissionError as e:
            return Response(
                {"error": {"code": "ACCESS_DENIED", "message": str(e)}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as e:
            return Response(
                {"error": {"code": "INVALID_REQUEST", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Broadcast to WebSocket group
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"chat_{message.room_id}",
                {
                    "type": "chat_message_edited",
                    "message_id": message.id,
                    "content": message.content,
                    "updated_at": message.updated_at.isoformat(),
                },
            )

        serializer = MessageSerializer(message)
        return Response(serializer.data)

    def destroy(self, request, room_id=None, pk=None):
        """
        DELETE /api/chat/{room_id}/messages/{message_id}/ - удалить сообщение (soft delete)
        """
        try:
            room = ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "CHAT_NOT_FOUND",
                        "message": "Chat not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            message = Message.objects.get(id=pk, room=room, is_deleted=False)
        except Message.DoesNotExist:
            return Response(
                {
                    "error": {
                        "code": "MESSAGE_NOT_FOUND",
                        "message": "Message not found",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        service = ChatService()
        if not service.can_access_chat(request.user, room):
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        message_service = MessageService()
        try:
            # Store room_id and message_id before deletion
            room_id = message.room_id
            message_id = message.id

            message_service.delete_message(request.user, message)

            # Broadcast to WebSocket group
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"chat_{room_id}",
                    {
                        "type": "chat_message_deleted",
                        "message_id": message_id,
                    },
                )
        except (PermissionError, ValueError) as e:
            return Response(
                {"error": {"code": "ACCESS_DENIED", "message": str(e)}},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatContactsView(APIView):
    """
    GET /api/chat/contacts/ - список доступных контактов для создания чата
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Возвращает список пользователей, с которыми текущий пользователь может общаться.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            service = ChatService()
            contacts = service.get_contacts(request.user)
            return Response(contacts)
        except Exception as e:
            logger.error(f"ChatContactsView error: {str(e)}")
            return Response(
                {"error": {"code": "ERROR", "message": "Failed to load contacts"}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get unread chat notifications count"""
        from django.db.models import Subquery

        user = request.user

        # Get participant record to access last_read_at
        unread_messages = 0
        unread_threads = 0

        # Get all chat rooms where user is participant
        user_participants = ChatParticipant.objects.filter(user=user).select_related('room')

        for participant in user_participants:
            room = participant.room
            # Count messages created after last_read_at that are not from the user
            query = Message.objects.filter(
                room=room,
                is_deleted=False
            ).exclude(
                sender=user
            )

            if participant.last_read_at:
                # Only count messages created AFTER last_read_at
                query = query.filter(created_at__gt=participant.last_read_at)

            unread_in_chat = query.count()
            if unread_in_chat > 0:
                unread_messages += unread_in_chat
                unread_threads += 1

        has_new_messages = unread_messages > 0

        return Response({
            'unread_messages': unread_messages,
            'unread_threads': unread_threads,
            'has_new_messages': has_new_messages,
        })
