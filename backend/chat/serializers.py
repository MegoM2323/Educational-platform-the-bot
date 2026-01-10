from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatParticipant, Message

User = get_user_model()


class UserSimpleSerializer(serializers.ModelSerializer):
    """Сериализатор для информации о пользователе (упрощённая версия)"""

    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "full_name", "role")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_role(self, obj):
        return getattr(obj, "role", "user")


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщений"""

    sender = UserSimpleSerializer(read_only=True)
    message_type = serializers.CharField(read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "message_type",
            "content",
            "created_at",
            "updated_at",
            "is_edited",
        )
        read_only_fields = ("id", "sender", "created_at", "updated_at", "is_edited")


class MessageCreateSerializer(serializers.Serializer):
    """Сериализатор для создания сообщения через WebSocket.

    Примечание: message_type не поддерживается в текущей версии.
    Все сообщения обрабатываются как текст.
    """

    content = serializers.CharField(
        max_length=10000,
        min_length=1,
        trim_whitespace=True,
        error_messages={
            "required": "Message content is required.",
            "blank": "Message content cannot be empty.",
            "max_length": "Message content cannot exceed 10000 characters.",
            "min_length": "Message content must be at least 1 character.",
        },
    )

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value


class MessageUpdateSerializer(serializers.Serializer):
    """Сериализатор для обновления сообщения"""

    content = serializers.CharField(max_length=10000, min_length=1)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()


class ChatParticipantSerializer(serializers.ModelSerializer):
    """Сериализатор для участников чата"""

    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = ChatParticipant
        fields = ("id", "user", "joined_at", "last_read_at")
        read_only_fields = ("id", "joined_at", "last_read_at")


class ChatRoomListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка чатов.
    Включает информацию об участниках, последнем сообщении и количестве непрочитанных.
    """

    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_group = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = (
            "id",
            "name",
            "type",
            "subject",
            "other_participant",
            "last_message",
            "unread_count",
            "is_group",
            "updated_at",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_other_participant(self, obj):
        """Получить информацию о другом участнике (для direct чатов)"""
        request = self.context.get("request")
        if not request:
            return None

        participants = getattr(obj, "_prefetched_participants", obj.participants.all())
        if len(participants) != 2:
            return None

        other_user = None
        for p in participants:
            if p.user_id != request.user.id:
                other_user = p.user
                break

        if not other_user:
            return None

        return {
            "id": other_user.id,
            "full_name": f"{other_user.first_name} {other_user.last_name}".strip(),
            "role": getattr(other_user, "role", "user"),
        }

    def get_last_message(self, obj):
        """Использует аннотацию last_message_content из ChatService.get_user_chats()"""
        if hasattr(obj, "last_message_content") and obj.last_message_content:
            return {
                "content": obj.last_message_content[:100],
                "created_at": getattr(obj, "last_message_time", None),
            }
        return None

    def get_unread_count(self, obj):
        """Использует аннотацию unread_count из ChatService.get_user_chats()"""
        if hasattr(obj, "unread_count"):
            return obj.unread_count or 0

        request = self.context.get("request")
        if not request:
            return 0

        try:
            participants = getattr(obj, "_prefetched_participants", [])
            participant = None
            for p in participants:
                if p.user_id == request.user.id:
                    participant = p
                    break

            if not participant:
                participant = obj.participants.get(user=request.user)

            last_read = participant.last_read_at

            if not last_read:
                return (
                    obj.messages.filter(is_deleted=False)
                    .exclude(sender=request.user)
                    .count()
                )

            return (
                obj.messages.filter(
                    is_deleted=False,
                    created_at__gt=last_read,
                )
                .exclude(sender=request.user)
                .count()
            )
        except ChatParticipant.DoesNotExist:
            return 0

    def get_is_group(self, obj):
        """Определить, является ли чат групповым (более 2 участников).

        Использует len() вместо count() для работы с prefetch_related.
        Если prefetch_related не был использован, len() все равно работает,
        но может вызвать дополнительный запрос. Это нормально для edge cases.
        """
        participants = getattr(obj, "_prefetched_participants", obj.participants.all())
        return len(participants) > 2

    def get_name(self, obj):
        """Получить имя чата. Для direct чата - имя другого участника, для группового - 'Групповой чат {id}'"""
        participants = getattr(obj, "_prefetched_participants", obj.participants.all())
        if len(participants) == 2:
            request = self.context.get("request")
            if not request:
                return None

            other_user = None
            for p in participants:
                if p.user_id != request.user.id:
                    other_user = p.user
                    break

            if other_user:
                return (
                    f"{other_user.first_name} {other_user.last_name}".strip()
                    or other_user.username
                )

        return f"Групповой чат {obj.id}"

    def get_type(self, obj):
        """Получить тип чата: 'direct' для 2 участников, 'group' для остальных"""
        participants = getattr(obj, "_prefetched_participants", obj.participants.all())
        participants_count = len(participants)
        return "direct" if participants_count == 2 else "group"

    def get_subject(self, obj):
        """Получить тему чата (заглушка)"""
        return None


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального просмотра чата.
    Включает информацию об участниках.
    """

    participants = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ("id", "participants", "created_at", "is_active")
        read_only_fields = ("id", "created_at", "is_active")

    def get_participants(self, obj):
        """Получить список участников"""
        participants = getattr(obj, "_prefetched_participants", obj.participants.all())
        return [
            {
                "id": p.user.id,
                "full_name": f"{p.user.first_name} {p.user.last_name}".strip(),
                "role": getattr(p.user, "role", "user"),
            }
            for p in participants
        ]


class ChatRoomCreateSerializer(serializers.Serializer):
    """Сериализатор для создания чата"""

    recipient_id = serializers.IntegerField()

    def validate_recipient_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class ContactSerializer(serializers.Serializer):
    """Сериализатор для контакта в списке доступных контактов"""

    id = serializers.IntegerField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    has_existing_chat = serializers.BooleanField()
    existing_chat_id = serializers.IntegerField(allow_null=True)
