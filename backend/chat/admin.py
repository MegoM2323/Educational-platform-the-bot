from django.contrib import admin
from .models import ChatRoom, Message, ChatParticipant


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["id", "participant_count", "created_at", "updated_at", "is_active"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["id"]
    readonly_fields = ["created_at", "updated_at", "id"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Информация", {"fields": ("id", "is_active")}),
        ("Участники", {"fields": ("participants",)}),
        (
            "Временные метки",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def participant_count(self, obj):
        return obj.participants.count()

    participant_count.short_description = "Участников"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "sender", "message_type", "created_at", "is_edited", "is_deleted"]
    list_filter = ["message_type", "is_edited", "is_deleted", "created_at"]
    search_fields = ["room__id", "sender__username", "sender__email", "content"]
    readonly_fields = ["created_at", "updated_at", "id"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Контент", {"fields": ("id", "room", "sender", "content", "message_type")}),
        ("Статус", {"fields": ("is_edited", "is_deleted", "deleted_at")}),
        (
            "Временные метки",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def has_delete_permission(self, request, obj=None):
        # Использовать soft delete (is_deleted=True) вместо hard delete
        return False


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "user", "joined_at", "last_read_at", "is_muted"]
    list_filter = ["is_muted", "joined_at"]
    search_fields = ["room__id", "user__username", "user__email"]
    readonly_fields = ["joined_at", "id"]
    date_hierarchy = "joined_at"

    fieldsets = (
        ("Связь", {"fields": ("id", "room", "user")}),
        ("Статус", {"fields": ("is_muted",)}),
        ("Временные метки", {"fields": ("joined_at", "last_read_at")}),
    )
