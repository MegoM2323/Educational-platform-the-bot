from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Notification, NotificationTemplate, NotificationSettings, NotificationQueue


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Админка для уведомлений
    """
    list_display = [
        'recipient', 'title_short', 'type_badge', 'priority_badge', 
        'is_read_badge', 'is_sent_badge', 'created_at'
    ]
    list_filter = ['type', 'priority', 'is_read', 'is_sent', 'created_at']
    search_fields = ['title', 'message', 'recipient__username', 'recipient__email']
    readonly_fields = ['created_at', 'read_at', 'sent_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('recipient', 'title', 'message', 'type', 'priority')
        }),
        ('Статус', {
            'fields': ('is_read', 'is_sent', 'read_at', 'sent_at')
        }),
        ('Связанные объекты', {
            'fields': ('related_object_type', 'related_object_id'),
            'classes': ('collapse',)
        }),
        ('Дополнительные данные', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def title_short(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Заголовок'
    
    def type_badge(self, obj):
        """
        Отображает тип уведомления с цветным бейджем
        """
        colors = {
            Notification.Type.ASSIGNMENT_NEW: 'blue',
            Notification.Type.ASSIGNMENT_DUE: 'orange',
            Notification.Type.ASSIGNMENT_GRADED: 'green',
            Notification.Type.MATERIAL_NEW: 'purple',
            Notification.Type.MESSAGE_NEW: 'cyan',
            Notification.Type.REPORT_READY: 'brown',
            Notification.Type.PAYMENT_SUCCESS: 'green',
            Notification.Type.PAYMENT_FAILED: 'red',
            Notification.Type.SYSTEM: 'gray',
            Notification.Type.REMINDER: 'yellow'
        }
        
        emojis = {
            Notification.Type.ASSIGNMENT_NEW: '📝',
            Notification.Type.ASSIGNMENT_DUE: '⏰',
            Notification.Type.ASSIGNMENT_GRADED: '✅',
            Notification.Type.MATERIAL_NEW: '📚',
            Notification.Type.MESSAGE_NEW: '💬',
            Notification.Type.REPORT_READY: '📊',
            Notification.Type.PAYMENT_SUCCESS: '💰',
            Notification.Type.PAYMENT_FAILED: '❌',
            Notification.Type.SYSTEM: '⚙️',
            Notification.Type.REMINDER: '🔔'
        }
        
        color = colors.get(obj.type, 'gray')
        emoji = emojis.get(obj.type, '📢')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_type_display()}"
        )
    type_badge.short_description = 'Тип'
    
    def priority_badge(self, obj):
        """
        Отображает приоритет с цветным бейджем
        """
        colors = {
            Notification.Priority.LOW: 'gray',
            Notification.Priority.NORMAL: 'blue',
            Notification.Priority.HIGH: 'orange',
            Notification.Priority.URGENT: 'red'
        }
        
        emojis = {
            Notification.Priority.LOW: '🔽',
            Notification.Priority.NORMAL: '➡️',
            Notification.Priority.HIGH: '🔼',
            Notification.Priority.URGENT: '🚨'
        }
        
        color = colors.get(obj.priority, 'blue')
        emoji = emojis.get(obj.priority, '➡️')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_priority_display()}"
        )
    priority_badge.short_description = 'Приоритет'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Прочитано</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📬 Не прочитано</span>'
            )
    is_read_badge.short_description = 'Статус прочтения'
    
    def is_sent_badge(self, obj):
        if obj.is_sent:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📤 Отправлено</span>'
            )
        else:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">⏳ Не отправлено</span>'
            )
    is_sent_badge.short_description = 'Статус отправки'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    Админка для шаблонов уведомлений
    """
    list_display = [
        'name', 'type_badge', 'is_active_badge', 'created_at'
    ]
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'title_template']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'type', 'is_active')
        }),
        ('Шаблоны', {
            'fields': ('title_template', 'message_template')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def type_badge(self, obj):
        """
        Отображает тип шаблона с цветным бейджем
        """
        colors = {
            Notification.Type.ASSIGNMENT_NEW: 'blue',
            Notification.Type.ASSIGNMENT_DUE: 'orange',
            Notification.Type.ASSIGNMENT_GRADED: 'green',
            Notification.Type.MATERIAL_NEW: 'purple',
            Notification.Type.MESSAGE_NEW: 'cyan',
            Notification.Type.REPORT_READY: 'brown',
            Notification.Type.PAYMENT_SUCCESS: 'green',
            Notification.Type.PAYMENT_FAILED: 'red',
            Notification.Type.SYSTEM: 'gray',
            Notification.Type.REMINDER: 'yellow'
        }
        
        emojis = {
            Notification.Type.ASSIGNMENT_NEW: '📝',
            Notification.Type.ASSIGNMENT_DUE: '⏰',
            Notification.Type.ASSIGNMENT_GRADED: '✅',
            Notification.Type.MATERIAL_NEW: '📚',
            Notification.Type.MESSAGE_NEW: '💬',
            Notification.Type.REPORT_READY: '📊',
            Notification.Type.PAYMENT_SUCCESS: '💰',
            Notification.Type.PAYMENT_FAILED: '❌',
            Notification.Type.SYSTEM: '⚙️',
            Notification.Type.REMINDER: '🔔'
        }
        
        color = colors.get(obj.type, 'gray')
        emoji = emojis.get(obj.type, '📢')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_type_display()}"
        )
    type_badge.short_description = 'Тип'
    
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


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    """
    Админка для настроек уведомлений
    """
    list_display = [
        'user', 'email_notifications_badge', 'push_notifications_badge', 
        'sms_notifications_badge'
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Настройки по типам уведомлений', {
            'fields': (
                'assignment_notifications', 'material_notifications', 
                'message_notifications', 'report_notifications', 
                'payment_notifications', 'system_notifications'
            )
        }),
        ('Настройки каналов доставки', {
            'fields': ('email_notifications', 'push_notifications', 'sms_notifications')
        }),
        ('Время тишины', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def email_notifications_badge(self, obj):
        if obj.email_notifications:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📧 Включены</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📧 Выключены</span>'
            )
    email_notifications_badge.short_description = 'Email'
    
    def push_notifications_badge(self, obj):
        if obj.push_notifications:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🔔 Включены</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🔔 Выключены</span>'
            )
    push_notifications_badge.short_description = 'Push'
    
    def sms_notifications_badge(self, obj):
        if obj.sms_notifications:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📱 Включены</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📱 Выключены</span>'
            )
    sms_notifications_badge.short_description = 'SMS'


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    """
    Админка для очереди уведомлений
    """
    list_display = [
        'notification', 'channel_badge', 'status_badge', 'attempts_display', 
        'scheduled_at', 'created_at'
    ]
    list_filter = ['status', 'channel', 'created_at', 'scheduled_at']
    search_fields = ['notification__title', 'notification__recipient__username']
    readonly_fields = ['created_at', 'processed_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('notification', 'channel', 'status', 'scheduled_at')
        }),
        ('Обработка', {
            'fields': ('forms', 'max_attempts', 'error_message', 'processed_at')
        }),
        ('Временные метки', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def channel_badge(self, obj):
        """
        Отображает канал доставки с цветным бейджем
        """
        colors = {
            'email': 'blue',
            'push': 'green',
            'sms': 'orange',
            'in_app': 'purple'
        }
        
        emojis = {
            'email': '📧',
            'push': '🔔',
            'sms': '📱',
            'in_app': '📱'
        }
        
        color = colors.get(obj.channel, 'gray')
        emoji = emojis.get(obj.channel, '📤')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.channel.upper()}"
        )
    channel_badge.short_description = 'Канал'
    
    def status_badge(self, obj):
        """
        Отображает статус с цветным бейджем
        """
        colors = {
            NotificationQueue.Status.PENDING: 'blue',
            NotificationQueue.Status.PROCESSING: 'orange',
            NotificationQueue.Status.SENT: 'green',
            NotificationQueue.Status.FAILED: 'red',
            NotificationQueue.Status.CANCELLED: 'gray'
        }
        
        emojis = {
            NotificationQueue.Status.PENDING: '⏳',
            NotificationQueue.Status.PROCESSING: '⚙️',
            NotificationQueue.Status.SENT: '✅',
            NotificationQueue.Status.FAILED: '❌',
            NotificationQueue.Status.CANCELLED: '🚫'
        }
        
        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📤')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'
    
    def attempts_display(self, obj):
        if obj.attempts >= obj.max_attempts:
            color = 'red'
        elif obj.attempts > 0:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span>',
            color,
            obj.attempts,
            obj.max_attempts
        )
    attempts_display.short_description = 'Попытки'