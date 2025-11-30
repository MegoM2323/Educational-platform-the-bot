"""
Admin panel for simplified lesson scheduling system.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from scheduling.models import Lesson, LessonHistory


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """Admin interface for lessons."""

    list_display = [
        'id_short',
        'date_time',
        'student_name',
        'teacher_name',
        'subject_name',
        'status_badge',
        'description_short',
        'has_telemost_link',
        'created_at_formatted'
    ]
    list_filter = [
        'status',
        'date',
        'teacher',
        'student',
        'subject'
    ]
    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__email',
        'teacher__first_name',
        'teacher__last_name',
        'teacher__email',
        'subject__name',
        'description'
    ]
    date_hierarchy = 'date'
    readonly_fields = [
        'id',
        'created_at',
        'updated_at'
    ]
    ordering = ['-date', '-start_time']

    fieldsets = (
        ('Main information', {
            'fields': (
                'teacher',
                'student',
                'subject',
                'status'
            )
        }),
        ('Schedule', {
            'fields': (
                'date',
                'start_time',
                'end_time'
            )
        }),
        ('Lesson details', {
            'fields': (
                'description',
                'telemost_link'
            )
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def id_short(self, obj):
        """Short ID."""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def date_time(self, obj):
        """Lesson date and time."""
        return format_html(
            '<b>{}</b><br>{}',
            obj.date.strftime('%d.%m.%Y'),
            f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
        )
    date_time.short_description = 'Date & Time'

    def student_name(self, obj):
        """Student name with link."""
        url = reverse('admin:accounts_user_change', args=[obj.student.pk])
        return format_html('<a href="{}">{}</a>', url, obj.student.get_full_name())
    student_name.short_description = 'Student'

    def teacher_name(self, obj):
        """Teacher name with link."""
        url = reverse('admin:accounts_user_change', args=[obj.teacher.pk])
        return format_html('<a href="{}">{}</a>', url, obj.teacher.get_full_name())
    teacher_name.short_description = 'Teacher'

    def subject_name(self, obj):
        """Subject name."""
        return obj.subject.name
    subject_name.short_description = 'Subject'

    def status_badge(self, obj):
        """Colored status badge."""
        colors = {
            'pending': '#FFA500',
            'confirmed': '#28a745',
            'completed': '#6c757d',
            'cancelled': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def description_short(self, obj):
        """Short description."""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_short.short_description = 'Description'

    def has_telemost_link(self, obj):
        """Check if Telemost link is set."""
        if obj.telemost_link:
            return format_html('✅')
        return '—'
    has_telemost_link.short_description = 'Telemost'

    def created_at_formatted(self, obj):
        """Formatted creation date."""
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_at_formatted.short_description = 'Created'


@admin.register(LessonHistory)
class LessonHistoryAdmin(admin.ModelAdmin):
    """Admin interface for lesson history."""

    list_display = [
        'lesson_short',
        'action_badge',
        'performed_by_name',
        'timestamp_formatted'
    ]
    list_filter = [
        'action',
        'timestamp',
        'performed_by'
    ]
    search_fields = [
        'lesson__student__first_name',
        'lesson__student__last_name',
        'lesson__teacher__first_name',
        'lesson__teacher__last_name',
        'performed_by__first_name',
        'performed_by__last_name'
    ]
    date_hierarchy = 'timestamp'
    readonly_fields = [
        'id',
        'lesson',
        'action',
        'performed_by',
        'timestamp',
        'old_values',
        'new_values'
    ]
    ordering = ['-timestamp']

    def lesson_short(self, obj):
        """Short lesson info."""
        lesson = obj.lesson
        return format_html(
            '{} → {}<br><small>{}</small>',
            lesson.student.get_full_name(),
            lesson.teacher.get_full_name(),
            lesson.date.strftime('%d.%m.%Y')
        )
    lesson_short.short_description = 'Lesson'

    def action_badge(self, obj):
        """Colored action badge."""
        colors = {
            'created': '#007bff',
            'updated': '#ffc107',
            'cancelled': '#dc3545',
            'completed': '#6c757d'
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def performed_by_name(self, obj):
        """Who performed action."""
        if obj.performed_by:
            return obj.performed_by.get_full_name()
        return '-'
    performed_by_name.short_description = 'Performed by'

    def timestamp_formatted(self, obj):
        """Formatted timestamp."""
        return obj.timestamp.strftime('%d.%m.%Y %H:%M:%S')
    timestamp_formatted.short_description = 'Timestamp'
