from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, MessageRead, ChatParticipant, MessageThread

User = get_user_model()


class ChatRoomListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка чат-комнат
    """
    participants_count = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'description', 'type', 'participants_count', 'participants',
            'subject', 'is_active', 'created_at', 'updated_at', 'last_message', 'unread_count'
        )

    def get_participants_count(self, obj):
        # Use annotated value from queryset to avoid N+1 query
        if hasattr(obj, 'annotated_participants_count'):
            return obj.annotated_participants_count
        # Fallback for non-annotated querysets
        return obj.participants.count()

    def get_participants(self, obj):
        """Return full participant objects for frontend ForumChat interface"""
        return [{
            'id': user.id,
            'full_name': user.get_full_name(),
            'role': user.role
        } for user in obj.participants.all()]

    def get_subject(self, obj):
        """Return subject if chat is forum_subject type"""
        if obj.type == ChatRoom.Type.FORUM_SUBJECT and obj.enrollment and obj.enrollment.subject:
            return {
                'id': obj.enrollment.subject.id,
                'name': obj.enrollment.subject.name
            }
        return None

    def get_last_message(self, obj):
        last_msg = obj.last_message
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100],
                'sender': {
                    'id': last_msg.sender.id,
                    'full_name': last_msg.sender.get_full_name(),
                    'role': last_msg.sender.role
                },
                'created_at': last_msg.created_at
            }
        return None

    def get_unread_count(self, obj):
        # Use prefetched participant to avoid N+1 query
        # ForumChatViewSet prefetches 'current_user_participant'
        if hasattr(obj, 'current_user_participant') and obj.current_user_participant:
            participant = obj.current_user_participant[0]
            return participant.unread_count

        # Fallback for non-prefetched querysets (e.g., in tests, other views)
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
        request = self.context.get('request')
        return [{
            'id': user.id,
            'name': user.get_full_name(),
            'role': user.role,
            'avatar': request.build_absolute_uri(user.avatar.url) if (user.avatar and request) else (user.avatar.url if user.avatar else None)
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
    sender = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    is_read = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    thread_title = serializers.CharField(source='thread.title', read_only=True)
    file_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    # Метаданные файла для frontend
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            'id', 'room', 'thread', 'thread_title', 'sender', 'sender_name', 'sender_avatar', 'sender_role',
            'content', 'message_type', 'file', 'file_url', 'file_name', 'file_size', 'file_type',
            'image', 'image_url', 'is_image', 'is_edited',
            'reply_to', 'created_at', 'updated_at', 'is_read', 'replies_count'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_sender(self, obj):
        """Return full sender object for frontend ForumMessage interface"""
        return {
            'id': obj.sender.id,
            'full_name': obj.sender.get_full_name(),
            'role': obj.sender.role
        }
    
    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.sender.avatar.url)
            return obj.sender.avatar.url
        return None
    
    def get_file_url(self, obj):
        """Возвращает абсолютный URL файла"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_image_url(self, obj):
        """Возвращает абсолютный URL изображения"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_file_name(self, obj):
        """Возвращает имя файла (file или image)"""
        import os
        if obj.file:
            return os.path.basename(obj.file.name)
        if obj.image:
            return os.path.basename(obj.image.name)
        return None

    def get_file_size(self, obj):
        """Возвращает размер файла в байтах"""
        try:
            if obj.file and obj.file.name:
                return obj.file.size
            if obj.image and obj.image.name:
                return obj.image.size
        except (OSError, ValueError):
            # Файл может не существовать на диске
            return None
        return None

    def get_file_type(self, obj):
        """
        Возвращает тип файла: 'image', 'document', 'archive'
        Определяется по расширению файла
        """
        import os

        # Расширения для определения типа
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico'}
        archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}

        # Проверяем image поле
        if obj.image and obj.image.name:
            return 'image'

        # Проверяем file поле
        if obj.file and obj.file.name:
            _, ext = os.path.splitext(obj.file.name.lower())
            if ext in image_extensions:
                return 'image'
            if ext in archive_extensions:
                return 'archive'
            return 'document'

        return None

    def get_is_image(self, obj):
        """Проверяет, является ли вложение изображением"""
        # Если есть image поле - это изображение
        if obj.image and obj.image.name:
            return True

        # Проверяем file поле по расширению
        if obj.file and obj.file.name:
            import os
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico'}
            _, ext = os.path.splitext(obj.file.name.lower())
            return ext in image_extensions

        return False

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
    Сериализатор для создания сообщения.

    Поле content может быть пустым если прикреплён файл.
    """
    content = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Message
        fields = ('room', 'content', 'message_type', 'reply_to')

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class MessageUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления сообщения"""

    class Meta:
        model = Message
        fields = ['content']

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Сообщение не может быть пустым')
        if len(value) > 5000:
            raise serializers.ValidationError('Сообщение слишком длинное (максимум 5000 символов)')
        return value.strip()

    def update(self, instance, validated_data):
        instance.content = validated_data.get('content', instance.content)
        instance.is_edited = True
        instance.save(update_fields=['content', 'is_edited', 'updated_at'])
        return instance


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
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None


class MessageThreadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для тредов сообщений
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    created_by_role = serializers.CharField(source='created_by.role', read_only=True)
    messages_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageThread
        fields = (
            'id', 'room', 'title', 'created_by', 'created_by_name', 'created_by_role',
            'is_pinned', 'is_locked', 'created_at', 'updated_at', 'messages_count', 'last_message'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
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


class MessageThreadCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания треда
    """
    class Meta:
        model = MessageThread
        fields = ('title',)
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['room'] = self.context['room']
        return super().create(validated_data)


class ChatRoomStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики чата
    """
    total_rooms = serializers.IntegerField()
    active_rooms = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    participants_count = serializers.IntegerField()


class InitiateChatRequestSerializer(serializers.Serializer):
    """
    Сериализатор для запроса создания чата
    """
    contact_user_id = serializers.IntegerField(required=True)
    subject_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_contact_user_id(self, value):
        """Проверка существования пользователя"""
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Contact user not found")
        return value

    def validate_subject_id(self, value):
        """Проверка существования предмета"""
        if value is not None:
            from materials.models import Subject
            if not Subject.objects.filter(id=value).exists():
                raise serializers.ValidationError("Subject not found")
        return value


class ChatDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального ответа при создании чата
    """
    room_id = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = (
            'id', 'room_id', 'type', 'other_user', 'created_at',
            'last_message', 'unread_count', 'name'
        )

    def get_room_id(self, obj):
        """Возвращает room_id для WebSocket подключения"""
        return f"chat_room_{obj.id}"

    def get_other_user(self, obj):
        """Возвращает информацию о собеседнике"""
        request = self.context.get('request')
        if not request or not request.user:
            return None

        # Получаем другого участника чата (не текущего пользователя)
        other_users = obj.participants.exclude(id=request.user.id)
        if not other_users.exists():
            return None

        other_user = other_users.first()
        return {
            'id': other_user.id,
            'first_name': other_user.first_name,
            'last_name': other_user.last_name,
            'email': other_user.email,
            'avatar': request.build_absolute_uri(other_user.avatar.url) if other_user.avatar else None
        }

    def get_last_message(self, obj):
        """Возвращает последнее сообщение (если есть)"""
        last_msg = obj.last_message
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content[:100],
                'sender_id': last_msg.sender.id,
                'created_at': last_msg.created_at
            }
        return None

    def get_unread_count(self, obj):
        """Возвращает количество непрочитанных сообщений"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0

        try:
            participant = obj.room_participants.get(user=request.user)
            return participant.unread_count
        except ChatParticipant.DoesNotExist:
            return 0


class AvailableContactSerializer(serializers.Serializer):
    """
    Serializer for available contacts (users you can initiate chats with).

    Returns user info along with chat status and subject info.
    """
    id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    has_active_chat = serializers.BooleanField()
    chat_id = serializers.IntegerField(allow_null=True)

    def get_id(self, obj):
        """Extract user ID from contact dict"""
        return obj['user'].id

    def get_email(self, obj):
        """Extract user email from contact dict"""
        return obj['user'].email

    def get_first_name(self, obj):
        """Extract user first_name from contact dict"""
        return obj['user'].first_name

    def get_last_name(self, obj):
        """Extract user last_name from contact dict"""
        return obj['user'].last_name

    def get_role(self, obj):
        """Extract user role from contact dict"""
        return obj['user'].role

    def get_avatar(self, obj):
        """Extract user avatar URL from contact dict"""
        user = obj['user']
        if user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(user.avatar.url)
            return user.avatar.url
        return None

    def get_subject(self, obj):
        """Extract subject info if available"""
        subject = obj.get('subject')
        if subject:
            return {
                'id': subject.id,
                'name': subject.name
            }
        return None

