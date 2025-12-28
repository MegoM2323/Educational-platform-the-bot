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

from django.db import transaction
from django.db.models import Q, Count, Max, Prefetch, OuterRef, Subquery, Case, When, IntegerField, Value, F, Exists
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import StudentProfile, User
from materials.models import SubjectEnrollment, Subject
from .models import ChatRoom, Message, ChatParticipant


def check_parent_access_to_room(user: User, chat: ChatRoom) -> bool:
    """
    Проверяет, имеет ли родитель доступ к комнате чата через своих детей.

    Родители могут получить доступ к FORUM_SUBJECT и FORUM_TUTOR чатам,
    если хотя бы один из их детей является участником комнаты.

    При положительной проверке родитель автоматически добавляется в участники.

    Args:
        user: Пользователь (должен быть родителем)
        chat: Комната чата

    Returns:
        True если доступ разрешён, False иначе
    """
    if user.role != 'parent':
        return False

    # Получаем ID всех детей этого родителя
    children_ids = StudentProfile.objects.filter(
        parent=user
    ).values_list('user_id', flat=True)

    # Проверяем, является ли хотя бы один ребёнок участником комнаты
    if children_ids and chat.participants.filter(id__in=children_ids).exists():
        # Добавляем родителя в участники для будущих проверок
        chat.participants.add(user)
        ChatParticipant.objects.get_or_create(room=chat, user=user)
        logger.info(
            f'[check_parent_access_to_room] Parent {user.id} granted access to room {chat.id} '
            f'via child relationship and added to participants'
        )
        return True

    return False
from .serializers import (
    ChatRoomListSerializer, MessageSerializer, MessageCreateSerializer,
    InitiateChatRequestSerializer, ChatDetailSerializer, AvailableContactSerializer
)
from .permissions import CanInitiateChat

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
            base_queryset = ChatRoom.objects.filter(
                participants=user,
                is_active=True
            ).select_related(
                'created_by',
                'enrollment__subject',
                'enrollment__teacher',
                'enrollment__student'
            ).prefetch_related(
                'participants'
            ).distinct()

            # Filter by chat type and user role
            if user.role == 'student':
                # Student sees ONLY their own FORUM_SUBJECT and FORUM_TUTOR chats
                chats = base_queryset.filter(
                    Q(type=ChatRoom.Type.FORUM_SUBJECT, enrollment__student=user) |
                    Q(type=ChatRoom.Type.FORUM_TUTOR, enrollment__student=user)
                ).order_by('-updated_at')

            elif user.role == 'teacher':
                # Teacher sees ONLY FORUM_SUBJECT chats where they are the assigned teacher
                chats = base_queryset.filter(
                    type=ChatRoom.Type.FORUM_SUBJECT,
                    enrollment__teacher=user  # Verify teacher is assigned via enrollment
                ).order_by('-updated_at')

            elif user.role == 'tutor':
                # Tutor sees ONLY FORUM_TUTOR chats where they are a participant
                # base_queryset already filters by participants=user, so just filter by type
                chats = base_queryset.filter(
                    type=ChatRoom.Type.FORUM_TUTOR
                ).order_by('-updated_at')

            elif user.role == 'parent':
                # Родители видят чаты своих детей
                # Get children's IDs
                children_profiles = StudentProfile.objects.filter(parent=user).values_list('user_id', flat=True)

                if children_profiles:
                    # Get chats where children are participants
                    chats = ChatRoom.objects.filter(
                        Q(
                            type__in=[ChatRoom.Type.FORUM_SUBJECT, ChatRoom.Type.FORUM_TUTOR],
                            participants__id__in=children_profiles
                        ),
                        is_active=True
                    ).select_related(
                        'created_by',
                        'enrollment__subject',
                        'enrollment__teacher',
                        'enrollment__student'
                    ).prefetch_related(
                        'participants'
                    ).distinct().order_by('-updated_at')
                else:
                    chats = ChatRoom.objects.none()

            else:
                # Неизвестная роль - пустой список
                chats = ChatRoom.objects.none()

            # Optimize N+1 queries: annotate unread_count and participants_count
            # This prevents separate queries for each chat in the serializer
            if chats.exists():
                # Prefetch messages to allow unread_count calculation without N+1
                # This prefetches all messages per chat, which unread_count property uses
                messages_prefetch = Prefetch(
                    'messages',
                    queryset=Message.objects.select_related('sender').order_by('-created_at')
                )

                # Prefetch ChatParticipant for current user to avoid N+1
                # This allows serializer to use participant.unread_count without extra queries
                user_participant_prefetch = Prefetch(
                    'room_participants',
                    queryset=ChatParticipant.objects.filter(user=user).select_related('user'),
                    to_attr='current_user_participant'
                )

                chats = chats.prefetch_related(
                    messages_prefetch,
                    user_participant_prefetch
                ).annotate(
                    # Count all participants (simple aggregation, no N+1)
                    annotated_participants_count=Count('participants', distinct=True)
                )

            # Serialize with unread counts
            serializer = ChatRoomListSerializer(
                chats,
                many=True,
                context={'request': request}
            )

            return Response({
                'success': True,
                'count': len(serializer.data),
                'results': serializer.data
            })

        except Exception as e:
            logger.error(
                f"Error listing forum chats for user {user.id}: {str(e)}",
                exc_info=True  # Include traceback for debugging
            )
            return Response(
                {'success': False, 'error': 'Failed to retrieve forum chats'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
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
                        f'[messages] User {user.id} synced from ChatParticipant to M2M '
                        f'for room {pk}'
                    )

            # Проверка 3: Родительский доступ к чатам детей
            if not has_access:
                has_access = check_parent_access_to_room(user, chat)

            if not has_access:
                logger.warning(
                    f'[messages] Access denied: user {user.id} (role={user.role}) '
                    f'is not a participant in room {pk} (type={chat.type})'
                )
                return Response(
                    {'success': False, 'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get pagination parameters
            limit = min(int(request.query_params.get('limit', 50)), 100)
            offset = int(request.query_params.get('offset', 0))

            # Get filter parameters
            search = request.query_params.get('search', '').strip()
            message_type = request.query_params.get('message_type', '').strip()
            sender_id = request.query_params.get('sender', '').strip()

            # Base queryset - exclude deleted messages
            messages = Message.objects.filter(
                room=chat,
                is_deleted=False
            ).select_related(
                'sender',
                'reply_to__sender'
            ).prefetch_related(
                'replies',
                'read_by'
            )

            # Apply search filter
            if search:
                messages = messages.filter(
                    Q(content__icontains=search) |
                    Q(sender__first_name__icontains=search) |
                    Q(sender__last_name__icontains=search)
                )

            # Apply message type filter
            if message_type:
                messages = messages.filter(message_type=message_type)

            # Apply sender filter
            if sender_id:
                messages = messages.filter(sender_id=sender_id)

            # Order and paginate (chronological order, oldest first)
            messages = messages.order_by('created_at')[offset:offset + limit]

            serializer = MessageSerializer(
                messages,
                many=True,
                context={'request': request}
            )

            return Response({
                'success': True,
                'chat_id': pk,
                'limit': limit,
                'offset': offset,
                'count': len(serializer.data),
                'results': serializer.data
            })

        except ChatRoom.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Chat not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving forum messages for chat {pk}: {str(e)}")
            return Response(
                {'success': False, 'error': 'Failed to retrieve messages'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
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
                        f'[send_message] User {user.id} synced from ChatParticipant to M2M '
                        f'for room {pk}'
                    )

            # Проверка 3: Родительский доступ к чатам детей
            if not has_access:
                has_access = check_parent_access_to_room(user, chat)

            if not has_access:
                logger.warning(
                    f'[send_message] Access denied: user {user.id} (role={user.role}) '
                    f'is not a participant in room {pk} (type={chat.type})'
                )
                return Response(
                    {'success': False, 'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if not chat.is_active:
                return Response(
                    {'success': False, 'error': 'Chat is inactive'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract data from request (supports both JSON and FormData)
            content = request.data.get('content', '')
            message_type = request.data.get('message_type', Message.Type.TEXT)
            reply_to = request.data.get('reply_to')
            uploaded_file = request.FILES.get('file')

            # Validate: either content or file must be provided
            if not content and not uploaded_file:
                return Response(
                    {'success': False, 'error': 'Either content or file must be provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate uploaded file if present
            if uploaded_file:
                is_valid, error_message = validate_uploaded_file(
                    uploaded_file,
                    max_size_mb=50  # 50MB limit for chat attachments
                )
                if not is_valid:
                    return Response(
                        {'success': False, 'error': error_message},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Build serializer data
            serializer_data = {
                'room': chat.id,
                'content': content or '',
                'message_type': message_type,
            }
            if reply_to:
                serializer_data['reply_to'] = reply_to

            # Create message with serializer
            serializer = MessageCreateSerializer(
                data=serializer_data,
                context={'request': request}
            )

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
                        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
                        is_image = any(file_name.endswith(ext) for ext in image_extensions)

                        if is_image:
                            # Save to image field and set message_type to IMAGE
                            message.image = uploaded_file
                            message.message_type = Message.Type.IMAGE
                        else:
                            # Save to file field and set message_type to FILE
                            message.file = uploaded_file
                            message.message_type = Message.Type.FILE

                        message.save(update_fields=['file', 'image', 'message_type'])
                        logger.info(
                            f'[send_message] File attached to message {message.id}: '
                            f'{uploaded_file.name} ({uploaded_file.size} bytes), is_image={is_image}'
                        )

                    # Update chat's updated_at timestamp
                    chat.save(update_fields=['updated_at'])

                # Broadcast message to all connected WebSocket clients in this chat room
                # WebSocket broadcast is OUTSIDE transaction - failure here doesn't affect DB
                try:
                    channel_layer = get_channel_layer()
                    message_data = MessageSerializer(
                        message,
                        context={'request': request}
                    ).data

                    room_group_name = f'chat_{chat.id}'
                    async_to_sync(channel_layer.group_send)(
                        room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_data
                        }
                    )
                    logger.info(f'Broadcasted message {message.id} to group {room_group_name}')
                except Exception as e:
                    logger.error(f'Failed to broadcast message via WebSocket: {str(e)}')

                return Response({
                    'success': True,
                    'message': MessageSerializer(
                        message,
                        context={'request': request}
                    ).data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except ChatRoom.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Chat not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending message to forum chat {pk}: {str(e)}")
            return Response(
                {'success': False, 'error': 'Failed to send message'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
    - Checks for existing active chats
    """
    permission_classes = [permissions.IsAuthenticated]

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
            if user.role == 'student':
                # Получить всех учителей из зачислений студента
                teacher_enrollments = SubjectEnrollment.objects.filter(
                    student=user,
                    subject__isnull=False
                ).select_related(
                    'teacher',
                    'subject'
                ).distinct()

                # Добавить учителей в контакты
                for enrollment in teacher_enrollments:
                    teacher = enrollment.teacher
                    if teacher and teacher.role == 'teacher':
                        # Проверить наличие активного чата
                        existing_chat = ChatRoom.objects.filter(
                            type=ChatRoom.Type.FORUM_SUBJECT,
                            enrollment=enrollment,
                            is_active=True
                        ).first()

                        contacts.append({
                            'user': teacher,
                            'subject': enrollment.subject,
                            'has_active_chat': existing_chat is not None,
                            'chat_id': existing_chat.id if existing_chat else None,
                            'enrollment_id': enrollment.id
                        })

                # Получить тьютора студента (если есть)
                try:
                    student_profile = StudentProfile.objects.select_related('tutor').get(user=user)
                    if student_profile.tutor and student_profile.tutor.role == 'tutor':
                        # Проверить наличие активного чата с тьютором
                        # Для FORUM_TUTOR тип нужно найти чат через enrollment с student=user
                        tutor_enrollment = SubjectEnrollment.objects.filter(
                            student=user
                        ).first()  # Берем любое зачисление для связи с чатом

                        existing_chat = ChatRoom.objects.filter(
                            type=ChatRoom.Type.FORUM_TUTOR,
                            enrollment__student=user,
                            participants=student_profile.tutor,
                            is_active=True
                        ).first()

                        contacts.append({
                            'user': student_profile.tutor,
                            'subject': None,
                            'has_active_chat': existing_chat is not None,
                            'chat_id': existing_chat.id if existing_chat else None,
                            'enrollment_id': tutor_enrollment.id if tutor_enrollment else None
                        })
                except StudentProfile.DoesNotExist:
                    pass

            elif user.role == 'teacher':
                # Получить всех студентов из предметов учителя
                student_enrollments = SubjectEnrollment.objects.filter(
                    teacher=user,
                    subject__isnull=False
                ).select_related(
                    'student',
                    'subject'
                ).distinct()

                # Добавить студентов в контакты
                for enrollment in student_enrollments:
                    student = enrollment.student
                    if student and student.role == 'student':
                        # Проверить наличие активного чата
                        existing_chat = ChatRoom.objects.filter(
                            type=ChatRoom.Type.FORUM_SUBJECT,
                            enrollment=enrollment,
                            is_active=True
                        ).first()

                        contacts.append({
                            'user': student,
                            'subject': enrollment.subject,
                            'has_active_chat': existing_chat is not None,
                            'chat_id': existing_chat.id if existing_chat else None,
                            'enrollment_id': enrollment.id
                        })

            elif user.role == 'tutor':
                # Получить всех студентов тьютора
                # Проверяем оба способа связи: StudentProfile.tutor и User.created_by_tutor
                student_profiles = StudentProfile.objects.filter(
                    Q(tutor=user) | Q(user__created_by_tutor=user)
                ).select_related('user').distinct()

                students = [profile.user for profile in student_profiles]

                # Добавить студентов в контакты
                for student in students:
                    if student and student.role == 'student':
                        # Найти enrollment для создания чата (берем первый)
                        student_enrollment = SubjectEnrollment.objects.filter(
                            student=student
                        ).first()

                        # Проверить наличие активного чата
                        existing_chat = ChatRoom.objects.filter(
                            type=ChatRoom.Type.FORUM_TUTOR,
                            enrollment__student=student,
                            participants=user,
                            is_active=True
                        ).first()

                        contacts.append({
                            'user': student,
                            'subject': None,
                            'has_active_chat': existing_chat is not None,
                            'chat_id': existing_chat.id if existing_chat else None,
                            'enrollment_id': student_enrollment.id if student_enrollment else None
                        })

                # Получить всех учителей студентов тьютора
                if students:
                    teacher_enrollments = SubjectEnrollment.objects.filter(
                        student__in=students
                    ).select_related(
                        'teacher',
                        'subject'
                    ).distinct()

                    # Добавить учителей в контакты (избегаем дублирования)
                    seen_teachers = set()
                    for enrollment in teacher_enrollments:
                        teacher = enrollment.teacher
                        if teacher and teacher.role == 'teacher' and teacher.id not in seen_teachers:
                            seen_teachers.add(teacher.id)

                            # Для тьютора и учителя пока нет прямого чата
                            # Оставляем возможность для будущего расширения
                            contacts.append({
                                'user': teacher,
                                'subject': enrollment.subject,
                                'has_active_chat': False,
                                'chat_id': None,
                                'enrollment_id': None
                            })

            elif user.role == 'parent':
                # Родители могут связаться с преподавателями и тьюторами своих детей
                children_profiles = StudentProfile.objects.filter(parent=user).select_related('tutor')
                children_ids = children_profiles.values_list('user_id', flat=True)

                if children_ids:
                    # Получить учителей из зачислений детей
                    teacher_enrollments = SubjectEnrollment.objects.filter(
                        student_id__in=children_ids
                    ).select_related(
                        'teacher',
                        'subject'
                    ).distinct()

                    # Добавить учителей в контакты (избегаем дублирования)
                    seen_teachers = set()
                    for enrollment in teacher_enrollments:
                        teacher = enrollment.teacher
                        if teacher and teacher.role == 'teacher' and teacher.id not in seen_teachers:
                            seen_teachers.add(teacher.id)

                            contacts.append({
                                'user': teacher,
                                'subject': enrollment.subject,
                                'has_active_chat': False,
                                'chat_id': None,
                                'enrollment_id': None
                            })

                    # Получить тьюторов детей
                    for profile in children_profiles:
                        if profile.tutor and profile.tutor.role == 'tutor':
                            # Избегаем дублирования тьюторов
                            tutor_key = profile.tutor.id
                            if tutor_key not in [c['user'].id for c in contacts if c['user'].role == 'tutor']:
                                contacts.append({
                                    'user': profile.tutor,
                                    'subject': None,
                                    'has_active_chat': False,
                                    'chat_id': None,
                                    'enrollment_id': None
                                })

            else:
                # Неизвестная роль - пустой список
                pass

            # Сериализовать контакты
            serializer = AvailableContactSerializer(
                contacts,
                many=True,
                context={'request': request}
            )

            return Response({
                'success': True,
                'count': len(serializer.data),
                'results': serializer.data
            })

        except Exception as e:
            logger.error(f"Error retrieving available contacts for user {user.id}: {str(e)}")
            return Response(
                {'success': False, 'error': 'Failed to retrieve available contacts'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        contact_user_id = serializer.validated_data['contact_user_id']
        subject_id = serializer.validated_data.get('subject_id')

        try:
            # Получить пользователя для чата
            try:
                contact_user = User.objects.get(id=contact_user_id)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Contact user not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Проверить разрешение на создание чата
            can_chat, chat_type, enrollment = CanInitiateChat.can_chat_with(
                request.user,
                contact_user,
                subject_id
            )

            if not can_chat:
                return Response({
                    'success': False,
                    'error': 'You are not authorized to chat with this user'
                }, status=status.HTTP_403_FORBIDDEN)

            if not enrollment:
                return Response({
                    'success': False,
                    'error': 'No enrollment found for this relationship'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Проверить наличие существующего чата (без фильтра is_active для UNIQUE constraint)
            existing_chat = ChatRoom.objects.filter(
                type=getattr(ChatRoom.Type, chat_type),
                enrollment=enrollment
            ).prefetch_related('participants').first()

            if existing_chat:
                # Чат с таким type+enrollment уже существует
                # Реактивировать если неактивен и обновить участников
                with transaction.atomic():
                    if not existing_chat.is_active:
                        existing_chat.is_active = True
                        existing_chat.save(update_fields=['is_active'])
                        logger.info(f"Reactivated chat {existing_chat.id}")

                    # Убедиться что оба участника в чате
                    current_participants = set(existing_chat.participants.values_list('id', flat=True))
                    expected_participants = {request.user.id, contact_user.id}
                    missing_participants = expected_participants - current_participants

                    if missing_participants:
                        for user_id in missing_participants:
                            existing_chat.participants.add(user_id)
                            ChatParticipant.objects.get_or_create(
                                room=existing_chat,
                                user_id=user_id
                            )
                        logger.info(f"Added missing participants to chat {existing_chat.id}: {missing_participants}")

                logger.info(
                    f"Returning existing chat {existing_chat.id} for users "
                    f"{request.user.id} and {contact_user_id}"
                )

                response_serializer = ChatDetailSerializer(
                    existing_chat,
                    context={'request': request}
                )

                return Response({
                    'success': True,
                    'chat': response_serializer.data,
                    'created': False
                }, status=status.HTTP_200_OK)

            # Создать новый чат
            with transaction.atomic():
                # Определить имя чата
                if chat_type == 'FORUM_SUBJECT':
                    subject_name = enrollment.subject.name
                    student_name = enrollment.student.get_full_name()
                    teacher_name = enrollment.teacher.get_full_name()
                    chat_name = f"{subject_name} - {student_name} ↔ {teacher_name}"
                elif chat_type == 'FORUM_TUTOR':
                    subject_name = enrollment.subject.name if enrollment.subject else "General"
                    student_name = enrollment.student.get_full_name()
                    # Получить тьютора из StudentProfile
                    try:
                        student_profile = StudentProfile.objects.get(user=enrollment.student)
                        tutor_name = student_profile.tutor.get_full_name()
                    except StudentProfile.DoesNotExist:
                        tutor_name = contact_user.get_full_name()
                    chat_name = f"{subject_name} - {student_name} ↔ {tutor_name}"
                else:
                    chat_name = f"Chat {request.user.get_full_name()} ↔ {contact_user.get_full_name()}"

                # Создать ChatRoom с get_or_create для race condition safety
                new_chat, created = ChatRoom.objects.get_or_create(
                    type=getattr(ChatRoom.Type, chat_type),
                    enrollment=enrollment,
                    defaults={
                        'name': chat_name,
                        'created_by': request.user,
                        'is_active': True
                    }
                )

                if not created:
                    # Race condition: чат был создан между проверкой и созданием
                    # Реактивировать если неактивен
                    if not new_chat.is_active:
                        new_chat.is_active = True
                        new_chat.save(update_fields=['is_active'])
                    logger.info(f"Race condition resolved: returning existing chat {new_chat.id}")

                # Добавить участников
                new_chat.participants.add(request.user, contact_user)

                # Создать ChatParticipant записи (для unread_count tracking)
                ChatParticipant.objects.get_or_create(
                    room=new_chat,
                    user=request.user
                )
                ChatParticipant.objects.get_or_create(
                    room=new_chat,
                    user=contact_user
                )

                if created:
                    logger.info(
                        f"Created new chat {new_chat.id} ({chat_type}) for users "
                        f"{request.user.id} and {contact_user_id}"
                    )

                # Сериализовать ответ
                response_serializer = ChatDetailSerializer(
                    new_chat,
                    context={'request': request}
                )

                return Response({
                    'success': True,
                    'chat': response_serializer.data,
                    'created': created
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                f"Error initiating chat between {request.user.id} and {contact_user_id}: {str(e)}",
                exc_info=True
            )
            return Response({
                'success': False,
                'error': 'Failed to initiate chat'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
