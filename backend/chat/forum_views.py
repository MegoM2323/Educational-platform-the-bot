"""
REST API views for forum chat functionality.

Provides endpoints for:
- Listing user's forum chats (filtered by role)
- Getting messages from specific forum chat
- Sending messages to forum chat
- Unread message counts per chat
- Available contacts for chat initiation
"""

import logging
import json
from typing import List

from django.db import transaction, IntegrityError
from django.db.models import (
    Q,
    Count,
    Max,
    Prefetch,
    OuterRef,
    Subquery,
    Case,
    When,
    IntegerField,
    Value,
    F,
    Exists,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import StudentProfile, User
from materials.models import SubjectEnrollment, Subject
from .models import ChatRoom, Message, ChatParticipant, MessageThread
from .serializers import (
    ChatRoomListSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    InitiateChatRequestSerializer,
    ChatDetailSerializer,
    AvailableContactSerializer,
)
from .permissions import (
    CanInitiateChat,
    CanModerateChat,
    check_parent_access_to_room,
    check_teacher_access_to_room,
)

logger = logging.getLogger(__name__)


class ForumChatViewSet(viewsets.ViewSet):
    """
    ViewSet for forum chat operations.

    Provides:
    - List user's forum chats (student sees teacher+tutor, teacher sees all students)
    - Get messages for specific forum chat
    - Send messages to forum chat
    - Query optimization with select_related/prefetch_related
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request: Request) -> Response:
        """
        List user's forum chats filtered by role.

        For STUDENT:
        - Returns FORUM_SUBJECT chats (student-teacher)
        - Returns FORUM_TUTOR chats (student-tutor) if student has tutor

        For TEACHER:
        - Returns FORUM_SUBJECT chats where user is teacher

        For TUTOR:
        - Returns FORUM_TUTOR chats where user is tutor

        For PARENT:
        - Returns FORUM_SUBJECT and FORUM_TUTOR chats of their children

        Response includes unread count per chat.

        Query optimization:
        - Uses select_related for participants and enrollment
        - Uses prefetch_related for messages
        - Uses Count aggregation for unread counts

        Returns:
            Response with list of forum chats
        """
        user = request.user

        try:
            # Base query with optimizations
            base_queryset = (
                ChatRoom.objects.filter(participants=user, is_active=True)
                .select_related(
                    "created_by",
                    "enrollment__subject",
                    "enrollment__teacher",
                    "enrollment__student",
                )
                .prefetch_related("participants")
                .distinct()
            )

            # Filter by chat type and user role
            if user.role == "student":
                # Student sees ONLY their own FORUM_SUBJECT and FORUM_TUTOR chats
                # FORUM_SUBJECT: require enrollment__student=user for subject-specific filtering
                # FORUM_TUTOR: enrollment may be NULL, use participants filter (already in base_queryset)
                chats = base_queryset.filter(
                    Q(type=ChatRoom.Type.FORUM_SUBJECT, enrollment__student=user)
                    | Q(type=ChatRoom.Type.FORUM_TUTOR)
                ).order_by("-updated_at")

            elif user.role == "teacher":
                # Teacher sees FORUM_SUBJECT chats where they are assigned teacher
                # OR chat creator (but only if enrollment has no other teacher assigned)
                chats = (
                    base_queryset.filter(type=ChatRoom.Type.FORUM_SUBJECT)
                    .filter(
                        Q(enrollment__teacher=user)
                        | Q(created_by=user, enrollment__teacher__isnull=True)
                    )
                    .order_by("-updated_at")
                )

            elif user.role == "tutor":
                # Tutor sees ONLY FORUM_TUTOR chats for their enrolled students
                # BUG FIX A1: Tutor links to students in TWO ways:
                # 1. StudentProfile.tutor (direct assignment)
                # 2. User.created_by_tutor (created via enrollment)
                # Must check BOTH relationships to get all student chats

                logger.debug(f"[tutor_chat_list] Getting chats for tutor {user.id}")

                # Get all students where tutor is linked (both paths)
                tutored_student_ids = (
                    StudentProfile.objects.filter(Q(tutor=user) | Q(user__created_by_tutor=user))
                    .values_list("user_id", flat=True)
                    .distinct()
                )

                tutored_student_ids_list = list(tutored_student_ids)
                logger.debug(
                    f"[tutor_chat_list] Found {len(tutored_student_ids_list)} students for tutor {user.id}"
                )

                # Get all FORUM_TUTOR chats for these students with full prefetch
                chats = (
                    ChatRoom.objects.filter(
                        type=ChatRoom.Type.FORUM_TUTOR,
                        is_active=True,
                        participants__id__in=tutored_student_ids,
                    )
                    .select_related(
                        "created_by",
                        "enrollment__subject",
                        "enrollment__teacher",
                        "enrollment__student",
                    )
                    .prefetch_related(
                        Prefetch(
                            "participants",
                            queryset=User.objects.only("id", "first_name", "last_name", "role"),
                        )
                    )
                    .distinct()
                    .order_by("-updated_at")
                )

                chats_list = list(chats)
                logger.debug(
                    f"[tutor_chat_list] Found {len(chats_list)} active chats for tutor {user.id}"
                )

                chats_needing_tutor = []
                participant_records = []
                user_id = user.id
                for chat in chats_list:
                    participant_ids = {p.id for p in chat.participants.all()}
                    if user_id not in participant_ids:
                        chats_needing_tutor.append(chat)
                        participant_records.append(ChatParticipant(room=chat, user=user))

                if chats_needing_tutor:
                    # Bulk add tutor to M2M participants
                    for chat in chats_needing_tutor:
                        chat.participants.add(user)

                    # Bulk create ChatParticipant records (ignore conflicts)
                    ChatParticipant.objects.bulk_create(participant_records, ignore_conflicts=True)

                    logger.info(
                        f"[tutor_chat_list] Added tutor {user.id} to {len(chats_needing_tutor)} chats "
                        f"in bulk: {[c.id for c in chats_needing_tutor]}"
                    )

                # Keep chats as queryset for later operations (.exists(), prefetch, annotate)
                # chats_list was only used for efficient iteration with prefetch_related

            elif user.role == "parent":
                # Родители видят чаты своих детей
                # Get children's IDs
                children_profiles = StudentProfile.objects.filter(parent=user).values_list(
                    "user_id", flat=True
                )

                if children_profiles:
                    # Get chats where children are participants
                    chats = (
                        ChatRoom.objects.filter(
                            Q(
                                type__in=[
                                    ChatRoom.Type.FORUM_SUBJECT,
                                    ChatRoom.Type.FORUM_TUTOR,
                                ],
                                participants__id__in=children_profiles,
                            ),
                            is_active=True,
                        )
                        .select_related(
                            "created_by",
                            "enrollment__subject",
                            "enrollment__teacher",
                            "enrollment__student",
                        )
                        .prefetch_related("participants")
                        .distinct()
                        .order_by("-updated_at")
                    )
                else:
                    chats = ChatRoom.objects.none()

            elif user.role == "admin" or user.is_staff or user.is_superuser:
                # Admin has read-only access to ALL forum chats
                # Note: We don't use base_queryset because it filters by participants=user
                # Admin should see all chats even without being a participant
                chats = (
                    ChatRoom.objects.filter(
                        type__in=[
                            ChatRoom.Type.FORUM_SUBJECT,
                            ChatRoom.Type.FORUM_TUTOR,
                        ],
                        is_active=True,
                    )
                    .select_related(
                        "created_by",
                        "enrollment__subject",
                        "enrollment__teacher",
                        "enrollment__student",
                    )
                    .prefetch_related("participants")
                    .distinct()
                    .order_by("-updated_at")
                )

            else:
                # Неизвестная роль - пустой список
                chats = ChatRoom.objects.none()

            # Optimize N+1 queries: annotate unread_count and participants_count
            # This prevents separate queries for each chat in the serializer
            if chats.exists():
                # Prefetch messages to allow last_message calculation without N+1
                messages_prefetch = Prefetch(
                    "messages",
                    queryset=Message.objects.select_related("sender").order_by("-created_at"),
                )

                # Subquery для получения last_read_at текущего пользователя
                participant_last_read_subquery = ChatParticipant.objects.filter(
                    room=OuterRef("pk"), user=user
                ).values("last_read_at")[:1]

                chats = chats.prefetch_related(messages_prefetch).annotate(
                    # Count all participants (simple aggregation, no N+1)
                    annotated_participants_count=Count("participants", distinct=True),
                    # Получаем last_read_at для текущего пользователя через Subquery
                    _user_last_read_at=Subquery(participant_last_read_subquery),
                    # Подсчёт непрочитанных сообщений напрямую на ChatRoom:
                    # - Если last_read_at есть: считаем сообщения после этого времени
                    # - Если last_read_at NULL: считаем все сообщения (кроме своих и удалённых)
                    annotated_unread_count=Count(
                        "messages",
                        filter=(
                            # Базовые условия: не удалено и не от текущего пользователя
                            Q(messages__is_deleted=False)
                            & ~Q(messages__sender=user)
                            & (
                                # Если last_read_at есть - только новые сообщения
                                Q(messages__created_at__gt=F("_user_last_read_at"))
                                |
                                # Если last_read_at NULL - все сообщения
                                Q(_user_last_read_at__isnull=True)
                            )
                        ),
                    ),
                )

            # Serialize with unread counts
            serializer = ChatRoomListSerializer(chats, many=True, context={"request": request})

            return Response(
                {
                    "success": True,
                    "count": len(serializer.data),
                    "results": serializer.data,
                }
            )

        except Exception as e:
            logger.error(
                f"Error listing forum chats for user {user.id}: {str(e)}",
                exc_info=True,  # Include traceback for debugging
            )
            return Response(
                {"success": False, "error": "Failed to retrieve forum chats"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"])
    def messages(self, request: Request, pk: str = None) -> Response:
        """
        Get messages from specific forum chat with search and filtering.

        Supports pagination via query parameters:
        - limit: Number of messages (default 50, max 100)
        - offset: Pagination offset (default 0)

        Supports filtering via query parameters:
        - search: Text search in message content and sender name
        - message_type: Filter by message type (text, file, image, etc.)
        - sender: Filter by sender user ID

        Query optimization:
        - Uses select_related for sender and file/image fields
        - Prefetches related replies
        - Filters by chat_id
        - Excludes deleted messages

        Permission check:
        - User must be participant of the chat

        Args:
            pk: ChatRoom ID

        Returns:
            Response with paginated messages
        """
        try:
            # Get chat room and verify access
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка 1: M2M participants
            has_access = chat.participants.filter(id=user.id).exists()

            # Проверка 2: ChatParticipant (fallback для обратной совместимости)
            if not has_access:
                has_access = ChatParticipant.objects.filter(room=chat, user=user).exists()
                if has_access:
                    # Синхронизируем: добавляем в M2M если ещё нет
                    chat.participants.add(user)
                    logger.info(
                        f"[messages] User {user.id} synced from ChatParticipant to M2M "
                        f"for room {pk}"
                    )

            # Проверка 3: Родительский доступ к чатам детей
            if not has_access:
                has_access = check_parent_access_to_room(user, chat)

            # Проверка 4: Учительский доступ через enrollment
            if not has_access:
                has_access = check_teacher_access_to_room(user, chat)

            # Проверка 5: Admin/staff/superuser имеют read-only доступ ко всем чатам
            if not has_access:
                if user.role == "admin" or user.is_staff or user.is_superuser:
                    has_access = True
                    logger.info(
                        f"[messages] Admin/staff access granted: user {user.id} "
                        f"to room {pk} (type={chat.type})"
                    )

            if not has_access:
                logger.warning(
                    f"[messages] Access denied: user {user.id} (role={user.role}) "
                    f"is not a participant in room {pk} (type={chat.type})"
                )
                return Response(
                    {"success": False, "error": "Access denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Get pagination parameters with validation
            try:
                limit = int(request.query_params.get("limit", 50))
                limit = max(1, min(limit, 100))  # Between 1 and 100
                offset = int(request.query_params.get("offset", 0))
                offset = max(0, offset)  # Must be >= 0
            except (ValueError, TypeError):
                return Response(
                    {"success": False, "error": "Неверные параметры пагинации"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get filter parameters
            search = request.query_params.get("search", "").strip()
            message_type = request.query_params.get("message_type", "").strip()
            sender_id = request.query_params.get("sender", "").strip()

            # Валидация sender_id - должен быть числом если указан
            if sender_id:
                try:
                    sender_id = int(sender_id)
                except (ValueError, TypeError):
                    return Response(
                        {"success": False, "error": "Неверный ID отправителя"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Валидация message_type - должен быть одним из допустимых значений
            allowed_types = ["text", "file", "image", "system"]
            if message_type and message_type not in allowed_types:
                return Response(
                    {
                        "success": False,
                        "error": f'Неверный тип сообщения. Допустимые значения: {", ".join(allowed_types)}',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Base queryset - exclude deleted messages
            # Оптимизация N+1: используем select_related, prefetch_related и аннотации
            messages = (
                Message.objects.filter(room=chat, is_deleted=False)
                .select_related("sender", "thread", "reply_to__sender")
                .prefetch_related(
                    # Prefetch только не-удалённые replies для подсчёта в serializer
                    Prefetch(
                        "replies",
                        queryset=Message.objects.filter(is_deleted=False).only("id", "is_deleted"),
                    ),
                    "read_by",
                )
                .annotate(
                    # Аннотация для replies_count - избегает N+1 при сериализации
                    annotated_replies_count=Count("replies", filter=Q(replies__is_deleted=False))
                )
            )

            # Apply search filter
            if search:
                messages = messages.filter(
                    Q(content__icontains=search)
                    | Q(sender__first_name__icontains=search)
                    | Q(sender__last_name__icontains=search)
                )

            # Apply message type filter
            if message_type:
                messages = messages.filter(message_type=message_type)

            # Apply sender filter
            if sender_id:
                messages = messages.filter(sender_id=sender_id)

            # Order and paginate (chronological order, oldest first)
            messages = messages.order_by("created_at")[offset : offset + limit]

            serializer = MessageSerializer(messages, many=True, context={"request": request})

            return Response(
                {
                    "success": True,
                    "chat_id": pk,
                    "limit": limit,
                    "offset": offset,
                    "count": len(serializer.data),
                    "results": serializer.data,
                }
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error retrieving forum messages for chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to retrieve messages"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def send_message(self, request: Request, pk: str = None) -> Response:
        """
        Send message to forum chat.

        Supports both JSON and multipart/form-data requests:
        - JSON: { "content": "text", "message_type": "text", "reply_to": null }
        - FormData: content (text), file (optional), message_type (optional), reply_to (optional)

        Validates:
        - User is participant of the chat
        - Message content or file is provided
        - Chat is active
        - File type and size (if file uploaded)

        On success:
        - Creates Message instance with optional file/image attachment
        - Triggers Pachca notification signal
        - Updates ChatRoom.updated_at
        - Broadcasts message via WebSocket

        Args:
            pk: ChatRoom ID
            content: Message content (required if no file)
            message_type: Message type, default 'text' (optional)
            reply_to: ID of message being replied to (optional)
            file: Uploaded file (optional, via multipart/form-data)

        Returns:
            Response with created message
        """
        from core.validators import validate_uploaded_file

        try:
            # Get chat room and verify access
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка 1: M2M participants
            has_access = chat.participants.filter(id=user.id).exists()

            # Проверка 2: ChatParticipant (fallback для обратной совместимости)
            if not has_access:
                has_access = ChatParticipant.objects.filter(room=chat, user=user).exists()
                if has_access:
                    # Синхронизируем: добавляем в M2M если ещё нет
                    chat.participants.add(user)
                    logger.info(
                        f"[send_message] User {user.id} synced from ChatParticipant to M2M "
                        f"for room {pk}"
                    )

            # Проверка 3: Родительский доступ к чатам детей
            if not has_access:
                has_access = check_parent_access_to_room(user, chat)

            # Проверка 4: Учительский доступ через enrollment
            if not has_access:
                has_access = check_teacher_access_to_room(user, chat)

            if not has_access:
                logger.warning(
                    f"[send_message] Access denied: user {user.id} (role={user.role}) "
                    f"is not a participant in room {pk} (type={chat.type})"
                )
                return Response(
                    {"success": False, "error": "Access denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Block admin/staff from sending messages (read-only oversight)
            # Parent role CAN send messages - they are NOT blocked
            if user.is_staff or user.is_superuser:
                logger.warning(
                    f"[send_message] Admin/staff blocked from sending: user {user.id} "
                    f"(is_staff={user.is_staff}, is_superuser={user.is_superuser}) "
                    f"attempted to send message to room {pk}"
                )
                return Response(
                    {
                        "success": False,
                        "error": "Администраторы имеют доступ только для чтения",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not chat.is_active:
                return Response(
                    {"success": False, "error": "Chat is inactive"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extract data from request (supports both JSON and FormData)
            content = request.data.get("content", "")
            message_type = request.data.get("message_type", Message.Type.TEXT)
            reply_to = request.data.get("reply_to")
            uploaded_file = request.FILES.get("file")

            # Validate: either content or file must be provided
            if not content and not uploaded_file:
                return Response(
                    {
                        "success": False,
                        "error": "Either content or file must be provided",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate uploaded file if present
            if uploaded_file:
                is_valid, error_message = validate_uploaded_file(
                    uploaded_file, max_size_mb=50  # 50MB limit for chat attachments
                )
                if not is_valid:
                    return Response(
                        {"success": False, "error": error_message},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Build serializer data
            serializer_data = {
                "room": chat.id,
                "content": content or "",
                "message_type": message_type,
            }
            if reply_to:
                serializer_data["reply_to"] = reply_to

            # Create message with serializer
            serializer = MessageCreateSerializer(data=serializer_data, context={"request": request})

            if serializer.is_valid():
                # FIX F004: Wrap in transaction for consistency
                # Message creation and chat update must be atomic
                with transaction.atomic():
                    # Save message (will trigger signal for Pachca notification)
                    message = serializer.save(sender=request.user, room=chat)

                    # Handle file attachment if present
                    if uploaded_file:
                        # Determine if file is an image
                        file_name = uploaded_file.name.lower()
                        image_extensions = {
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".gif",
                            ".webp",
                            ".bmp",
                            ".svg",
                            ".ico",
                        }
                        is_image = any(file_name.endswith(ext) for ext in image_extensions)

                        if is_image:
                            # Save to image field and set message_type to IMAGE
                            message.image = uploaded_file
                            message.message_type = Message.Type.IMAGE
                        else:
                            # Save to file field and set message_type to FILE
                            message.file = uploaded_file
                            message.message_type = Message.Type.FILE

                        message.save(update_fields=["file", "image", "message_type"])
                        logger.info(
                            f"[send_message] File attached to message {message.id}: "
                            f"{uploaded_file.name} ({uploaded_file.size} bytes), is_image={is_image}"
                        )

                    # Update chat's updated_at timestamp
                    chat.save(update_fields=["updated_at"])

                # FIX A7: Removed WebSocket broadcast from REST endpoint
                # Reason: REST response is already sent via onSuccess handler (optimistic update)
                # Other clients will receive message via WebSocket broadcast from consumer
                # (when other users send messages via WebSocket directly)
                # Sender gets message in REST response, avoiding duplicate

                return Response(
                    {
                        "success": True,
                        "message": MessageSerializer(message, context={"request": request}).data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error sending message to forum chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to send message"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["patch"], url_path="messages/(?P<message_id>[^/.]+)/edit")
    def edit_message(self, request: Request, pk: str = None, message_id: str = None) -> Response:
        """
        Edit message in forum chat.

        PATCH /api/chat/forum/{chat_id}/messages/{message_id}/edit/

        Only the message author can edit their own messages.

        Request body:
        {
            "content": "new message content"
        }

        Validation:
        - User must be the author of the message
        - Message must not be deleted
        - Message must belong to this chat
        - New content must be provided

        On success:
        - Updates message content
        - Sets is_edited=True
        - Updates updated_at timestamp
        - Broadcasts edit via WebSocket

        Args:
            pk: ChatRoom ID
            message_id: Message ID

        Returns:
            Response with updated message
        """
        try:
            # Получить чат
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка доступа к чату
            has_access = chat.participants.filter(id=user.id).exists()
            if not has_access:
                has_access = ChatParticipant.objects.filter(room=chat, user=user).exists()

            if not has_access:
                return Response(
                    {"success": False, "error": "Access denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Получить сообщение
            try:
                message = Message.objects.select_related("sender").get(id=message_id, room=chat)
            except Message.DoesNotExist:
                return Response(
                    {"success": False, "error": "Message not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Проверка что сообщение не удалено
            if message.is_deleted:
                return Response(
                    {"success": False, "error": "Cannot edit deleted message"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Проверка что пользователь - автор сообщения
            if message.sender_id != user.id:
                logger.warning(
                    f"[edit_message] Access denied: user {user.id} is not the author "
                    f"of message {message_id} (author: {message.sender_id})"
                )
                return Response(
                    {"success": False, "error": "You can only edit your own messages"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Получить новый контент
            new_content = request.data.get("content", "").strip()
            if not new_content:
                return Response(
                    {"success": False, "error": "Content is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Обновить сообщение
            message.content = new_content
            message.is_edited = True
            message.save(update_fields=["content", "is_edited", "updated_at"])

            logger.info(f"[edit_message] User {user.id} edited message {message_id} in room {pk}")

            # Broadcast edit via WebSocket
            try:
                channel_layer = get_channel_layer()
                message_data = MessageSerializer(message, context={"request": request}).data

                room_group_name = f"chat_{chat.id}"
                async_to_sync(channel_layer.group_send)(
                    room_group_name, {"type": "message_edited", "message": message_data}
                )
                logger.info(f"Broadcasted edit for message {message.id} to group {room_group_name}")
            except Exception as e:
                logger.error(f"Failed to broadcast message edit via WebSocket: {str(e)}")

            return Response(
                {
                    "success": True,
                    "message": MessageSerializer(message, context={"request": request}).data,
                }
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error editing message {message_id} in chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to edit message"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=["delete"],
        url_path="messages/(?P<message_id>[^/.]+)/delete",
    )
    def delete_message(self, request: Request, pk: str = None, message_id: str = None) -> Response:
        """
        Delete message in forum chat (soft delete).

        DELETE /api/chat/forum/{chat_id}/messages/{message_id}/delete/

        Permission:
        - Message author can delete their own messages
        - Moderators (teacher, tutor for FORUM_TUTOR, admin, staff) can delete any message

        On success:
        - Sets is_deleted=True
        - Sets deleted_at=now()
        - Sets deleted_by=user
        - Broadcasts deletion via WebSocket

        Args:
            pk: ChatRoom ID
            message_id: Message ID

        Returns:
            Response with success status
        """
        try:
            # Получить чат
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка доступа к чату
            has_access = chat.participants.filter(id=user.id).exists()
            if not has_access:
                has_access = ChatParticipant.objects.filter(room=chat, user=user).exists()

            if not has_access:
                return Response(
                    {"success": False, "error": "Access denied"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Получить сообщение
            try:
                message = Message.objects.select_related("sender").get(id=message_id, room=chat)
            except Message.DoesNotExist:
                return Response(
                    {"success": False, "error": "Message not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Проверка что сообщение не удалено
            if message.is_deleted:
                return Response(
                    {"success": False, "error": "Message already deleted"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Проверка прав: автор ИЛИ модератор
            is_author = message.sender_id == user.id
            is_moderator = self._check_moderation_permission(user, chat)

            if not is_author and not is_moderator:
                logger.warning(
                    f"[delete_message] Access denied: user {user.id} is not the author "
                    f"of message {message_id} and is not a moderator"
                )
                return Response(
                    {
                        "success": False,
                        "error": "You can only delete your own messages or be a moderator",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Soft delete сообщения
            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.deleted_by = user
            message.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

            deleted_by_role = "author" if is_author else "moderator"
            logger.info(
                f"[delete_message] User {user.id} ({deleted_by_role}) deleted message {message_id} in room {pk}"
            )

            # Broadcast deletion via WebSocket
            try:
                channel_layer = get_channel_layer()
                room_group_name = f"chat_{chat.id}"
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        "type": "message_deleted",
                        "message_id": str(message_id),
                        "deleted_by": user.id,
                        "deleted_by_role": deleted_by_role,
                    },
                )
                logger.info(
                    f"Broadcasted deletion for message {message_id} to group {room_group_name}"
                )
            except Exception as e:
                logger.error(f"Failed to broadcast message deletion via WebSocket: {str(e)}")

            return Response(
                {
                    "success": True,
                    "message_id": str(message_id),
                    "deleted_by": user.id,
                    "deleted_by_role": deleted_by_role,
                    "deleted_at": message.deleted_at.isoformat(),
                }
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error deleting message {message_id} in chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to delete message"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _check_moderation_permission(self, user, chat) -> bool:
        """
        Проверяет права модерации для пользователя в чате.

        Модератором может быть:
        1. staff/superuser
        2. ChatParticipant с is_admin=True
        3. teacher
        4. tutor для FORUM_TUTOR чатов

        Args:
            user: User объект
            chat: ChatRoom объект

        Returns:
            bool: True если пользователь может модерировать
        """
        if user.is_staff or user.is_superuser:
            return True

        participant = ChatParticipant.objects.filter(room=chat, user=user).first()
        if not participant:
            logger.warning(f"[moderation] User {user.id} is not a participant in room {chat.id}")
            return False

        if participant.is_admin:
            return True

        if user.role == "teacher":
            return True

        if user.role == "tutor" and chat.type == ChatRoom.Type.FORUM_TUTOR:
            return True

        return False

    @action(detail=True, methods=["post"], url_path="messages/(?P<message_id>[^/.]+)/pin")
    def pin_message(self, request: Request, pk: str = None, message_id: str = None) -> Response:
        """
        Закрепить/открепить сообщение в чате.

        POST /api/chat/forum/{chat_id}/messages/{message_id}/pin/

        Только для модераторов (teacher, tutor, admin).
        Toggle is_pinned на сообщении.

        Args:
            pk: ChatRoom ID
            message_id: Message ID

        Returns:
            Response с результатом операции
        """
        try:
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка прав модерации
            if not self._check_moderation_permission(user, chat):
                return Response(
                    {
                        "success": False,
                        "error": "Permission denied. Moderation rights required.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Получить сообщение
            try:
                message = Message.objects.get(id=message_id, room=chat, is_deleted=False)
            except Message.DoesNotExist:
                return Response(
                    {"success": False, "error": "Message not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Для pin/unpin нужно привязать сообщение к треду
            # Если сообщение не в треде - создаём новый тред
            if not message.thread:
                # Создаём тред для этого сообщения
                thread = MessageThread.objects.create(
                    room=chat,
                    title=message.content[:100] if message.content else f"Thread #{message.id}",
                    created_by=message.sender,
                )
                message.thread = thread
                message.save(update_fields=["thread"])
                logger.info(f"Created thread {thread.id} for message {message.id}")

            # Toggle is_pinned на треде
            thread = message.thread
            thread.is_pinned = not thread.is_pinned
            thread.save(update_fields=["is_pinned", "updated_at"])

            action_str = "pinned" if thread.is_pinned else "unpinned"
            logger.info(
                f"[pin_message] User {user.id} {action_str} message {message_id} "
                f"(thread {thread.id}) in room {pk}"
            )

            return Response(
                {
                    "success": True,
                    "message_id": message_id,
                    "thread_id": str(thread.id),
                    "is_pinned": thread.is_pinned,
                    "action": action_str,
                }
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error pinning message {message_id} in chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to pin message"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="lock")
    def lock_chat(self, request: Request, pk: str = None) -> Response:
        """
        Заблокировать/разблокировать чат.

        POST /api/chat/forum/{chat_id}/lock/

        Только для модераторов (teacher, tutor, admin).
        Toggle is_active на ChatRoom (блокировка = is_active=False).

        Args:
            pk: ChatRoom ID

        Returns:
            Response с результатом операции
        """
        try:
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка прав модерации
            if not self._check_moderation_permission(user, chat):
                return Response(
                    {
                        "success": False,
                        "error": "Permission denied. Moderation rights required.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Toggle is_active (locked = not active)
            chat.is_active = not chat.is_active
            chat.save(update_fields=["is_active", "updated_at"])

            is_locked = not chat.is_active
            action_str = "locked" if is_locked else "unlocked"

            logger.info(f"[lock_chat] User {user.id} {action_str} room {pk}")

            return Response(
                {
                    "success": True,
                    "chat_id": pk,
                    "is_locked": is_locked,
                    "is_active": chat.is_active,
                    "action": action_str,
                }
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error locking chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to lock chat"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="participants/(?P<user_id>[^/.]+)/mute")
    def mute_participant(self, request: Request, pk: str = None, user_id: str = None) -> Response:
        """
        Заглушить/разглушить участника чата.

        POST /api/chat/forum/{chat_id}/participants/{user_id}/mute/

        Только для модераторов (teacher, tutor, admin).
        Toggle is_muted на ChatParticipant.

        Args:
            pk: ChatRoom ID
            user_id: User ID участника

        Returns:
            Response с результатом операции
        """
        try:
            chat = ChatRoom.objects.get(id=pk)
            user = request.user

            # Проверка прав модерации
            if not self._check_moderation_permission(user, chat):
                return Response(
                    {
                        "success": False,
                        "error": "Permission denied. Moderation rights required.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Нельзя замутить самого себя
            if str(user.id) == user_id:
                return Response(
                    {"success": False, "error": "Cannot mute yourself"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Получить участника
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"success": False, "error": "User not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Нельзя замутить teacher или admin
            if (
                target_user.role in ["teacher", "admin"]
                or target_user.is_staff
                or target_user.is_superuser
            ):
                return Response(
                    {"success": False, "error": "Cannot mute teacher or admin"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Получить или создать ChatParticipant
            participant, created = ChatParticipant.objects.get_or_create(
                room=chat, user=target_user
            )

            # Toggle is_muted
            participant.is_muted = not participant.is_muted
            participant.save(update_fields=["is_muted"])

            action_str = "muted" if participant.is_muted else "unmuted"
            logger.info(
                f"[mute_participant] User {user.id} {action_str} user {user_id} in room {pk}"
            )

            return Response(
                {
                    "success": True,
                    "chat_id": pk,
                    "user_id": user_id,
                    "is_muted": participant.is_muted,
                    "action": action_str,
                }
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Chat not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error muting participant {user_id} in chat {pk}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to mute participant"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AvailableContactsView(APIView):
    """
    Returns list of users the authenticated user can initiate chats with.

    Contact discovery logic per role:

    STUDENT:
    - Teachers from SubjectEnrollment (student's enrolled subjects)
    - Tutor from StudentProfile.tutor (if assigned)

    TEACHER:
    - Students from SubjectEnrollment (students in teacher's subjects)

    TUTOR:
    - Students from StudentProfile.tutor (students assigned to tutor)
    - Teachers from SubjectEnrollment (teachers of tutor's students)

    PARENT:
    - Teachers from SubjectEnrollment (teachers of parent's children)
    - Tutors from StudentProfile.tutor (tutors assigned to parent's children)

    Query optimization:
    - Uses select_related to avoid N+1 queries
    - Uses distinct() to eliminate duplicates
    - Pre-fetches all user chats to avoid N+1 for existing_chat checks
    - Checks for existing active chats via mapping
    """

    permission_classes = [permissions.IsAuthenticated]

    def _build_contact_to_chat_mapping(self, user: User) -> tuple:
        """
        Получить все existing chats пользователя ОДНИМ запросом.
        Возвращает tuple: (contact_to_chat, enrollment_to_chat)

        contact_to_chat: mapping (contact_id, chat_type) -> chat
        enrollment_to_chat: mapping enrollment_id -> chat

        Оптимизация N+1: вместо запроса для каждого контакта,
        делаем один запрос и строим lookup dictionary.
        """
        user_chats = ChatRoom.objects.filter(
            participants=user,
            type__in=[ChatRoom.Type.FORUM_SUBJECT, ChatRoom.Type.FORUM_TUTOR],
            is_active=True,
        ).prefetch_related("participants")

        # Mapping: (contact_id, chat_type) -> chat
        contact_to_chat = {}
        # Mapping: enrollment_id -> chat (для teacher role)
        enrollment_to_chat = {}

        for chat in user_chats:
            for participant in chat.participants.all():
                if participant.id != user.id:
                    # Ключ: (contact_id, chat_type) для точного матчинга
                    contact_to_chat[(participant.id, chat.type)] = chat
            # Также храним по enrollment_id если есть
            if chat.enrollment_id:
                enrollment_to_chat[chat.enrollment_id] = chat

        return contact_to_chat, enrollment_to_chat

    def get(self, request: Request) -> Response:
        """
        Get available contacts for the authenticated user.

        Returns:
            Response with list of available contacts, including:
            - User info (id, email, first_name, last_name, role, avatar)
            - has_active_chat (boolean)
            - chat_id (if has_active_chat is True)
        """
        user = request.user
        contacts = []

        try:
            # Оптимизация N+1: получаем ВСЕ чаты пользователя ОДНИМ запросом
            contact_to_chat, enrollment_to_chat = self._build_contact_to_chat_mapping(user)

            if user.role == "student":
                # Получить всех учителей из зачислений студента
                student_enrollments = SubjectEnrollment.objects.filter(
                    student=user, is_active=True
                ).select_related("teacher", "subject")

                # Используем dict для дедупликации по teacher_id
                teachers_seen = {}
                for enrollment in student_enrollments:
                    teacher = enrollment.teacher
                    if teacher and teacher.role == "teacher":
                        if teacher.id not in teachers_seen:
                            teachers_seen[teacher.id] = {
                                "user": teacher,
                                "subjects": [enrollment.subject],
                                "enrollment": enrollment,
                            }
                        else:
                            teachers_seen[teacher.id]["subjects"].append(enrollment.subject)

                # Добавить учителей в контакты (без дубликатов)
                for teacher_id, data in teachers_seen.items():
                    # Используем mapping вместо запроса (оптимизация N+1)
                    existing_chat = contact_to_chat.get((teacher_id, ChatRoom.Type.FORUM_SUBJECT))

                    contacts.append(
                        {
                            "user": data["user"],
                            "subject": data["subjects"][0],  # Первый предмет
                            "subjects": data["subjects"],  # Все предметы
                            "has_active_chat": existing_chat is not None,
                            "chat_id": existing_chat.id if existing_chat else None,
                            "enrollment_id": data["enrollment"].id,
                        }
                    )

                # Получить тьютора студента (если есть)
                try:
                    student_profile = StudentProfile.objects.select_related("tutor").get(user=user)
                    if student_profile.tutor and student_profile.tutor.role == "tutor":
                        # Берем любое зачисление для связи с чатом
                        tutor_enrollment = SubjectEnrollment.objects.filter(student=user).first()

                        # Используем mapping вместо запроса (оптимизация N+1)
                        existing_chat = contact_to_chat.get(
                            (student_profile.tutor.id, ChatRoom.Type.FORUM_TUTOR)
                        )

                        contacts.append(
                            {
                                "user": student_profile.tutor,
                                "subject": None,
                                "has_active_chat": existing_chat is not None,
                                "chat_id": existing_chat.id if existing_chat else None,
                                "enrollment_id": tutor_enrollment.id if tutor_enrollment else None,
                            }
                        )
                except StudentProfile.DoesNotExist:
                    pass

            elif user.role == "teacher":
                # Получить всех студентов из предметов учителя
                # FIX: Добавляем is_active=True для фильтрации только активных enrollment
                student_enrollments = (
                    SubjectEnrollment.objects.filter(
                        teacher=user, subject__isnull=False, is_active=True
                    )
                    .select_related("student", "subject")
                    .distinct()
                )

                # Добавить студентов в контакты
                for enrollment in student_enrollments:
                    student = enrollment.student
                    if student and student.role == "student":
                        # Используем enrollment_to_chat для точного матчинга (оптимизация N+1)
                        existing_chat = enrollment_to_chat.get(enrollment.id)

                        contacts.append(
                            {
                                "user": student,
                                "subject": enrollment.subject,
                                "has_active_chat": existing_chat is not None,
                                "chat_id": existing_chat.id if existing_chat else None,
                                "enrollment_id": enrollment.id,
                            }
                        )

                # Получить тьюторов студентов этого учителя
                # Teacher can chat with tutors of their students
                student_ids = list(student_enrollments.values_list("student_id", flat=True))

                # Находим тьюторов через StudentProfile.tutor и User.created_by_tutor
                tutors = User.objects.filter(
                    Q(tutored_students__user_id__in=student_ids)
                    | Q(created_users__id__in=student_ids),
                    role="tutor",
                ).distinct()

                # Оптимизация N+1: получаем все enrollments для всех тьюторов ОДНИМ запросом
                tutor_ids = list(tutors.values_list("id", flat=True))
                tutor_enrollments_map = {}
                if tutor_ids:
                    for enrollment in SubjectEnrollment.objects.filter(
                        student_id__in=student_ids,
                        teacher=user,
                        is_active=True,
                    ).select_related("student__student_profile"):
                        # Получаем tutor_id из студента
                        if (
                            enrollment.student.student_profile
                            and enrollment.student.student_profile.tutor_id
                        ):
                            tutor_id = enrollment.student.student_profile.tutor_id
                        elif enrollment.student.created_by_tutor_id:
                            tutor_id = enrollment.student.created_by_tutor_id
                        else:
                            continue

                        # Сохраняем первый found enrollment для каждого тьютора
                        if tutor_id not in tutor_enrollments_map:
                            tutor_enrollments_map[tutor_id] = enrollment

                # Для каждого тьютора используем prefetched enrollment
                for tutor in tutors:
                    tutor_enrollment = tutor_enrollments_map.get(tutor.id)

                    # Используем mapping вместо запроса (оптимизация N+1)
                    existing_chat = contact_to_chat.get((tutor.id, ChatRoom.Type.FORUM_TUTOR))

                    contacts.append(
                        {
                            "user": tutor,
                            "subject": None,  # Тьютор не привязан к предмету
                            "has_active_chat": existing_chat is not None,
                            "chat_id": existing_chat.id if existing_chat else None,
                            "enrollment_id": tutor_enrollment.id if tutor_enrollment else None,
                        }
                    )

            elif user.role == "tutor":
                # Получить всех студентов тьютора
                # Проверяем оба способа связи: StudentProfile.tutor и User.created_by_tutor
                student_profiles = (
                    StudentProfile.objects.filter(Q(tutor=user) | Q(user__created_by_tutor=user))
                    .select_related("user")
                    .distinct()
                )

                students = [profile.user for profile in student_profiles if profile.user]

                # Оптимизация N+1: получаем все enrollments для студентов одним запросом
                student_ids = [s.id for s in students if s and s.role == "student"]
                student_enrollments_map = {}
                if student_ids:
                    for enrollment in SubjectEnrollment.objects.filter(student_id__in=student_ids):
                        if enrollment.student_id not in student_enrollments_map:
                            student_enrollments_map[enrollment.student_id] = enrollment

                # Добавить студентов в контакты
                for student in students:
                    if student and student.role == "student":
                        # Используем предзагруженный enrollment (оптимизация N+1)
                        student_enrollment = student_enrollments_map.get(student.id)

                        # Используем mapping вместо запроса (оптимизация N+1)
                        existing_chat = contact_to_chat.get((student.id, ChatRoom.Type.FORUM_TUTOR))

                        contacts.append(
                            {
                                "user": student,
                                "subject": None,
                                "has_active_chat": existing_chat is not None,
                                "chat_id": existing_chat.id if existing_chat else None,
                                "enrollment_id": student_enrollment.id
                                if student_enrollment
                                else None,
                            }
                        )

                # Получить всех учителей студентов тьютора
                if students:
                    teacher_enrollments = (
                        SubjectEnrollment.objects.filter(student__in=students)
                        .select_related("teacher", "subject")
                        .distinct()
                    )

                    # Добавить учителей в контакты (избегаем дублирования)
                    seen_teachers = set()
                    for enrollment in teacher_enrollments:
                        teacher = enrollment.teacher
                        if (
                            teacher
                            and teacher.role == "teacher"
                            and teacher.id not in seen_teachers
                        ):
                            seen_teachers.add(teacher.id)

                            # Используем mapping вместо запроса (оптимизация N+1)
                            # Проверяем оба типа чатов
                            existing_chat = contact_to_chat.get(
                                (teacher.id, ChatRoom.Type.FORUM_SUBJECT)
                            ) or contact_to_chat.get((teacher.id, ChatRoom.Type.FORUM_TUTOR))

                            contacts.append(
                                {
                                    "user": teacher,
                                    "subject": enrollment.subject,
                                    "has_active_chat": existing_chat is not None,
                                    "chat_id": existing_chat.id if existing_chat else None,
                                    "enrollment_id": None,
                                }
                            )

            elif user.role == "parent":
                # Родители могут связаться с преподавателями и тьюторами своих детей
                children_profiles = StudentProfile.objects.filter(parent=user).select_related(
                    "tutor"
                )
                children_ids = children_profiles.values_list("user_id", flat=True)

                if children_ids:
                    # Получить учителей из зачислений детей
                    teacher_enrollments = (
                        SubjectEnrollment.objects.filter(student_id__in=children_ids)
                        .select_related("teacher", "subject")
                        .distinct()
                    )

                    # Добавить учителей в контакты (избегаем дублирования)
                    seen_teachers = set()
                    for enrollment in teacher_enrollments:
                        teacher = enrollment.teacher
                        if (
                            teacher
                            and teacher.role == "teacher"
                            and teacher.id not in seen_teachers
                        ):
                            seen_teachers.add(teacher.id)

                            # Используем mapping вместо запроса (оптимизация N+1)
                            existing_chat = contact_to_chat.get(
                                (teacher.id, ChatRoom.Type.FORUM_SUBJECT)
                            )

                            contacts.append(
                                {
                                    "user": teacher,
                                    "subject": enrollment.subject,
                                    "has_active_chat": existing_chat is not None,
                                    "chat_id": existing_chat.id if existing_chat else None,
                                    "enrollment_id": None,
                                }
                            )

                    # Получить тьюторов детей
                    seen_tutors = set()
                    for profile in children_profiles:
                        if profile.tutor and profile.tutor.role == "tutor":
                            tutor_id = profile.tutor.id
                            # Используем set для дедупликации (оптимизация)
                            if tutor_id not in seen_tutors:
                                seen_tutors.add(tutor_id)

                                # Используем mapping вместо запроса (оптимизация N+1)
                                existing_chat = contact_to_chat.get(
                                    (tutor_id, ChatRoom.Type.FORUM_TUTOR)
                                )

                                contacts.append(
                                    {
                                        "user": profile.tutor,
                                        "subject": None,
                                        "has_active_chat": existing_chat is not None,
                                        "chat_id": existing_chat.id if existing_chat else None,
                                        "enrollment_id": None,
                                    }
                                )

            elif user.role == "admin" or user.is_staff or user.is_superuser:
                # Admin has read-only access - cannot initiate chats
                # Return empty contacts list
                pass

            else:
                # Неизвестная роль - пустой список
                pass

            # Сериализовать контакты
            serializer = AvailableContactSerializer(
                contacts, many=True, context={"request": request}
            )

            return Response(
                {
                    "success": True,
                    "count": len(serializer.data),
                    "results": serializer.data,
                }
            )

        except Exception as e:
            logger.error(f"Error retrieving available contacts for user {user.id}: {str(e)}")
            return Response(
                {"success": False, "error": "Failed to retrieve available contacts"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InitiateChatView(APIView):
    """
    Create or retrieve existing chat between users.

    POST /api/chat/initiate-chat/
    {
        "contact_user_id": 42,
        "subject_id": 1  // optional, for FORUM_SUBJECT type
    }

    Functionality:
    - Validates permission to chat (using CanInitiateChat permission)
    - Determines chat type based on roles and subject_id
    - Checks for existing chat (idempotent)
    - Creates new chat with participants if not exists
    - Returns chat details with room_id for WebSocket connection

    Response:
    {
        "id": 99,
        "room_id": "chat_room_99",
        "type": "FORUM_SUBJECT",
        "other_user": {...},
        "created_at": "2025-12-14T10:30:00Z",
        "last_message": null,
        "unread_count": 0,
        "name": "Subject - Student ↔ Teacher"
    }
    """

    permission_classes = [permissions.IsAuthenticated, CanInitiateChat]

    def post(self, request: Request) -> Response:
        """
        Initiate chat with contact user.

        Validates request, checks permissions, and creates/retrieves chat.
        """
        # Валидация входных данных
        serializer = InitiateChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact_user_id = serializer.validated_data["contact_user_id"]
        subject_id = serializer.validated_data.get("subject_id")

        try:
            # Получить пользователя для чата
            try:
                contact_user = User.objects.get(id=contact_user_id)
            except User.DoesNotExist:
                return Response(
                    {"success": False, "error": "Contact user not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Проверить разрешение на создание чата
            can_chat, chat_type, enrollment = CanInitiateChat.can_chat_with(
                request.user, contact_user, subject_id
            )

            if not can_chat:
                return Response(
                    {
                        "success": False,
                        "error": "You are not authorized to chat with this user",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not enrollment:
                return Response(
                    {
                        "success": False,
                        "error": "No enrollment found for this relationship",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Проверить наличие существующего чата и создать новый в одной транзакции
            # с блокировкой enrollment для предотвращения race condition
            with transaction.atomic():
                # Lock the enrollment row to prevent concurrent chat creation
                enrollment_locked = SubjectEnrollment.objects.select_for_update().get(
                    id=enrollment.id
                )

                existing_chat = (
                    ChatRoom.objects.filter(
                        type=getattr(ChatRoom.Type, chat_type),
                        enrollment=enrollment_locked,
                    )
                    .prefetch_related("participants")
                    .first()
                )

                if existing_chat:
                    # Чат с таким type+enrollment уже существует
                    # Реактивировать если неактивен и обновить участников
                    if not existing_chat.is_active:
                        existing_chat.is_active = True
                        existing_chat.save(update_fields=["is_active"])
                        logger.info(f"Reactivated chat {existing_chat.id}")

                    # Убедиться что оба участника в чате
                    current_participants = set(
                        existing_chat.participants.values_list("id", flat=True)
                    )
                    expected_participants = {request.user.id, contact_user.id}
                    missing_participants = expected_participants - current_participants

                    if missing_participants:
                        for user_id in missing_participants:
                            existing_chat.participants.add(user_id)
                            ChatParticipant.objects.get_or_create(
                                room=existing_chat, user_id=user_id
                            )
                        logger.info(
                            f"Added missing participants to chat {existing_chat.id}: {missing_participants}"
                        )

                    logger.info(
                        f"Returning existing chat {existing_chat.id} for users "
                        f"{request.user.id} and {contact_user_id}"
                    )

                    response_serializer = ChatDetailSerializer(
                        existing_chat, context={"request": request}
                    )

                    return Response(
                        {
                            "success": True,
                            "chat": response_serializer.data,
                            "created": False,
                        },
                        status=status.HTTP_200_OK,
                    )

                # Создать новый чат (внутри того же atomic блока)
                # Определить имя чата
                if chat_type == "FORUM_SUBJECT":
                    subject_name = enrollment_locked.subject.name

                    # Проверяем кто инициирует чат
                    if request.user.role == "parent":
                        # Parent initiated chat with teacher
                        child_name = (
                            enrollment_locked.student.first_name or enrollment_locked.student.email
                        )
                        teacher_name = contact_user.first_name or contact_user.email
                        chat_name = f"{subject_name} - Родитель ({child_name}) ↔ {teacher_name}"
                    elif request.user.role == "student":
                        student_name = request.user.first_name or request.user.email
                        teacher_name = contact_user.first_name or contact_user.email
                        chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"
                    elif request.user.role == "teacher":
                        student_name = contact_user.first_name or contact_user.email
                        teacher_name = request.user.first_name or request.user.email
                        chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"
                    else:
                        # Fallback для других ролей
                        student_name = enrollment_locked.student.get_full_name()
                        teacher_name = enrollment_locked.teacher.get_full_name()
                        chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"
                elif chat_type == "FORUM_TUTOR":
                    # Проверяем тип связи: tutor-teacher или tutor-student
                    user = request.user
                    target_user = contact_user

                    if user.role == "tutor" and target_user.role == "teacher":
                        # Чат между тьютором и учителем
                        chat_name = f"Тьютор {user.first_name} ↔ Учитель {target_user.first_name}"
                    elif user.role == "teacher" and target_user.role == "tutor":
                        # Чат между учителем и тьютором
                        chat_name = f"Учитель {user.first_name} ↔ Тьютор {target_user.first_name}"
                    else:
                        # Стандартное имя для tutor-student чата
                        student_name = (
                            enrollment_locked.student.first_name or enrollment_locked.student.email
                        )
                        chat_name = f"Тьютор - {student_name}"
                else:
                    chat_name = (
                        f"Chat {request.user.get_full_name()} ↔ {contact_user.get_full_name()}"
                    )

                # T046: Валидация имени чата - проверка на пустое/пробельное значение
                if not chat_name or not chat_name.strip():
                    # Генерируем дефолтное имя если имя пустое
                    chat_name = f"Chat #{enrollment_locked.id}"
                    logger.warning(
                        f"[InitiateChatView] Empty chat name generated, using fallback: {chat_name}"
                    )
                else:
                    chat_name = chat_name.strip()

                # Создать ChatRoom с get_or_create для race condition safety
                # Обёрнуто в try-except для обработки IntegrityError при concurrent запросах
                try:
                    new_chat, created = ChatRoom.objects.get_or_create(
                        type=getattr(ChatRoom.Type, chat_type),
                        enrollment=enrollment_locked,
                        defaults={
                            "name": chat_name,
                            "created_by": request.user,
                            "is_active": True,
                        },
                    )
                except IntegrityError:
                    # Другой concurrent запрос уже создал чат - получить существующий
                    logger.warning(
                        f"IntegrityError caught during chat creation for enrollment {enrollment_locked.id}. "
                        f"Fetching existing chat."
                    )
                    new_chat = ChatRoom.objects.filter(
                        type=getattr(ChatRoom.Type, chat_type),
                        enrollment=enrollment_locked,
                    ).first()

                    if new_chat:
                        created = False
                        logger.info(f"Found existing chat {new_chat.id} after IntegrityError")
                    else:
                        # Очень редкий edge case - перезапустить транзакцию
                        logger.error(
                            f"IntegrityError but no existing chat found for enrollment {enrollment_locked.id}"
                        )
                        raise

                if not created:
                    # Race condition: чат был создан между проверкой и созданием
                    # Реактивировать если неактивен
                    if not new_chat.is_active:
                        new_chat.is_active = True
                        new_chat.save(update_fields=["is_active"])
                    logger.info(f"Race condition resolved: returning existing chat {new_chat.id}")

                # Добавить участников
                new_chat.participants.add(request.user, contact_user)

                # Создать ChatParticipant записи (для unread_count tracking)
                ChatParticipant.objects.get_or_create(room=new_chat, user=request.user)
                ChatParticipant.objects.get_or_create(room=new_chat, user=contact_user)

                if created:
                    logger.info(
                        f"Created new chat {new_chat.id} ({chat_type}) for users "
                        f"{request.user.id} and {contact_user_id}"
                    )

                # Сериализовать ответ
                response_serializer = ChatDetailSerializer(new_chat, context={"request": request})

                return Response(
                    {
                        "success": True,
                        "chat": response_serializer.data,
                        "created": created,
                    },
                    status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                )

        except Exception as e:
            logger.error(
                f"Error initiating chat between {request.user.id} and {contact_user_id}: {str(e)}",
                exc_info=True,
            )
            return Response(
                {"success": False, "error": "Failed to initiate chat"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
