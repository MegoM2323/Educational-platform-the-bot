from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ChatRoom, Message, MessageRead, ChatParticipant


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender', 'created_at']
    fields = ['sender', 'content', 'message_type', 'created_at']


class ChatParticipantInline(admin.TabularInline):
    model = ChatParticipant
    extra = 0
    readonly_fields = ['joined_at']
    fields = ['user', 'is_admin', 'is_muted', 'joined_at', 'last_read_at']


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """
    Админка для чат-комнат
    """
    list_display = [
        'name', 'type_badge', 'created_by', 'participants_count', 
        'messages_count', 'is_active_badge', 'created_at'
    ]
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['participants']
    inlines = [ChatParticipantInline, MessageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'type', 'created_by')
        }),
        ('Настройки', {
            'fields': ('is_active',)
        }),
        ('Участники', {
            'fields': ('participants',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def type_badge(self, obj):
        """
        Отображает тип чата с цветным бейджем
        """
        colors = {
            ChatRoom.Type.DIRECT: 'blue',
            ChatRoom.Type.GROUP: 'green',
            ChatRoom.Type.SUPPORT: 'orange',
            ChatRoom.Type.CLASS: 'purple'
        }
        
        emojis = {
            ChatRoom.Type.DIRECT: '💬',
            ChatRoom.Type.GROUP: '👥',
            ChatRoom.Type.SUPPORT: '🆘',
            ChatRoom.Type.CLASS: '🎓'
        }
        
        color = colors.get(obj.type, 'gray')
        emoji = emojis.get(obj.type, '💬')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_type_display()}"
        )
    type_badge.short_description = 'Тип'
    
    def participants_count(self, obj):
        count = obj.participants.count()
        return format_html(
            '<span style="background-color: blue; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">👥 {}</span>',
            count
        )
    participants_count.short_description = 'Участников'
    
    def messages_count(self, obj):
        count = obj.messages.count()
        return format_html(
            '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">💬 {}</span>',
            count
        )
    messages_count.short_description = 'Сообщений'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Активен</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❌ Неактивен</span>'
            )
    is_active_badge.short_description = 'Статус'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Админка для сообщений
    """
    list_display = [
        'room', 'sender', 'content_short', 'message_type_badge', 
        'is_edited_badge', 'created_at'
    ]
    list_filter = ['message_type', 'is_edited', 'created_at', 'room__type']
    search_fields = ['content', 'sender__username', 'room__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('room', 'sender', 'content', 'message_type')
        }),
        ('Файлы', {
            'fields': ('file', 'image'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('reply_to', 'is_edited'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_short(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Содержание'
    
    def message_type_badge(self, obj):
        """
        Отображает тип сообщения с цветным бейджем
        """
        colors = {
            Message.Type.TEXT: 'blue',
            Message.Type.IMAGE: 'green',
            Message.Type.FILE: 'orange',
            Message.Type.SYSTEM: 'gray'
        }
        
        emojis = {
            Message.Type.TEXT: '💬',
            Message.Type.IMAGE: '🖼️',
            Message.Type.FILE: '📎',
            Message.Type.SYSTEM: '⚙️'
        }
        
        color = colors.get(obj.message_type, 'gray')
        emoji = emojis.get(obj.message_type, '💬')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_message_type_display()}"
        )
    message_type_badge.short_description = 'Тип'
    
    def is_edited_badge(self, obj):
        if obj.is_edited:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✏️ Отредактировано</span>'
            )
        return "—"
    is_edited_badge.short_description = 'Статус'


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    """
    Админка для прочитанных сообщений
    """
    list_display = ['message', 'user', 'read_at']
    list_filter = ['read_at', 'message__room__type']
    search_fields = ['message__content', 'user__username']
    readonly_fields = ['read_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('message', 'user')
        }),
        ('Временные метки', {
            'fields': ('read_at',)
        }),
    )


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    """
    Админка для участников чата
    """
    list_display = [
        'room', 'user', 'is_admin_badge', 'is_muted_badge', 
        'joined_at', 'unread_count_display'
    ]
    list_filter = ['is_admin', 'is_muted', 'joined_at', 'room__type']
    search_fields = ['room__name', 'user__username']
    readonly_fields = ['joined_at', 'unread_count_display']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('room', 'user')
        }),
        ('Права и настройки', {
            'fields': ('is_admin', 'is_muted')
        }),
        ('Временные метки', {
            'fields': ('joined_at', 'last_read_at')
        }),
        ('Статистика', {
            'fields': ('unread_count_display',)
        }),
    )
    
    def is_admin_badge(self, obj):
        if obj.is_admin:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">👑 Админ</span>'
            )
        return "—"
    is_admin_badge.short_description = 'Роль'
    
    def is_muted_badge(self, obj):
        if obj.is_muted:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🔇 Заглушен</span>'
            )
        return "—"
    is_muted_badge.short_description = 'Статус'
    
    def unread_count_display(self, obj):
        count = obj.unread_count
        if count > 0:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📬 {}</span>',
                count
            )
        return format_html(
            '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Все прочитано</span>'
        )
    unread_count_display.short_description = 'Непрочитанных'