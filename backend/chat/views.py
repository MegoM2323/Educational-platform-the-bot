from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ChatRoom, Message, ChatParticipant
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    MessageSerializer,
)
from .services.chat_service import ChatService
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
        except User.DoesNotExist:
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

        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=content,
        )
        room.updated_at = timezone.now()
        room.save(update_fields=["updated_at"])

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
            message = Message.objects.get(id=pk, room=room)
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

        if message.is_deleted:
            return Response(
                {
                    "error": {
                        "code": "MESSAGE_DELETED",
                        "message": "Cannot edit deleted message",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
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

        message.content = content
        message.is_edited = True
        message.updated_at = timezone.now()
        message.save(update_fields=["content", "is_edited", "updated_at"])

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
            message = Message.objects.get(id=pk, room=room)
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

        can_delete = (
            message.sender_id == request.user.id
            or getattr(request.user, "role", None) == "admin"
        )

        if not can_delete:
            return Response(
                {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Only author or admin can delete message",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=["is_deleted", "deleted_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatContactsView(APIView):
    """
    GET /api/chat/contacts/ - список доступных контактов для создания чата
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Возвращает список пользователей, с которыми текущий пользователь может общаться.
        Проверяется через can_initiate_chat().
        """
        all_users = User.objects.filter(is_active=True).exclude(id=request.user.id)

        if not all_users.exists():
            return Response({"contacts": []})

        user_ids = list(all_users.values_list("id", flat=True))

        existing_chats = {}
        for cp in (
            ChatParticipant.objects.filter(
                room__participants__user=request.user, user_id__in=user_ids
            )
            .select_related("room")
            .distinct()
        ):
            if cp.user_id not in existing_chats:
                existing_chats[cp.user_id] = cp.room_id

        contacts = []
        for user in all_users:
            if can_initiate_chat(request.user, user):
                contacts.append(
                    {
                        "id": user.id,
                        "full_name": f"{user.first_name} {user.last_name}".strip(),
                        "role": getattr(user, "role", "user"),
                        "has_existing_chat": user.id in existing_chats,
                        "existing_chat_id": existing_chats.get(user.id),
                    }
                )

        return Response({"contacts": contacts})
