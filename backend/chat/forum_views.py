"""
REST API views for forum chat functionality.

Provides endpoints for:
- Listing user's forum chats (filtered by role)
- Getting messages from specific forum chat
- Sending messages to forum chat
- Unread message counts per chat
"""

import logging
import json
from typing import List

from django.db.models import Q, Count, Max, Prefetch, OuterRef, Subquery, Case, When, IntegerField, Value, F, Exists
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from accounts.models import StudentProfile
from .models import ChatRoom, Message, ChatParticipant
from .serializers import ChatRoomListSerializer, MessageSerializer, MessageCreateSerializer

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
                # Save message (will trigger signal for Pachca notification)
                message = serializer.save(sender=request.user, room=chat)

                # Update chat's updated_at timestamp
                chat.save(update_fields=['updated_at'])

                # Broadcast message to all connected WebSocket clients in this chat room
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
