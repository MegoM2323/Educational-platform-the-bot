import logging
import os

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, MessageRead, ChatParticipant, MessageThread

User = get_user_model()
logger = logging.getLogger(__name__)


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
            "id",
            "name",
            "description",
            "type",
            "participants_count",
            "participants",
            "subject",
            "is_active",
            "created_at",
            "updated_at",
            "last_message",
            "unread_count",
        )

    def get_participants_count(self, obj):
        # Use annotated value from queryset to avoid N+1 query
        if hasattr(obj, "annotated_participants_count"):
            return obj.annotated_participants_count
        # Fallback for non-annotated querysets
        return obj.participants.count()

    def get_participants(self, obj):
        """
        Return full participant objects for frontend ForumChat interface.

        Оптимизация N+1: использует prefetched данные если доступны.
        Требуется prefetch_related('participants') в view queryset.
        """
        # Проверяем prefetched данные (избегаем N+1 query)
        # obj.participants.all() использует prefetched cache если доступен
        return [
            {"id": user.id, "full_name": user.get_full_name(), "role": user.role}
            for user in obj.participants.all()
        ]

    def get_subject(self, obj):
        """Return subject if chat is forum_subject type"""
        if obj.type == ChatRoom.Type.FORUM_SUBJECT and obj.enrollment and obj.enrollment.subject:
            return {"id": obj.enrollment.subject.id, "name": obj.enrollment.subject.name}
        return None

    def get_last_message(self, obj):
        last_msg = obj.last_message
        if last_msg:
            return {
                "id": last_msg.id,
                "content": last_msg.content[:100],
                "sender": {
                    "id": last_msg.sender.id,
                    "full_name": last_msg.sender.get_full_name(),
                    "role": last_msg.sender.role,
                },
                "created_at": last_msg.created_at,
            }
        return None

    def get_unread_count(self, obj):
        """
        Возвращает количество непрочитанных сообщений для текущего пользователя.

        Оптимизация N+1:
        1. Использует аннотированное значение annotated_unread_count (самый быстрый)
        2. Fallback возвращает 0 без запроса к БД

        ВАЖНО: НЕ делаем запрос к БД в fallback - это предотвращает N+1 queries.
        Если аннотация отсутствует, возвращаем 0.
        """
        # Приоритет 1: Аннотированное значение из queryset (самый оптимальный)
        if hasattr(obj, "annotated_unread_count"):
            return obj.annotated_unread_count or 0

        # Fallback: НЕ делаем запрос к БД - возвращаем 0
        # Это предотвращает N+1 queries при отсутствии аннотации
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
            "id",
            "name",
            "description",
            "type",
            "participants",
            "created_by",
            "is_active",
            "created_at",
            "updated_at",
            "messages",
        )

    def get_participants(self, obj):
        request = self.context.get("request")
        return [
            {
                "id": user.id,
                "name": user.get_full_name(),
                "role": user.role,
                "avatar": request.build_absolute_uri(user.avatar.url)
                if (user.avatar and request)
                else (user.avatar.url if user.avatar else None),
            }
            for user in obj.participants.all()
        ]

    def get_messages(self, obj):
        # Prefetch related data and filter properly for optimal performance
        messages = (
            obj.messages.filter(is_deleted=False)
            .select_related("sender")
            .order_by("-created_at")[:50]
        )
        return MessageSerializer(messages, many=True, context=self.context).data


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания чат-комнаты
    """

    class Meta:
        model = ChatRoom
        fields = ("name", "description", "type", "participants")

    def create(self, validated_data):
        participants = validated_data.pop("participants", [])
        room = ChatRoom.objects.create(created_by=self.context["request"].user, **validated_data)
        room.participants.set(participants)
        return room


class MessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для сообщений.

    Оптимизация N+1 queries:
    - replies_count: использует аннотацию из queryset или prefetched данные
    - is_read: использует prefetched read_by данные
    - sender поля: требуют select_related('sender') в queryset

    Требования к queryset для оптимальной производительности:
    - select_related('sender', 'thread', 'reply_to__sender')
    - prefetch_related('replies', 'read_by')
    - annotate(annotated_replies_count=Count('replies', filter=Q(replies__is_deleted=False)))
    """

    sender = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    is_read = serializers.SerializerMethodField()
    # Поддерживает аннотированное значение из queryset (annotated_replies_count)
    # или fallback на prefetched/direct count
    replies_count = serializers.SerializerMethodField()
    thread_title = serializers.CharField(source="thread.title", read_only=True)
    is_pinned = serializers.SerializerMethodField()
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
            "id",
            "room",
            "thread",
            "thread_title",
            "sender",
            "sender_name",
            "sender_avatar",
            "sender_role",
            "content",
            "message_type",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "file_type",
            "image",
            "image_url",
            "is_image",
            "is_edited",
            "reply_to",
            "created_at",
            "updated_at",
            "is_read",
            "is_pinned",
            "replies_count",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_sender(self, obj):
        """Return full sender object for frontend ForumMessage interface"""
        return {
            "id": obj.sender.id,
            "full_name": obj.sender.get_full_name(),
            "role": obj.sender.role,
        }

    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.sender.avatar.url)
            return obj.sender.avatar.url
        return None

    def get_file_url(self, obj):
        """Возвращает абсолютный URL файла"""
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_image_url(self, obj):
        """Возвращает абсолютный URL изображения"""
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_file_name(self, obj):
        """Возвращает имя файла (file или image)"""
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
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"}
        archive_extensions = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}

        # Проверяем image поле
        if obj.image and obj.image.name:
            return "image"

        # Проверяем file поле
        if obj.file and obj.file.name:
            _, ext = os.path.splitext(obj.file.name.lower())
            if ext in image_extensions:
                return "image"
            if ext in archive_extensions:
                return "archive"
            return "document"

        return None

    def get_is_image(self, obj):
        """Проверяет, является ли вложение изображением"""
        # Если есть image поле - это изображение
        if obj.image and obj.image.name:
            return True

        # Проверяем file поле по расширению
        if obj.file and obj.file.name:
            image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"}
            _, ext = os.path.splitext(obj.file.name.lower())
            return ext in image_extensions

        return False

    def get_is_read(self, obj):
        """
        Проверяет, прочитано ли сообщение текущим пользователем.

        Оптимизация: использует prefetched read_by данные если доступны,
        избегая N+1 запросов при итерации по списку сообщений.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        user_id = request.user.id

        # Проверяем prefetched данные (read_by уже загружены)
        # Если prefetch_related('read_by') был вызван, _prefetched_cache будет содержать данные
        if hasattr(obj, "_prefetched_objects_cache") and "read_by" in obj._prefetched_objects_cache:
            # Используем prefetched данные без дополнительного запроса
            return any(read.user_id == user_id for read in obj.read_by.all())

        # Fallback: прямой запрос (для единичных объектов или без prefetch)
        return obj.read_by.filter(user_id=user_id).exists()

    def get_replies_count(self, obj):
        """
        Возвращает количество ответов на сообщение.
        Требует аннотации annotated_replies_count в view.

        Не делает N+1 запросы - если аннотация отсутствует, возвращает 0 и логирует warning.
        """
        # Аннотированное значение из queryset (оптимальный способ)
        if hasattr(obj, "annotated_replies_count"):
            return obj.annotated_replies_count

        # Не делаем N+1 query - возвращаем 0 и логируем warning
        logger.warning(f"Message {obj.id} missing annotated_replies_count annotation")
        return 0

    def get_is_pinned(self, obj):
        """
        Возвращает, закреплено ли сообщение в своем треде.

        Проверяет, принадлежит ли сообщение закреплённому треду.
        Требует select_related('thread') в queryset для оптимальной производительности.
        """
        if obj.thread and obj.thread.is_pinned:
            return True
        return False

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания сообщения.

    Поле content может быть пустым если прикреплён файл.
    """

    content = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Message
        fields = ("room", "content", "message_type", "reply_to")

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class MessageUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления сообщения"""

    class Meta:
        model = Message
        fields = ["content"]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Сообщение не может быть пустым")
        if len(value) > 5000:
            raise serializers.ValidationError("Сообщение слишком длинное (максимум 5000 символов)")
        return value.strip()

    def update(self, instance, validated_data):
        instance.content = validated_data.get("content", instance.content)
        instance.is_edited = True
        instance.save(update_fields=["content", "is_edited", "updated_at"])
        return instance


class MessageReadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отметок о прочтении
    """

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = MessageRead
        fields = ("id", "message", "user", "user_name", "read_at")
        read_only_fields = ("id", "read_at")


class ChatParticipantSerializer(serializers.ModelSerializer):
    """
    Сериализатор для участников чата
    """

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    user_avatar = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatParticipant
        fields = (
            "id",
            "room",
            "user",
            "user_name",
            "user_role",
            "user_avatar",
            "joined_at",
            "last_read_at",
            "is_muted",
            "is_admin",
            "unread_count",
        )
        read_only_fields = ("id", "joined_at")

    def get_user_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None


class MessageThreadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для тредов сообщений
    """

    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    created_by_role = serializers.CharField(source="created_by.role", read_only=True)
    messages_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = MessageThread
        fields = (
            "id",
            "room",
            "title",
            "created_by",
            "created_by_name",
            "created_by_role",
            "is_pinned",
            "is_locked",
            "created_at",
            "updated_at",
            "messages_count",
            "last_message",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_last_message(self, obj):
        last_msg = obj.last_message
        if last_msg:
            return {
                "id": last_msg.id,
                "content": last_msg.content[:100],
                "sender": last_msg.sender.get_full_name(),
                "created_at": last_msg.created_at,
            }
        return None


class MessageThreadCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания треда
    """

    class Meta:
        model = MessageThread
        fields = ("title",)

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        validated_data["room"] = self.context["room"]
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
            "id",
            "room_id",
            "type",
            "other_user",
            "created_at",
            "last_message",
            "unread_count",
            "name",
        )

    def get_room_id(self, obj):
        """Возвращает room_id для WebSocket подключения"""
        return f"chat_room_{obj.id}"

    def get_other_user(self, obj):
        """Возвращает информацию о собеседнике"""
        request = self.context.get("request")
        if not request or not request.user:
            return None

        # Получаем другого участника чата (не текущего пользователя)
        other_users = obj.participants.exclude(id=request.user.id)
        if not other_users.exists():
            return None

        other_user = other_users.first()
        return {
            "id": other_user.id,
            "first_name": other_user.first_name,
            "last_name": other_user.last_name,
            "email": other_user.email,
            "avatar": request.build_absolute_uri(other_user.avatar.url)
            if other_user.avatar
            else None,
        }

    def get_last_message(self, obj):
        """Возвращает последнее сообщение (если есть)"""
        last_msg = obj.last_message
        if last_msg:
            return {
                "id": last_msg.id,
                "content": last_msg.content[:100],
                "sender_id": last_msg.sender.id,
                "created_at": last_msg.created_at,
            }
        return None

    def get_unread_count(self, obj):
        """Возвращает количество непрочитанных сообщений"""
        request = self.context.get("request")
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
    user_id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    is_teacher = serializers.SerializerMethodField()
    is_tutor = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    has_active_chat = serializers.BooleanField()
    chat_id = serializers.IntegerField(allow_null=True)

    def get_id(self, obj):
        """Extract user ID from contact dict"""
        return obj["user"].id

    def get_user_id(self, obj):
        """Extract user ID (alias for id)"""
        return obj["user"].id

    def get_email(self, obj):
        """Extract user email from contact dict"""
        return obj["user"].email

    def get_first_name(self, obj):
        """Extract user first_name from contact dict"""
        return obj["user"].first_name

    def get_last_name(self, obj):
        """Extract user last_name from contact dict"""
        return obj["user"].last_name

    def get_full_name(self, obj):
        """Extract user full name from contact dict"""
        return obj["user"].get_full_name()

    def get_role(self, obj):
        """Extract user role from contact dict"""
        return obj["user"].role

    def get_is_teacher(self, obj):
        """Check if contact is a teacher"""
        return obj["user"].role == "teacher"

    def get_is_tutor(self, obj):
        """Check if contact is a tutor"""
        return obj["user"].role == "tutor"

    def get_avatar(self, obj):
        """Extract user avatar URL from contact dict"""
        user = obj["user"]
        if user.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(user.avatar.url)
            return user.avatar.url
        return None

    def get_avatar_url(self, obj):
        """Alias for avatar field for compatibility"""
        return self.get_avatar(obj)

    def get_subject(self, obj):
        """Extract subject info if available"""
        subject = obj.get("subject")
        if subject:
            return {"id": subject.id, "name": subject.name}
        return None
