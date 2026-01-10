from django.db import models
from django.conf import settings


class ChatRoom(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Чат-комната"
        verbose_name_plural = "Чат-комнаты"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["-updated_at"], name="idx_chat_room_updated"),
            models.Index(fields=["is_active"], name="idx_chat_room_active"),
        ]

    def __str__(self):
        return f"Chat {self.id}"


class ChatParticipant(models.Model):
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Участник чата"
        verbose_name_plural = "Участники чата"
        unique_together = [("room", "user")]
        indexes = [
            models.Index(
                fields=["user", "room"], name="idx_chat_participant_user_room"
            ),
            models.Index(fields=["room"], name="idx_chat_participant_room"),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.room.id}"


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ("text", "Текст"),
        ("image", "Изображение"),
        ("file", "Файл"),
        ("system", "Системное"),
    ]

    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default="text",
        verbose_name="Тип сообщения"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["room", "created_at"], name="idx_message_room_created"
            ),
            models.Index(
                fields=["room", "is_deleted"], name="idx_message_room_deleted"
            ),
        ]

    def __str__(self):
        return f"Message {self.id} by {self.sender.username}"
