from django.contrib import admin
from django.utils.html import format_html
from .models import Invoice, InvoiceStatusHistory


class InvoiceStatusHistoryInline(admin.TabularInline):
    """
    Встроенная таблица истории статусов в админке счета
    """
    model = InvoiceStatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'changed_by', 'changed_at', 'reason']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Админка для управления счетами
    """
    list_display = [
        'id',
        'tutor_name',
        'student_name',
        'parent_name',
        'amount',
        'status_badge',
        'due_date',
        'is_overdue_badge',
        'created_at'
    ]

    list_filter = [
        'status',
        'created_at',
        'due_date',
        'tutor',
    ]

    search_fields = [
        'id',
        'tutor__first_name',
        'tutor__last_name',
        'student__first_name',
        'student__last_name',
        'parent__first_name',
        'parent__last_name',
        'description',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'sent_at',
        'viewed_at',
        'paid_at',
        'is_overdue',
    ]

    fieldsets = (
        ('Участники', {
            'fields': ('tutor', 'student', 'parent')
        }),
        ('Детали счета', {
            'fields': ('amount', 'description', 'enrollment')
        }),
        ('Статус и сроки', {
            'fields': ('status', 'due_date')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'sent_at', 'viewed_at', 'paid_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Интеграции', {
            'fields': ('payment', 'telegram_message_id'),
            'classes': ('collapse',)
        }),
    )

    inlines = [InvoiceStatusHistoryInline]

    def tutor_name(self, obj):
        return obj.tutor.get_full_name()
    tutor_name.short_description = 'Тьютор'
    tutor_name.admin_order_field = 'tutor__last_name'

    def student_name(self, obj):
        return obj.student.get_full_name()
    student_name.short_description = 'Студент'
    student_name.admin_order_field = 'student__last_name'

    def parent_name(self, obj):
        return obj.parent.get_full_name()
    parent_name.short_description = 'Родитель'
    parent_name.admin_order_field = 'parent__last_name'

    def status_badge(self, obj):
        """
        Отображение статуса с цветовой индикацией
        """
        colors = {
            'draft': 'gray',
            'sent': 'blue',
            'viewed': 'orange',
            'paid': 'green',
            'cancelled': 'red',
            'overdue': 'darkred',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'

    def is_overdue_badge(self, obj):
        """
        Индикатор просрочки
        """
        if obj.is_overdue:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Просрочен</span>'
            )
        elif obj.status == Invoice.Status.PAID:
            return format_html(
                '<span style="color: green;">✓ Оплачен</span>'
            )
        else:
            return format_html(
                '<span style="color: gray;">—</span>'
            )
    is_overdue_badge.short_description = 'Просрочка'


@admin.register(InvoiceStatusHistory)
class InvoiceStatusHistoryAdmin(admin.ModelAdmin):
    """
    Админка для просмотра истории изменений статусов
    """
    list_display = [
        'id',
        'invoice',
        'old_status',
        'new_status',
        'changed_by_name',
        'changed_at',
    ]

    list_filter = [
        'old_status',
        'new_status',
        'changed_at',
    ]

    search_fields = [
        'invoice__id',
        'changed_by__first_name',
        'changed_by__last_name',
        'reason',
    ]

    readonly_fields = [
        'invoice',
        'old_status',
        'new_status',
        'changed_by',
        'changed_at',
        'reason',
    ]

    def changed_by_name(self, obj):
        return obj.changed_by.get_full_name()
    changed_by_name.short_description = 'Изменил'
    changed_by_name.admin_order_field = 'changed_by__last_name'

    def has_add_permission(self, request):
        """
        Запретить создание записей истории вручную
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Запретить удаление записей истории
        """
        return False
