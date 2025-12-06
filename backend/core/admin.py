"""
Admin интерфейс для мониторинга Celery задач
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import FailedTask, TaskExecutionLog


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
