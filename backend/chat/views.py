from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import ChatRoom, Message, MessageRead, ChatParticipant
from .serializers import (
    ChatRoomListSerializer, ChatRoomDetailSerializer, ChatRoomCreateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageReadSerializer,
    ChatParticipantSerializer, ChatRoomStatsSerializer
)


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