"""
Admin интерфейс для мониторинга Celery задач и конфигурации системы
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import FailedTask, TaskExecutionLog, AuditLog, Configuration


@admin.register(FailedTask)
class FailedTaskAdmin(admin.ModelAdmin):
    """
    Админка для мониторинга неудачных задач (Dead Letter Queue)
    """
    list_display = [
        'task_name',
        'task_id_short',
        'status_badge',
        'error_type',
        'retry_count',
        'is_transient',
        'failed_at',
        'actions_column'
    ]
    list_filter = ['status', 'task_name', 'error_type', 'is_transient', 'failed_at']
    search_fields = ['task_id', 'task_name', 'error_message', 'error_type']
    readonly_fields = [
        'task_id',
        'task_name',
        'error_type',
        'retry_count',
        'is_transient',
        'failed_at',
        'error_message_formatted',
        'traceback_formatted',
        'metadata_formatted'
    ]
    fieldsets = (
        ('Основная информация', {
            'fields': ('task_id', 'task_name', 'status', 'failed_at')
        }),
        ('Детали ошибки', {
            'fields': ('error_type', 'retry_count', 'is_transient', 'error_message_formatted', 'traceback_formatted')
        }),
        ('Метаданные', {
            'fields': ('metadata_formatted',),
            'classes': ('collapse',)
        }),
        ('Анализ и решение', {
            'fields': (
                'investigation_notes',
                'investigated_at',
                'resolution_notes',
                'resolved_at'
            )
        })
    )
    date_hierarchy = 'failed_at'
    actions = ['mark_as_investigating', 'mark_as_resolved', 'mark_as_ignored']

    def task_id_short(self, obj):
        """Сокращенный task_id для отображения"""
        return obj.task_id[:16] + '...' if len(obj.task_id) > 16 else obj.task_id
    task_id_short.short_description = 'Task ID'

    def status_badge(self, obj):
        """Статус с цветовой индикацией"""
        colors = {
            'failed': 'red',
            'investigating': 'orange',
            'resolved': 'green',
            'ignored': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def actions_column(self, obj):
        """Быстрые действия"""
        return format_html(
            '<a class="button" href="{}">Детали</a>',
            reverse('admin:core_failedtask_change', args=[obj.pk])
        )
    actions_column.short_description = 'Actions'

    def error_message_formatted(self, obj):
        """Отформатированное сообщение об ошибке"""
        return format_html('<pre style="white-space: pre-wrap;">{}</pre>', obj.error_message)
    error_message_formatted.short_description = 'Error Message'

    def traceback_formatted(self, obj):
        """Отформатированный traceback"""
        return format_html('<pre style="white-space: pre-wrap; font-size: 12px;">{}</pre>', obj.traceback)
    traceback_formatted.short_description = 'Traceback'

    def metadata_formatted(self, obj):
        """Отформатированные метаданные"""
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.metadata, indent=2, ensure_ascii=False))
    metadata_formatted.short_description = 'Metadata'

    @admin.action(description='Пометить как исследуется')
    def mark_as_investigating(self, request, queryset):
        count = 0
        for task in queryset:
            task.mark_investigating()
            count += 1
        self.message_user(request, f'{count} задач помечены как исследуется')

    @admin.action(description='Пометить как решено')
    def mark_as_resolved(self, request, queryset):
        count = 0
        for task in queryset:
            task.mark_resolved()
            count += 1
        self.message_user(request, f'{count} задач помечены как решено')

    @admin.action(description='Пометить как игнорировать')
    def mark_as_ignored(self, request, queryset):
        count = 0
        for task in queryset:
            task.mark_ignored()
            count += 1
        self.message_user(request, f'{count} задач помечены как игнорировать')


@admin.register(TaskExecutionLog)
class TaskExecutionLogAdmin(admin.ModelAdmin):
    """
    Админка для мониторинга выполнения задач
    """
    list_display = [
        'task_name',
        'task_id_short',
        'status_badge',
        'started_at',
        'duration_display',
        'retry_count'
    ]
    list_filter = ['status', 'task_name', 'started_at']
    search_fields = ['task_id', 'task_name', 'error_message']
    readonly_fields = [
        'task_id',
        'task_name',
        'status',
        'started_at',
        'completed_at',
        'duration_seconds',
        'retry_count',
        'result_formatted',
        'error_message'
    ]
    date_hierarchy = 'started_at'

    def task_id_short(self, obj):
        """Сокращенный task_id"""
        return obj.task_id[:16] + '...' if len(obj.task_id) > 16 else obj.task_id
    task_id_short.short_description = 'Task ID'

    def status_badge(self, obj):
        """Статус с цветовой индикацией"""
        colors = {
            'success': 'green',
            'failed': 'red',
            'retrying': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def duration_display(self, obj):
        """Отображение длительности"""
        if obj.duration_seconds is not None:
            return f"{obj.duration_seconds:.2f}s"
        return "-"
    duration_display.short_description = 'Duration'

    def result_formatted(self, obj):
        """Отформатированный результат"""
        import json
        return format_html('<pre>{}</pre>', json.dumps(obj.result, indent=2, ensure_ascii=False))
    result_formatted.short_description = 'Result'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Админка для просмотра логов аудита пользовательской активности
    """
    list_display = [
        'action_badge',
        'user',
        'target_description',
        'ip_address',
        'timestamp_display',
    ]
    list_filter = [
        'action',
        'target_type',
        'timestamp',
        ('user', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ['user__email', 'user__username', 'ip_address', 'action']
    readonly_fields = [
        'action',
        'user',
        'target_type',
        'target_id',
        'ip_address',
        'user_agent',
        'metadata_formatted',
        'timestamp',
    ]
    fieldsets = (
        ('Действие', {
            'fields': ('action', 'timestamp')
        }),
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Объект', {
            'fields': ('target_type', 'target_id')
        }),
        ('Запрос', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Метаданные', {
            'fields': ('metadata_formatted',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def action_badge(self, obj):
        """Действие с цветовой индикацией"""
        action_colors = {
            'login': 'blue',
            'logout': 'gray',
            'view_material': 'green',
            'download_material': 'green',
            'submit_assignment': 'green',
            'create_material': 'blue',
            'edit_material': 'blue',
            'delete_material': 'red',
            'grade_assignment': 'orange',
            'create_chat': 'blue',
            'send_message': 'green',
            'delete_message': 'red',
            'process_payment': 'purple',
            'admin_action': 'red',
            'error': 'red',
        }
        color = action_colors.get(obj.action, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def target_description(self, obj):
        """Описание цели действия"""
        if obj.target_type and obj.target_id:
            return f"{obj.target_type} #{obj.target_id}"
        return "-"
    target_description.short_description = 'Target'

    def timestamp_display(self, obj):
        """Форматированный временной штамп"""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    timestamp_display.short_description = 'Time'

    def metadata_formatted(self, obj):
        """Отформатированные метаданные"""
        import json
        if obj.metadata:
            return format_html('<pre>{}</pre>', json.dumps(obj.metadata, indent=2, ensure_ascii=False))
        return "-"
    metadata_formatted.short_description = 'Metadata'

    def has_add_permission(self, request):
        """Запрещить создание через админку"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Только суперюзер может удалять логи"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Логи только для чтения"""
        return False


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    """
    Админка для управления системной конфигурацией

    Позволяет просматривать и редактировать все параметры конфигурации
    с аудитлогированием изменений.
    """
    list_display = [
        'key',
        'value_display',
        'value_type_badge',
        'group',
        'updated_by',
        'updated_at'
    ]
    list_filter = [
        'group',
        'value_type',
        'updated_at',
        ('updated_by', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ['key', 'description', 'group']
    readonly_fields = [
        'key',
        'value_type',
        'created_at',
        'updated_at',
        'updated_by',
        'value_formatted'
    ]
    fieldsets = (
        ('Основная информация', {
            'fields': ('key', 'group', 'description')
        }),
        ('Значение', {
            'fields': ('value_formatted', 'value_type')
        }),
        ('История', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'updated_at'
    ordering = ['group', 'key']

    def value_display(self, obj):
        """Компактное отображение значения"""
        value = str(obj.value)
        if len(value) > 50:
            return value[:47] + '...'
        return value
    value_display.short_description = 'Value'

    def value_type_badge(self, obj):
        """Тип значения с цветовой индикацией"""
        colors = {
            'string': '#3498db',
            'integer': '#2ecc71',
            'boolean': '#e74c3c',
            'list': '#f39c12',
            'json': '#9b59b6',
        }
        color = colors.get(obj.value_type, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px;">{}</span>',
            color,
            obj.get_value_type_display()
        )
    value_type_badge.short_description = 'Type'

    def value_formatted(self, obj):
        """Отформатированное значение"""
        import json
        if isinstance(obj.value, dict):
            return format_html('<pre>{}</pre>', json.dumps(obj.value, indent=2, ensure_ascii=False))
        elif isinstance(obj.value, list):
            return format_html('<pre>{}</pre>', json.dumps(obj.value, indent=2, ensure_ascii=False))
        else:
            return format_html('<code>{}</code>', str(obj.value))
    value_formatted.short_description = 'Value (Formatted)'

    def has_delete_permission(self, request, obj=None):
        """Только суперюзер может удалять конфигурации"""
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        """Сохраняет конфигурацию и логирует изменение"""
        from .config import ConfigurationService

        if change:
            # Обновление - используем ConfigurationService для логирования
            ConfigurationService.set(obj.key, obj.value, user=request.user)
        else:
            # Создание через админку
            obj.updated_by = request.user
            super().save_model(request, obj, form, change)
