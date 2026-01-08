from django.contrib import admin
from .models import ChatRoom, Message, ChatParticipant


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "updated_at", "is_active"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["id"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Основная информация", {"fields": ("is_active",)}),
        ("Участники", {"fields": ("participants",)}),
        (
            "Временные метки",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "sender", "created_at", "is_deleted"]
    list_filter = ["is_deleted", "created_at"]
    search_fields = ["room__id", "sender__email", "content"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Основная информация", {"fields": ("room", "sender", "content")}),
        ("Статус", {"fields": ("is_edited", "is_deleted", "deleted_at")}),
        (
            "Временные метки",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "user", "joined_at", "last_read_at"]
    list_filter = ["joined_at"]
    search_fields = ["room__id", "user__email"]
    readonly_fields = ["joined_at"]

    fieldsets = (
        ("Основная информация", {"fields": ("room", "user")}),
        ("Временные метки", {"fields": ("joined_at", "last_read_at")}),
    )
