from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Assignment, AssignmentSubmission, AssignmentQuestion, AssignmentAnswer


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