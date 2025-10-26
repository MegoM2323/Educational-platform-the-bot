from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import ChatRoom, Message, MessageRead, ChatParticipant, MessageThread
from .serializers import (
    ChatRoomListSerializer, ChatRoomDetailSerializer, ChatRoomCreateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageReadSerializer,
    ChatParticipantSerializer, ChatRoomStatsSerializer, MessageThreadSerializer,
    MessageThreadCreateSerializer
)
from .general_chat_service import GeneralChatService


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet для чат-комнат
    """
    queryset = ChatRoom.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChatRoomListSerializer
        elif self.action == 'create':
            return ChatRoomCreateSerializer
        return ChatRoomDetailSerializer
    
    def get_queryset(self):
        """
        Пользователи видят только чаты, в которых они участвуют
        """
        user = self.request.user
        return ChatRoom.objects.filter(participants=user)
    
    def perform_create(self, serializer):
        room = serializer.save(created_by=self.request.user)
        # Добавляем создателя в участники
        room.participants.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Присоединиться к чату
        """
        room = self.get_object()
        user = request.user
        
        if room.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Вы уже участвуете в этом чате'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room.participants.add(user)
        return Response({'message': 'Вы присоединились к чату'})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        Покинуть чат
        """
        room = self.get_object()
        user = request.user
        
        if not room.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Вы не участвуете в этом чате'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room.participants.remove(user)
        return Response({'message': 'Вы покинули чат'})
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Получить сообщения чата
        """
        room = self.get_object()
        limit = request.query_params.get('limit', 50)
        offset = request.query_params.get('offset', 0)
        
        messages = room.messages.all()[int(offset):int(offset) + int(limit)]
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Отметить сообщения как прочитанные
        """
        room = self.get_object()
        user = request.user
        
        # Обновляем время последнего прочтения
        participant, created = ChatParticipant.objects.get_or_create(
            room=room,
            user=user
        )
        participant.last_read_at = timezone.now()
        participant.save()
        
        return Response({'message': 'Сообщения отмечены как прочитанные'})
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """
        Получить участников чата
        """
        room = self.get_object()
        participants = room.room_participants.all()
        serializer = ChatParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Получить статистику чатов
        """
        user = request.user
        
        total_rooms = ChatRoom.objects.filter(participants=user).count()
        active_rooms = ChatRoom.objects.filter(participants=user, is_active=True).count()
        
        user_rooms = ChatRoom.objects.filter(participants=user)
        total_messages = Message.objects.filter(room__in=user_rooms).count()
        
        # Подсчитываем непрочитанные сообщения
        unread_messages = 0
        for room in user_rooms:
            try:
                participant = room.room_participants.get(user=user)
                unread_messages += participant.unread_count
            except ChatParticipant.DoesNotExist:
                pass
        
        participants_count = sum(room.participants.count() for room in user_rooms)
        
        stats_data = {
            'total_rooms': total_rooms,
            'active_rooms': active_rooms,
            'total_messages': total_messages,
            'unread_messages': unread_messages,
            'participants_count': participants_count
        }
        
        serializer = ChatRoomStatsSerializer(stats_data)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet для сообщений
    """
    queryset = Message.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['room', 'sender', 'message_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        """
        Пользователи видят только сообщения из чатов, в которых они участвуют
        """
        user = self.request.user
        user_rooms = ChatRoom.objects.filter(participants=user)
        return Message.objects.filter(room__in=user_rooms)
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Отметить сообщение как прочитанное
        """
        message = self.get_object()
        user = request.user
        
        # Проверяем, что пользователь участвует в чате
        if not message.room.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Вы не участвуете в этом чате'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Создаем или обновляем отметку о прочтении
        MessageRead.objects.get_or_create(
            message=message,
            user=user
        )
        
        return Response({'message': 'Сообщение отмечено как прочитанное'})
    
    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """
        Ответить на сообщение
        """
        original_message = self.get_object()
        user = request.user
        
        # Проверяем, что пользователь участвует в чате
        if not original_message.room.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Вы не участвуете в этом чате'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MessageCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(
                room=original_message.room,
                reply_to=original_message
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """
        Получить ответы на сообщение
        """
        message = self.get_object()
        replies = message.replies.all()
        serializer = MessageSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data)


class ChatParticipantViewSet(viewsets.ModelViewSet):
    """
    ViewSet для участников чата
    """
    queryset = ChatParticipant.objects.all()
    serializer_class = ChatParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['room', 'user', 'is_muted', 'is_admin']
    ordering_fields = ['joined_at', 'last_read_at']
    ordering = ['-joined_at']
    
    def get_queryset(self):
        """
        Пользователи видят только участников чатов, в которых они участвуют
        """
        user = self.request.user
        user_rooms = ChatRoom.objects.filter(participants=user)
        return ChatParticipant.objects.filter(room__in=user_rooms)


class GeneralChatViewSet(viewsets.ViewSet):
    """
    ViewSet для общего чата-форума
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """
        Получить общий чат
        """
        try:
            general_chat = GeneralChatService.get_or_create_general_chat()
            serializer = ChatRoomDetailSerializer(general_chat, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def messages(self, request):
        """
        Получить сообщения общего чата
        """
        try:
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            
            messages = GeneralChatService.get_general_chat_messages(limit, offset)
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """
        Отправить сообщение в общий чат
        """
        try:
            content = request.data.get('content')
            message_type = request.data.get('message_type', Message.Type.TEXT)
            
            if not content:
                return Response(
                    {'error': 'Содержание сообщения обязательно'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            message = GeneralChatService.send_general_message(
                sender=request.user,
                content=content,
                message_type=message_type
            )
            
            serializer = MessageSerializer(message, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def threads(self, request):
        """
        Получить треды общего чата
        """
        try:
            limit = int(request.query_params.get('limit', 20))
            offset = int(request.query_params.get('offset', 0))
            
            threads = GeneralChatService.get_general_chat_threads(limit, offset)
            serializer = MessageThreadSerializer(threads, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_thread(self, request):
        """
        Создать новый тред
        """
        try:
            title = request.data.get('title')
            
            if not title:
                return Response(
                    {'error': 'Заголовок треда обязателен'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            general_chat = GeneralChatService.get_or_create_general_chat()
            thread = GeneralChatService.create_thread(
                room=general_chat,
                title=title,
                created_by=request.user
            )
            
            serializer = MessageThreadSerializer(thread, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageThreadViewSet(viewsets.ModelViewSet):
    """
    ViewSet для тредов сообщений
    """
    queryset = MessageThread.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['room', 'created_by', 'is_pinned', 'is_locked']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-is_pinned', '-updated_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageThreadCreateSerializer
        return MessageThreadSerializer
    
    def get_queryset(self):
        """
        Пользователи видят только треды из чатов, в которых они участвуют
        """
        user = self.request.user
        user_rooms = ChatRoom.objects.filter(participants=user)
        return MessageThread.objects.filter(room__in=user_rooms)
    
    def perform_create(self, serializer):
        general_chat = GeneralChatService.get_or_create_general_chat()
        serializer.save(room=general_chat)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Получить сообщения треда
        """
        try:
            thread = self.get_object()
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            
            messages = GeneralChatService.get_thread_messages(thread, limit, offset)
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Отправить сообщение в тред
        """
        try:
            thread = self.get_object()
            content = request.data.get('content')
            message_type = request.data.get('message_type', Message.Type.TEXT)
            
            if not content:
                return Response(
                    {'error': 'Содержание сообщения обязательно'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            message = GeneralChatService.send_message_to_thread(
                room=thread.room,
                thread=thread,
                sender=request.user,
                content=content,
                message_type=message_type
            )
            
            serializer = MessageSerializer(message, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """
        Закрепить тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.pin_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={'request': request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        """
        Открепить тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.unpin_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={'request': request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """
        Заблокировать тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.lock_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={'request': request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """
        Разблокировать тред
        """
        try:
            thread = self.get_object()
            GeneralChatService.unlock_thread(thread, request.user)
            serializer = MessageThreadSerializer(thread, context={'request': request})
            return Response(serializer.data)
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )