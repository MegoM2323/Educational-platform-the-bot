from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, MessageRead, ChatParticipant

User = get_user_model()


class ChatRoomListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка чат-комнат
    """
    participants_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'description', 'type', 'participants_count',
            'is_active', 'created_at', 'updated_at', 'last_message', 'unread_count'
        )
    
    def get_participants_count(self, obj):
        return obj.participants.count()
    
    def get_last_message(self, obj):
        last_msg = obj.last_message
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100],
                'sender': last_msg.sender.get_full_name(),
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                participant = obj.room_participants.get(user=request.user)
                return participant.unread_count
            except ChatParticipant.DoesNotExist:
                return 0
        return 0


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального просмотра чат-комнаты
    """
    participants = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'description', 'type', 'participants',
            'created_by', 'is_active', 'created_at', 'updated_at', 'messages'
        )
    
    def get_participants(self, obj):
        return [{
            'id': user.id,
            'name': user.get_full_name(),
            'role': user.role,
            'avatar': user.avatar.url if user.avatar else None
        } for user in obj.participants.all()]
    
    def get_messages(self, obj):
        messages = obj.messages.all()[:50]  # Последние 50 сообщений
        return MessageSerializer(messages, many=True).data


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания чат-комнаты
    """
    class Meta:
        model = ChatRoom
        fields = ('name', 'description', 'type', 'participants')
    
    def create(self, validated_data):
        participants = validated_data.pop('participants', [])
        room = ChatRoom.objects.create(
            created_by=self.context['request'].user,
            **validated_data
        )
        room.participants.set(participants)
        return room


class MessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для сообщений
    """
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = (
            'id', 'room', 'sender', 'sender_name', 'sender_avatar',
            'content', 'message_type', 'file', 'image', 'is_edited',
            'reply_to', 'created_at', 'updated_at', 'is_read', 'replies_count'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            return obj.sender.avatar.url
        return None
    
    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_by.filter(user=request.user).exists()
        return False
    
    def get_replies_count(self, obj):
        return obj.replies.count()
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания сообщения
    """
    class Meta:
        model = Message
        fields = ('room', 'content', 'message_type', 'file', 'image', 'reply_to')
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class MessageReadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отметок о прочтении
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = MessageRead
        fields = ('id', 'message', 'user', 'user_name', 'read_at')
        read_only_fields = ('id', 'read_at')


class ChatParticipantSerializer(serializers.ModelSerializer):
    """
    Сериализатор для участников чата
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ChatParticipant
        fields = (
            'id', 'room', 'user', 'user_name', 'user_role', 'user_avatar',
            'joined_at', 'last_read_at', 'is_muted', 'is_admin', 'unread_count'
        )
        read_only_fields = ('id', 'joined_at')
    
    def get_user_avatar(self, obj):
        if obj.user.avatar:
            return obj.user.avatar.url
        return None


class ChatRoomStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики чата
    """
    total_rooms = serializers.IntegerField()
    active_rooms = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    participants_count = serializers.IntegerField()
