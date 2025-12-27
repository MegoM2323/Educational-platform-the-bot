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
        - Returns empty list (parents don't participate in forum chats)

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

            else:
                # Parent doesn't see forum chats
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
            logger.error(f"Error listing forum chats for user {user.id}: {str(e)}")
            return Response(
                {'success': False, 'error': 'Failed to retrieve forum chats'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def messages(self, request: Request, pk: str = None) -> Response:
        """
        Get messages from specific forum chat.

        Supports pagination via query parameters:
        - limit: Number of messages (default 50, max 100)
        - offset: Pagination offset (default 0)

        Query optimization:
        - Uses select_related for sender and file/image fields
        - Prefetches related replies
        - Filters by chat_id

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

            if not chat.participants.filter(id=request.user.id).exists():
                return Response(
                    {'success': False, 'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get pagination parameters
            limit = min(int(request.query_params.get('limit', 50)), 100)
            offset = int(request.query_params.get('offset', 0))

            # Fetch messages with optimization (chronological order, oldest first)
            messages = Message.objects.filter(
                room=chat
            ).select_related(
                'sender',
                'reply_to__sender'
            ).prefetch_related(
                'replies',
                'read_by'
            ).order_by('created_at')[offset:offset + limit]

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

        Validates:
        - User is participant of the chat
        - Message content is provided
        - Chat is active

        On success:
        - Creates Message instance
        - Triggers Pachca notification signal
        - Updates ChatRoom.updated_at

        Args:
            pk: ChatRoom ID
            content: Message content (required)
            message_type: Message type, default 'text' (optional)
            reply_to: ID of message being replied to (optional)

        Returns:
            Response with created message
        """
        try:
            # Get chat room and verify access
            chat = ChatRoom.objects.get(id=pk)

            if not chat.participants.filter(id=request.user.id).exists():
                return Response(
                    {'success': False, 'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if not chat.is_active:
                return Response(
                    {'success': False, 'error': 'Chat is inactive'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create message with serializer
            serializer = MessageCreateSerializer(
                data={**request.data, 'room': chat.id},
                context={'request': request}
            )

            if serializer.is_valid():
                # FIX F004: Wrap in transaction for consistency
                # Message creation and chat update must be atomic
                with transaction.atomic():
                    # Save message (will trigger signal for Pachca notification)
                    message = serializer.save(sender=request.user, room=chat)

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
    - Empty list (parents don't initiate forum chats)

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
                student_profiles = StudentProfile.objects.filter(
                    tutor=user
                ).select_related('user')

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

            else:
                # Parent или другие роли - пустой список
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

            # Проверить наличие существующего чата (idempotency)
            existing_chat = ChatRoom.objects.filter(
                type=getattr(ChatRoom.Type, chat_type),
                enrollment=enrollment,
                is_active=True
            ).prefetch_related('participants').first()

            if existing_chat:
                # Проверить что оба участника в чате
                participant_ids = set(existing_chat.participants.values_list('id', flat=True))
                expected_ids = {request.user.id, contact_user.id}

                if participant_ids == expected_ids:
                    # Чат уже существует, вернуть его
                    logger.info(
                        f"Existing chat {existing_chat.id} found for users "
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

                # Создать ChatRoom
                new_chat = ChatRoom.objects.create(
                    name=chat_name,
                    type=getattr(ChatRoom.Type, chat_type),
                    enrollment=enrollment,
                    created_by=request.user,
                    is_active=True
                )

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
                    'created': True
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                f"Error initiating chat between {request.user.id} and {contact_user_id}: {str(e)}",
                exc_info=True
            )
            return Response({
                'success': False,
                'error': 'Failed to initiate chat'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
