from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Notification,
    NotificationTemplate,
    NotificationSettings,
    NotificationQueue,
    Broadcast,
    BroadcastRecipient
)


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


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    """
    Админка для массовых рассылок
    """
    list_display = [
        'id', 'target_group_badge', 'message_short', 'status_badge',
        'recipient_stats', 'created_by', 'created_at'
    ]
    list_filter = ['status', 'target_group', 'created_at']
    search_fields = ['message', 'created_by__username', 'created_by__email']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'completed_at', 'recipient_count', 'sent_count', 'failed_count']

    fieldsets = (
        ('Основная информация', {
            'fields': ('created_by', 'target_group', 'target_filter', 'message')
        }),
        ('Статус и статистика', {
            'fields': ('status', 'recipient_count', 'sent_count', 'failed_count')
        }),
        ('Расписание', {
            'fields': ('scheduled_at', 'sent_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def message_short(self, obj):
        """Сокращенное сообщение"""
        return obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Сообщение'

    def target_group_badge(self, obj):
        """Отображает целевую группу с цветным бейджем"""
        colors = {
            'all_students': 'blue',
            'all_teachers': 'green',
            'all_tutors': 'purple',
            'all_parents': 'orange',
            'by_subject': 'cyan',
            'by_tutor': 'brown',
            'by_teacher': 'teal',
            'custom': 'gray'
        }

        emojis = {
            'all_students': '👨‍🎓',
            'all_teachers': '👨‍🏫',
            'all_tutors': '👨‍💼',
            'all_parents': '👨‍👩‍👧',
            'by_subject': '📚',
            'by_tutor': '👤',
            'by_teacher': '👤',
            'custom': '🎯'
        }

        color = colors.get(obj.target_group, 'gray')
        emoji = emojis.get(obj.target_group, '📢')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_target_group_display()}"
        )
    target_group_badge.short_description = 'Целевая группа'

    def status_badge(self, obj):
        """Отображает статус с цветным бейджем"""
        colors = {
            'draft': 'gray',
            'scheduled': 'blue',
            'sending': 'orange',
            'sent': 'green',
            'failed': 'red',
            'cancelled': 'darkgray'
        }

        emojis = {
            'draft': '📝',
            'scheduled': '⏰',
            'sending': '📤',
            'sent': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }

        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📢')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'

    def recipient_stats(self, obj):
        """Отображает статистику получателей"""
        if obj.recipient_count == 0:
            return format_html('<span style="color: gray;">Нет получателей</span>')

        success_rate = (obj.sent_count / obj.recipient_count * 100) if obj.recipient_count > 0 else 0

        if success_rate >= 90:
            color = 'green'
        elif success_rate >= 70:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{} ({:.1f}%)</span>',
            color,
            obj.sent_count,
            obj.recipient_count,
            success_rate
        )
    recipient_stats.short_description = 'Отправлено/Всего'


@admin.register(BroadcastRecipient)
class BroadcastRecipientAdmin(admin.ModelAdmin):
    """
    Админка для получателей рассылок
    """
    list_display = [
        'broadcast_info', 'recipient', 'telegram_sent_badge', 'sent_at'
    ]
    list_filter = ['telegram_sent', 'sent_at', 'broadcast__status']
    search_fields = ['recipient__username', 'recipient__email', 'broadcast__id']
    readonly_fields = ['broadcast', 'recipient', 'telegram_sent', 'telegram_message_id', 'telegram_error', 'sent_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('broadcast', 'recipient')
        }),
        ('Telegram доставка', {
            'fields': ('telegram_sent', 'telegram_message_id', 'telegram_error', 'sent_at')
        }),
    )

    def broadcast_info(self, obj):
        """Информация о рассылке"""
        return format_html(
            'Broadcast #{} ({})',
            obj.broadcast.id,
            obj.broadcast.get_status_display()
        )
    broadcast_info.short_description = 'Рассылка'

    def telegram_sent_badge(self, obj):
        """Статус отправки в Telegram"""
        if obj.telegram_sent:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Отправлено</span>'
            )
        elif obj.telegram_error:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❌ Ошибка</span>'
            )
        else:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">⏳ Ожидает</span>'
            )
    telegram_sent_badge.short_description = 'Статус Telegram'