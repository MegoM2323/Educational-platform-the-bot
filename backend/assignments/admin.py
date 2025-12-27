from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer,
    PlagiarismReport, GradingRubric, RubricCriterion, RubricScore, RubricTemplate
)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """
    Админка для заданий
    """
    list_display = [
        'title', 'author', 'type', 'status_badge', 'max_score', 
        'difficulty_level', 'due_date', 'submissions_count'
    ]
    list_filter = ['type', 'status', 'difficulty_level', 'created_at']
    search_fields = ['title', 'description', 'author__username', 'tags']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['assigned_to']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'instructions', 'author')
        }),
        ('Настройки', {
            'fields': ('type', 'status', 'max_score', 'time_limit', 'attempts_limit')
        }),
        ('Назначение', {
            'fields': ('assigned_to', 'start_date', 'due_date')
        }),
        ('Метаданные', {
            'fields': ('tags', 'difficulty_level')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """
        Отображает статус с цветным бейджем
        """
        colors = {
            Assignment.Status.DRAFT: 'gray',
            Assignment.Status.PUBLISHED: 'green',
            Assignment.Status.CLOSED: 'red'
        }
        
        emojis = {
            Assignment.Status.DRAFT: '📝',
            Assignment.Status.PUBLISHED: '✅',
            Assignment.Status.CLOSED: '🔒'
        }
        
        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📝')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'
    
    def submissions_count(self, obj):
        count = obj.submissions.count()
        return format_html(
            '<span style="background-color: blue; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📊 {}</span>',
            count
        )
    submissions_count.short_description = 'Ответов'


class AssignmentAnswerInline(admin.TabularInline):
    model = AssignmentAnswer
    extra = 0
    readonly_fields = ['is_correct', 'points_earned']


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    """
    Админка для ответов на задания
    """
    list_display = [
        'assignment', 'student', 'status_badge', 'score_display', 
        'percentage_display', 'submitted_at'
    ]
    list_filter = ['status', 'assignment__type', 'submitted_at']
    search_fields = ['assignment__title', 'student__username', 'student__email']
    readonly_fields = ['submitted_at', 'graded_at', 'updated_at']
    inlines = [AssignmentAnswerInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('assignment', 'student', 'content', 'file')
        }),
        ('Оценка', {
            'fields': ('status', 'score', 'max_score', 'feedback')
        }),
        ('Временные метки', {
            'fields': ('submitted_at', 'graded_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """
        Отображает статус с цветным бейджем
        """
        colors = {
            AssignmentSubmission.Status.SUBMITTED: 'blue',
            AssignmentSubmission.Status.GRADED: 'green',
            AssignmentSubmission.Status.RETURNED: 'orange'
        }
        
        emojis = {
            AssignmentSubmission.Status.SUBMITTED: '📤',
            AssignmentSubmission.Status.GRADED: '✅',
            AssignmentSubmission.Status.RETURNED: '🔄'
        }
        
        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📝')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'
    
    def score_display(self, obj):
        if obj.score is not None and obj.max_score is not None:
            return f"{obj.score}/{obj.max_score}"
        return "—"
    score_display.short_description = 'Балл'
    
    def percentage_display(self, obj):
        if obj.percentage is not None:
            color = 'green' if obj.percentage >= 70 else 'orange' if obj.percentage >= 50 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}%</span>',
                color,
                obj.percentage
            )
        return "—"
    percentage_display.short_description = 'Процент'


@admin.register(AssignmentQuestion)
class AssignmentQuestionAdmin(admin.ModelAdmin):
    """
    Админка для вопросов в заданиях
    """
    list_display = [
        'assignment', 'question_text_short', 'question_type', 
        'points', 'order'
    ]
    list_filter = ['question_type', 'assignment__type']
    search_fields = ['question_text', 'assignment__title']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('assignment', 'question_text', 'question_type', 'points', 'order')
        }),
        ('Варианты ответов', {
            'fields': ('options', 'correct_answer')
        }),
    )
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Текст вопроса'


@admin.register(AssignmentAnswer)
class AssignmentAnswerAdmin(admin.ModelAdmin):
    """
    Админка для ответов на вопросы
    """
    list_display = [
        'submission', 'question_short', 'is_correct_badge', 
        'points_earned', 'answer_preview'
    ]
    list_filter = ['is_correct', 'question__question_type']
    search_fields = ['submission__student__username', 'question__question_text']
    readonly_fields = ['is_correct', 'points_earned']
    
    def question_short(self, obj):
        return obj.question.question_text[:30] + "..." if len(obj.question.question_text) > 30 else obj.question.question_text
    question_short.short_description = 'Вопрос'
    
    def is_correct_badge(self, obj):
        if obj.is_correct:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Правильно</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❌ Неправильно</span>'
            )
    is_correct_badge.short_description = 'Правильность'
    
    def answer_preview(self, obj):
        if obj.answer_text:
            return obj.answer_text[:50] + "..." if len(obj.answer_text) > 50 else obj.answer_text
        elif obj.answer_choice:
            return str(obj.answer_choice)
        return "—"
    answer_preview.short_description = 'Ответ'


@admin.register(PlagiarismReport)
class PlagiarismReportAdmin(admin.ModelAdmin):
    """
    T_ASSIGN_014: Admin interface for plagiarism detection reports.
    """
    list_display = [
        'id', 'submission', 'similarity_score_badge', 'detection_status',
        'service', 'created_at', 'checked_at'
    ]
    list_filter = ['detection_status', 'service', 'created_at']
    search_fields = ['submission__student__email', 'submission__assignment__title', 'service_report_id']
    readonly_fields = ['id', 'created_at', 'checked_at', 'processing_time_seconds']

    fieldsets = (
        ('Submission & Results', {
            'fields': ('submission', 'similarity_score', 'detection_status')
        }),
        ('Service Information', {
            'fields': ('service', 'service_report_id', 'error_message')
        }),
        ('Detection Results', {
            'fields': ('sources',)
        }),
        ('Timing', {
            'fields': ('created_at', 'checked_at', 'processing_time_seconds'),
            'classes': ('collapse',)
        }),
    )

    def similarity_score_badge(self, obj):
        """Display similarity score with color badge"""
        if obj.detection_status != PlagiarismReport.DetectionStatus.COMPLETED:
            return format_html('<span style="color: gray;">{}</span>', obj.detection_status)

        score = float(obj.similarity_score)
        if score >= 30:
            color = 'red'
            status = '🚨 HIGH'
        elif score >= 15:
            color = 'orange'
            status = '⚠️  MEDIUM'
        else:
            color = 'green'
            status = '✅ LOW'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{} ({}%)</span>',
            color, status, score
        )
    similarity_score_badge.short_description = 'Similarity'


# T_ASN_006: Assignment Rubric Support Admin
# =============================================

class RubricCriterionInline(admin.TabularInline):
    """
    T_ASN_006: Inline admin for rubric criteria.

    Allows editing criteria directly within the rubric admin interface.
    """

    model = RubricCriterion
    extra = 1
    fields = ['name', 'description', 'max_points', 'point_scales', 'order']


@admin.register(GradingRubric)
class GradingRubricAdmin(admin.ModelAdmin):
    """
    T_ASN_006: Admin interface for grading rubrics.

    Allows managing rubrics and their criteria with a clean interface.
    """

    list_display = ['name', 'created_by', 'total_points', 'criteria_count',
                    'is_template_badge', 'created_at']
    list_filter = ['is_template', 'is_deleted', 'created_at', 'created_by']
    search_fields = ['name', 'description', 'created_by__username', 'created_by__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [RubricCriterionInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Settings', {
            'fields': ('is_template', 'total_points', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def criteria_count(self, obj):
        """Display number of criteria."""
        return obj.criteria.count()
    criteria_count.short_description = 'Criteria Count'

    def is_template_badge(self, obj):
        """Display template status as badge."""
        if obj.is_template:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; '
                'padding: 3px 8px; border-radius: 3px;">Template</span>'
            )
        return format_html(
            '<span style="background-color: #2196F3; color: white; '
            'padding: 3px 8px; border-radius: 3px;">Custom</span>'
        )
    is_template_badge.short_description = 'Type'

    def get_readonly_fields(self, request, obj=None):
        """Make created_by read-only after creation."""
        if obj:  # Editing an existing object
            return self.readonly_fields + ['created_by']
        return self.readonly_fields


@admin.register(RubricCriterion)
class RubricCriterionAdmin(admin.ModelAdmin):
    """
    T_ASN_006: Admin interface for rubric criteria.

    Manages individual criteria within rubrics.
    """

    list_display = ['name', 'rubric', 'max_points', 'order', 'created_at']
    list_filter = ['rubric', 'order', 'created_at']
    search_fields = ['name', 'description', 'rubric__name']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('rubric', 'name', 'description')
        }),
        ('Scoring', {
            'fields': ('max_points', 'point_scales', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(RubricScore)
class RubricScoreAdmin(admin.ModelAdmin):
    """
    T_ASN_006: Admin interface for rubric scores.

    Allows viewing and editing scores assigned during grading.
    """

    list_display = ['submission', 'criterion', 'score', 'created_at']
    list_filter = ['criterion__rubric', 'created_at']
    search_fields = ['submission__student__username', 'criterion__name',
                     'submission__assignment__title']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Score Information', {
            'fields': ('submission', 'criterion', 'score', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RubricTemplate)
class RubricTemplateAdmin(admin.ModelAdmin):
    """
    T_ASN_006: Admin interface for rubric templates.

    Manages pre-defined rubric templates for common assignment types.
    """

    list_display = ['name', 'assignment_type', 'rubric', 'is_system_badge',
                    'is_active_badge', 'created_at']
    list_filter = ['assignment_type', 'is_system', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'rubric__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'assignment_type', 'rubric')
        }),
        ('Settings', {
            'fields': ('is_system', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_system_badge(self, obj):
        """Display system status as badge."""
        if obj.is_system:
            return format_html(
                '<span style="background-color: #FF9800; color: white; '
                'padding: 3px 8px; border-radius: 3px;">System</span>'
            )
        return format_html(
            '<span style="background-color: #9C27B0; color: white; '
            'padding: 3px 8px; border-radius: 3px;">Custom</span>'
        )
    is_system_badge.short_description = 'Type'

    def is_active_badge(self, obj):
        """Display active status as badge."""
        if obj.is_active:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; '
                'padding: 3px 8px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #F44336; color: white; '
            'padding: 3px 8px; border-radius: 3px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'