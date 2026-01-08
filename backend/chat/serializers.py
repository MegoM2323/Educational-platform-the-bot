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

    class Meta:
        model = Message
        fields = ("id", "sender", "content", "created_at", "updated_at", "is_edited")
        read_only_fields = ("id", "sender", "created_at", "updated_at", "is_edited")


class MessageCreateSerializer(serializers.Serializer):
    """Сериализатор для создания сообщения"""

    content = serializers.CharField(max_length=10000, min_length=1)

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()


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

    class Meta:
        model = ChatRoom
        fields = (
            "id",
            "other_participant",
            "last_message",
            "unread_count",
            "updated_at",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_other_participant(self, obj):
        """Получить информацию о другом участнике (для direct чатов)"""
        request = self.context.get("request")
        if not request:
            return None

        participants = list(obj.participants.all())
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
        # Проверяем наличие аннотаций из сервиса (которые добавляет get_user_chats)
        if hasattr(obj, "last_message_content") and obj.last_message_content:
            return {
                "content": obj.last_message_content[:100],
                "created_at": getattr(obj, "last_message_time", None),
            }
        return None

    def get_unread_count(self, obj):
        """Использует аннотацию unread_count из ChatService.get_user_chats()"""
        # Используем аннотацию из сервиса если есть
        if hasattr(obj, "unread_count"):
            return obj.unread_count or 0

        # Fallback для случаев когда аннотации нет
        request = self.context.get("request")
        if not request:
            return 0

        try:
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
        return [
            {
                "id": p.user.id,
                "full_name": f"{p.user.first_name} {p.user.last_name}".strip(),
                "role": getattr(p.user, "role", "user"),
            }
            for p in obj.participants.all()
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
