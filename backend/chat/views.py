import logging
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db import models as db_models
from django.db.models import Q, Count, Prefetch, Sum
from django.utils import timezone

from .models import ChatRoom, Message, MessageRead, ChatParticipant, MessageThread
from .serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    ChatRoomCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageReadSerializer,
    ChatParticipantSerializer,
    ChatRoomStatsSerializer,
    MessageThreadSerializer,
    MessageThreadCreateSerializer,
)
from .permissions import IsMessageAuthor, CanModerateChat, IsParticipantPermission, CanDeleteMessage
from .general_chat_service import GeneralChatService


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet для чат-комнат
    """

    queryset = ChatRoom.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ChatRoomListSerializer
        elif self.action == "create":
            return ChatRoomCreateSerializer
        return ChatRoomDetailSerializer

    def get_queryset(self):
        """
        Пользователи видят только чаты, в которых они участвуют
        """
        user = self.request.user
        queryset = ChatRoom.objects.filter(participants=user)

        if self.action == "list":
            queryset = queryset.select_related("enrollment__subject").prefetch_related(
                "participants"
            )
        elif self.action in ["retrieve"]:
            queryset = queryset.select_related("enrollment__subject").prefetch_related(
                "participants"
            )

        return queryset

    def perform_create(self, serializer):
        # Wrap in transaction to ensure room creation and participant addition are atomic
        with transaction.atomic():
            room = serializer.save()
            # Добавляем создателя в участники
            room.participants.add(self.request.user)
            # Create ChatParticipant record for consistency
            ChatParticipant.objects.get_or_create(room=room, user=self.request.user)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """
        Присоединиться к чату
        """
        room = self.get_object()
        user = request.user

        if room.participants.filter(id=user.id).exists():
            return Response(
                {"error": "Вы уже участвуете в этом чате"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        room.participants.add(user)
        return Response({"message": "Вы присоединились к чату"})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        """
        Покинуть чат
        """
        room = self.get_object()
        user = request.user

        if not room.participants.filter(id=user.id).exists():
            return Response(
                {"error": "Вы не участвуете в этом чате"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        room.participants.remove(user)

        # Remove ChatParticipant record
        ChatParticipant.objects.filter(room=room, user=user).delete()

        return Response({"message": "Вы покинули чат"})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """
        Отметить все сообщения в чате как прочитанные
        """
        room = self.get_object()
        user = request.user

        messages = Message.objects.filter(room=room, is_deleted=False)
        for message in messages:
            MessageRead.objects.get_or_create(message=message, user=user)

        return Response({"message": "Все сообщения отмечены как прочитанные"})

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Получить статистику по чатам
        """
        logger = logging.getLogger(__name__)

        try:
            user = request.user
            total_rooms = ChatRoom.objects.filter(participants=user).count()
            active_rooms = ChatRoom.objects.filter(
                participants=user, is_active=True
            ).count()

            user_rooms = ChatRoom.objects.filter(participants=user)
            total_messages = Message.objects.filter(room__in=user_rooms).count()

            # Use aggregate instead of iteration to prevent N+1
            unread_messages = (
                ChatParticipant.with_unread_count()
                .filter(room__in=user_rooms, user=user)
                .aggregate(total=Sum("_annotated_unread_count"))["total"]
                or 0
            )

            participants_count = (
                ChatRoom.objects.filter(participants=user)
                .annotate(p_count=Count("participants"))
                .aggregate(total=Sum("p_count"))["total"]
                or 0
            )

            stats_data = {
                "total_rooms": total_rooms,
                "active_rooms": active_rooms,
                "total_messages": total_messages,
                "unread_messages": unread_messages,
                "participants_count": participants_count,
            }

            serializer = ChatRoomStatsSerializer(stats_data)
            return Response(serializer.data)
        except Exception as logger:
            logger.error(f"Error: {e}")
            return Response(
                {"error": "Ошибка при получении статистики"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """
        Архивировать чат-комнату
        """
        room = self.get_object()
        room.is_active = False
        room.save()
        serializer = self.get_serializer(room)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet для сообщений
    """

    queryset = Message.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["room", "sender", "message_type"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return MessageUpdateSerializer
        elif self.action == "create":
            return MessageCreateSerializer
        return MessageSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [permissions.IsAuthenticated(), IsMessageAuthor()]
        if self.action == "destroy":
            return [permissions.IsAuthenticated(), CanDeleteMessage()]
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsParticipantPermission()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """
        Пользователи видят только сообщения из чатов, в которых они участвуют.
        Удалённые сообщения (soft delete) исключаются из выборки.

        Оптимизация N+1 queries:
        - select_related для sender, thread, reply_to
        - prefetch_related для replies, read_by
        - annotate для replies_count
        """
        user = self.request.user
        user_rooms = ChatRoom.objects.filter(participants=user)
        return (
            Message.objects.filter(room__in=user_rooms, is_deleted=False)
            .select_related("sender", "thread", "reply_to__sender")
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=Message.objects.filter(is_deleted=False).only(
                        "id", "is_deleted"
                    ),
                ),
                "read_by",
            )
            .annotate(
                annotated_replies_count=Count(
                    "replies", filter=Q(replies__is_deleted=False)
                )
            )
        )

    def perform_create(self, serializer):
        logger = logging.getLogger(__name__)
        try:
            room_id = self.request.data.get("room")
            if not room_id:
                raise PermissionDenied("room ID is required")

            room = ChatRoom.objects.get(id=room_id)
            user = self.request.user

            if not room.participants.filter(id=user.id).exists():
                logger.warning(
                    f"[MessageViewSet.perform_create] IDOR attempt: "
                    f"User {user.id} tried to create message in room {room.id} "
                    f"where they are not a participant"
                )
                raise PermissionDenied("Вы не участник этой комнаты")

            serializer.save(sender=user)
            logger.info(
                f"[MessageViewSet.perform_create] Message created by user {user.id} "
                f"in room {room.id}"
            )
        except ChatRoom.DoesNotExist:
            logger.error(f"[MessageViewSet.perform_create] Room {room_id} not found")
            raise PermissionDenied("Комната не найдена")
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"[MessageViewSet.perform_create] Unexpected error: {str(e)}")
            raise

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """
        Отметить сообщение как прочитанное
        """
        message = self.get_object()
        MessageRead.objects.get_or_create(message=message, user=request.user)
        return Response({"message": "Сообщение отмечено как прочитанное"})

    @action(detail=True, methods=["post"])
    def react(self, request, pk=None):
        """
        Добавить реакцию на сообщение (emoji)
        """
        message = self.get_object()
        emoji = request.data.get("emoji")

        if not emoji:
            return Response(
                {"error": "emoji is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not hasattr(message, "reactions"):
            message.reactions = {}
        if not isinstance(message.reactions, dict):
            message.reactions = {}

        user_id_str = str(request.user.id)
        if emoji not in message.reactions:
            message.reactions[emoji] = []

        if user_id_str not in message.reactions[emoji]:
            message.reactions[emoji].append(user_id_str)

        message.save()
        return Response(message.reactions)


class ChatParticipantViewSet(viewsets.ModelViewSet):
    """
    ViewSet для участников чата
    """

    queryset = ChatParticipant.objects.all()
    serializer_class = ChatParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["room", "user", "is_muted", "is_admin"]
    ordering_fields = ["joined_at", "last_read_at"]
    ordering = ["-joined_at"]

    def get_queryset(self):
        """
        Пользователи видят только участников чатов, в которых они участвуют.
        Используем with_unread_count() для аннотации unread_count.
        """
        user = self.request.user
        user_rooms = ChatRoom.objects.filter(participants=user)
        return ChatParticipant.with_unread_count().filter(room__in=user_rooms)

    @action(detail=True, methods=["post"])
    def mute(self, request, pk=None):
        """Заблокировать отправку сообщений участнику"""
        participant = self.get_object()

        # Check moderation permission
        if not CanModerateChat().has_object_permission(request, self, participant):
            return Response(
                {"error": "Недостаточно прав для модерации"},
                status=status.HTTP_403_FORBIDDEN,
            )

        participant.is_muted = True
        participant.save(update_fields=["is_muted"])

        return Response(
            {
                "success": True,
                "message": f"Пользователь {participant.user.get_full_name()} заглушен",
            }
        )

    @action(detail=True, methods=["post"])
    def unmute(self, request, pk=None):
        """Разблокировать отправку сообщений участнику"""
        participant = self.get_object()

        if not CanModerateChat().has_object_permission(request, self, participant):
            return Response(
                {"error": "Недостаточно прав для модерации"},
                status=status.HTTP_403_FORBIDDEN,
            )

        participant.is_muted = False
        participant.save(update_fields=["is_muted"])

        return Response(
            {
                "success": True,
                "message": f"Пользователь {participant.user.get_full_name()} разглушен",
            }
        )

    @action(detail=True, methods=["post"])
    def set_admin(self, request, pk=None):
        """Назначить/снять права администратора чата"""
        participant = self.get_object()

        # Only staff/superuser or room admin can set admin
        if not (request.user.is_staff or request.user.is_superuser):
            try:
                requester_participant = ChatParticipant.objects.get(
                    room=participant.room, user=request.user
                )
                if not requester_participant.is_admin:
                    return Response(
                        {"error": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN
                    )
            except ChatParticipant.DoesNotExist:
                return Response(
                    {"error": "Вы не участник чата"}, status=status.HTTP_403_FORBIDDEN
                )

        is_admin = request.data.get("is_admin", False)
        participant.is_admin = is_admin
        participant.save(update_fields=["is_admin"])

        action_text = (
            "назначен администратором" if is_admin else "снят с администратора"
        )
        return Response(
            {
                "success": True,
                "message": f"Пользователь {participant.user.get_full_name()} {action_text}",
            }
        )


class GeneralChatViewSet(viewsets.ViewSet):
    """
    ViewSet для общего чата-форума
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def general(self, request):
        """
        Получить основной форум и темы
        """
        # Logic for getting general chat/forum
        return Response({"message": "Основной форум"})


class MessageThreadViewSet(viewsets.ModelViewSet):
    """
    ViewSet для тредов сообщений в форуме
    """

    queryset = MessageThread.objects.all()
    serializer_class = MessageThreadSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["room", "is_pinned", "is_locked"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "reply_count"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return MessageThreadCreateSerializer
        return MessageThreadSerializer

    def get_queryset(self):
        """
        Пользователи видят только треды в чатах, в которых они участвуют
        """
        user = self.request.user
        user_rooms = ChatRoom.objects.filter(participants=user)
        return (
            MessageThread.objects.filter(room__in=user_rooms)
            .select_related("room", "created_by")
            .prefetch_related("messages")
            .annotate(
                annotated_reply_count=Count(
                    "messages", filter=Q(messages__is_deleted=False)
                )
            )
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def pin(self, request, pk=None):
        """
        Закрепить тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.pin_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={"request": request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def unpin(self, request, pk=None):
        """
        Открепить тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.unpin_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={"request": request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        """
        Заблокировать тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.lock_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={"request": request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        """
        Разблокировать тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.unlock_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={"request": request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from rest_framework.views import APIView


class ParentChatView(APIView):
    """
    ViewSet для родительского чата - список сообщений и создание сообщений.

    GET /api/chat/ - список сообщений родителя
    POST /api/chat/ - отправить сообщение
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Получить список сообщений родителя"""
        user = request.user

        # Фильтр по пользователю (получателю/отправителю)
        user_filter = request.query_params.get("user_id")

        # Пагинация
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        # Получаем сообщения где текущий пользователь отправитель или получатель
        queryset = (
            Message.objects.filter(
                Q(sender=user) | Q(room__participants=user), is_deleted=False
            )
            .select_related("sender", "room")
            .order_by("-created_at")
        )

        if user_filter:
            queryset = queryset.filter(Q(sender_id=user_filter) | Q(sender=user))

        # Применяем пагинацию
        from django.core.paginator import Paginator

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = MessageSerializer(
            page_obj.object_list, many=True, context={"request": request}
        )

        return Response(
            {
                "results": serializer.data,
                "count": paginator.count,
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
            }
        )

    def post(self, request):
        """Создать новое сообщение"""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        recipient_id = request.data.get("recipient_id")
        message_text = request.data.get("message")

        if not message_text:
            return Response(
                {"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not recipient_id:
            return Response(
                {"error": "recipient_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Recipient not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Получаем или создаем комнату между пользователями
        room, created = ChatRoom.objects.get_or_create(
            type="direct",
            defaults={
                "name": f"{request.user.get_full_name()} - {recipient.get_full_name()}",
                "created_by": request.user,
            },
        )

        # Добавляем участников
        room.participants.add(request.user, recipient)

        # Создаем сообщение
        message = Message.objects.create(
            room=room, sender=request.user, content=message_text, message_type="text"
        )

        serializer = MessageSerializer(message, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
