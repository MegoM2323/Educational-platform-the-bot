from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Админка для управления заявками
    """
    list_display = [
        'id', 'student_name', 'parent_name', 'phone', 'email', 
        'grade', 'status_badge', 'created_at', 'telegram_link'
    ]
    list_filter = ['status', 'grade', 'created_at']
    search_fields = ['student_name', 'parent_name', 'phone', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at', 'telegram_message_id']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('student_name', 'parent_name', 'phone', 'email')
        }),
        ('Образовательная информация', {
            'fields': ('grade', 'goal', 'message')
        }),
        ('Статус и обработка', {
            'fields': ('status', 'notes', 'processed_at')
        }),
        ('Системная информация', {
            'fields': ('id', 'created_at', 'updated_at', 'telegram_message_id'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """
        Отображает статус с цветным бейджем
        """
        colors = {
            Application.Status.NEW: 'red',
            Application.Status.PROCESSING: 'orange',
            Application.Status.APPROVED: 'green',
            Application.Status.REJECTED: 'red',
            Application.Status.COMPLETED: 'blue'
        }
        
        emojis = {
            Application.Status.NEW: '🆕',
            Application.Status.PROCESSING: '⏳',
            Application.Status.APPROVED: '✅',
            Application.Status.REJECTED: '❌',
            Application.Status.COMPLETED: '🎉'
        }
        
        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📝')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'
    
    def telegram_link(self, obj):
        """
        Ссылка на сообщение в Telegram
        """
        if obj.telegram_message_id:
            return format_html(
                '<a href="https://t.me/c/{}/{}" target="_blank" style="color: #0088cc;">📱 Telegram</a>',
                obj.telegram_message_id.split('_')[0] if '_' in obj.telegram_message_id else obj.telegram_message_id,
                obj.telegram_message_id.split('_')[1] if '_' in obj.telegram_message_id else obj.telegram_message_id
            )
        return '—'
    telegram_link.short_description = 'Telegram'
    
    def get_queryset(self, request):
        """
        Оптимизированный запрос
        """
        return super().get_queryset(request).select_related()
    
    def save_model(self, request, obj, form, change):
        """
        Автоматически обновляет processed_at при изменении статуса
        """
        if change and 'status' in form.changed_data:
            from django.utils import timezone
            if obj.status != Application.Status.NEW and not obj.processed_at:
                obj.processed_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_processing', 'mark_as_approved', 'mark_as_rejected']
    
    def mark_as_processing(self, request, queryset):
        """
        Пометить заявки как "В обработке"
        """
        updated = queryset.filter(status=Application.Status.NEW).update(status=Application.Status.PROCESSING)
        self.message_user(request, f'{updated} заявок помечено как "В обработке"')
    mark_as_processing.short_description = 'Пометить как "В обработке"'
    
    def mark_as_approved(self, request, queryset):
        """
        Пометить заявки как "Одобрены"
        """
        updated = queryset.filter(status__in=[Application.Status.NEW, Application.Status.PROCESSING]).update(
            status=Application.Status.APPROVED
        )
        self.message_user(request, f'{updated} заявок помечено как "Одобрены"')
    mark_as_approved.short_description = 'Пометить как "Одобрены"'
    
    def mark_as_rejected(self, request, queryset):
        """
        Пометить заявки как "Отклонены"
        """
        updated = queryset.filter(status__in=[Application.Status.NEW, Application.Status.PROCESSING]).update(
            status=Application.Status.REJECTED
        )
        self.message_user(request, f'{updated} заявок помечено как "Отклонены"')
    mark_as_rejected.short_description = 'Пометить как "Отклонены"'
