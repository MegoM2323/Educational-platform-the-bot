from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Subject, Material, MaterialProgress, MaterialComment, SubjectEnrollment, SubjectPayment, SubjectSubscription


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """
    Админка для предметов
    """
    list_display = ['name', 'color_display', 'materials_count', 'description_short']
    search_fields = ['name', 'description']
    readonly_fields = ['materials_count']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'color')
        }),
        ('Статистика', {
            'fields': ('materials_count',)
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🎨 {}</span>',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Цвет'
    
    def materials_count(self, obj):
        count = obj.materials.count()
        return format_html(
            '<span style="background-color: blue; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📚 {}</span>',
            count
        )
    materials_count.short_description = 'Материалов'
    
    def description_short(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Описание'


class MaterialProgressInline(admin.TabularInline):
    model = MaterialProgress
    extra = 0
    readonly_fields = ['started_at', 'completed_at', 'last_accessed']


class MaterialCommentInline(admin.TabularInline):
    model = MaterialComment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """
    Админка для учебных материалов
    """
    list_display = [
        'title', 'author', 'subject', 'type_badge', 'status_badge', 
        'difficulty_level', 'is_public_badge', 'progress_count'
    ]
    list_filter = ['type', 'status', 'difficulty_level', 'is_public', 'subject', 'created_at']
    search_fields = ['title', 'description', 'author__username', 'tags']
    readonly_fields = ['created_at', 'updated_at', 'published_at']
    filter_horizontal = ['assigned_to']
    inlines = [MaterialProgressInline, MaterialCommentInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'content', 'author', 'subject')
        }),
        ('Тип и статус', {
            'fields': ('type', 'status', 'difficulty_level')
        }),
        ('Файлы и ссылки', {
            'fields': ('file', 'video_url'),
            'classes': ('collapse',)
        }),
        ('Настройки доступа', {
            'fields': ('is_public', 'assigned_to', 'tags')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    def type_badge(self, obj):
        """
        Отображает тип материала с цветным бейджем
        """
        colors = {
            Material.Type.LESSON: 'blue',
            Material.Type.PRESENTATION: 'green',
            Material.Type.VIDEO: 'red',
            Material.Type.DOCUMENT: 'orange',
            Material.Type.TEST: 'purple',
            Material.Type.HOMEWORK: 'brown'
        }
        
        emojis = {
            Material.Type.LESSON: '📖',
            Material.Type.PRESENTATION: '📊',
            Material.Type.VIDEO: '🎥',
            Material.Type.DOCUMENT: '📄',
            Material.Type.TEST: '📝',
            Material.Type.HOMEWORK: '📚'
        }
        
        color = colors.get(obj.type, 'gray')
        emoji = emojis.get(obj.type, '📖')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_type_display()}"
        )
    type_badge.short_description = 'Тип'
    
    def status_badge(self, obj):
        """
        Отображает статус материала с цветным бейджем
        """
        colors = {
            Material.Status.DRAFT: 'gray',
            Material.Status.ACTIVE: 'green',
            Material.Status.ARCHIVED: 'red'
        }
        
        emojis = {
            Material.Status.DRAFT: '📝',
            Material.Status.ACTIVE: '✅',
            Material.Status.ARCHIVED: '📦'
        }
        
        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📝')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'
    
    def is_public_badge(self, obj):
        if obj.is_public:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🌐 Публичный</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🔒 Приватный</span>'
            )
    is_public_badge.short_description = 'Доступ'
    
    def progress_count(self, obj):
        count = obj.progress.count()
        completed = obj.progress.filter(is_completed=True).count()
        return format_html(
            '<span style="background-color: blue; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">📊 {}/{}</span>',
            completed,
            count
        )
    progress_count.short_description = 'Прогресс'


@admin.register(MaterialProgress)
class MaterialProgressAdmin(admin.ModelAdmin):
    """
    Админка для прогресса изучения материалов
    """
    list_display = [
        'student', 'material', 'progress_percentage_display', 
        'is_completed_badge', 'time_spent', 'last_accessed'
    ]
    list_filter = ['is_completed', 'material__subject', 'material__type', 'started_at']
    search_fields = ['student__username', 'material__title']
    readonly_fields = ['started_at', 'completed_at', 'last_accessed']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('student', 'material')
        }),
        ('Прогресс', {
            'fields': ('is_completed', 'progress_percentage', 'time_spent')
        }),
        ('Временные метки', {
            'fields': ('started_at', 'completed_at', 'last_accessed'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_percentage_display(self, obj):
        color = 'green' if obj.progress_percentage >= 80 else 'orange' if obj.progress_percentage >= 50 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            obj.progress_percentage
        )
    progress_percentage_display.short_description = 'Прогресс'
    
    def is_completed_badge(self, obj):
        if obj.is_completed:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Завершен</span>'
            )
        else:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">⏳ В процессе</span>'
            )
    is_completed_badge.short_description = 'Статус'


@admin.register(MaterialComment)
class MaterialCommentAdmin(admin.ModelAdmin):
    """
    Админка для комментариев к материалам
    """
    list_display = [
        'material', 'author', 'content_short', 'is_question_badge', 'created_at'
    ]
    list_filter = ['is_question', 'created_at', 'material__subject']
    search_fields = ['content', 'author__username', 'material__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('material', 'author', 'content', 'is_question')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_short(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Содержание'
    
    def is_question_badge(self, obj):
        if obj.is_question:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❓ Вопрос</span>'
            )
        else:
            return format_html(
                '<span style="background-color: blue; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">💬 Комментарий</span>'
            )
    is_question_badge.short_description = 'Тип'


@admin.register(SubjectEnrollment)
class SubjectEnrollmentAdmin(admin.ModelAdmin):
    """
    Админка для зачислений на предметы
    """
    list_display = ['student', 'subject', 'teacher', 'assigned_by', 'enrolled_at', 'is_active_badge']
    list_filter = ['is_active', 'enrolled_at', 'subject', 'teacher']
    search_fields = ['student__username', 'subject__name', 'teacher__username']
    readonly_fields = ['enrolled_at']
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Активно</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❌ Неактивно</span>'
            )
    is_active_badge.short_description = 'Статус'


@admin.register(SubjectPayment)
class SubjectPaymentAdmin(admin.ModelAdmin):
    """
    Админка для платежей по предметам
    """
    list_display = ['enrollment', 'amount', 'status_badge', 'due_date', 'paid_at', 'created_at']
    list_filter = ['status', 'created_at', 'due_date']
    search_fields = ['enrollment__student__username', 'enrollment__subject__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def status_badge(self, obj):
        colors = {
            SubjectPayment.Status.PENDING: 'orange',
            SubjectPayment.Status.PAID: 'green',
            SubjectPayment.Status.EXPIRED: 'red',
            SubjectPayment.Status.REFUNDED: 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'


@admin.register(SubjectSubscription)
class SubjectSubscriptionAdmin(admin.ModelAdmin):
    """
    Админка для подписок на предметы
    """
    list_display = ['enrollment', 'amount', 'status_badge', 'next_payment_date', 'payment_interval_weeks', 'created_at']
    list_filter = ['status', 'created_at', 'next_payment_date']
    search_fields = ['enrollment__student__username', 'enrollment__subject__name']
    readonly_fields = ['created_at', 'updated_at', 'cancelled_at']
    
    def status_badge(self, obj):
        colors = {
            SubjectSubscription.Status.ACTIVE: 'green',
            SubjectSubscription.Status.PAUSED: 'orange',
            SubjectSubscription.Status.CANCELLED: 'red',
            SubjectSubscription.Status.EXPIRED: 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'