from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Subject, Material, MaterialProgress, MaterialComment, SubjectEnrollment,
    SubjectPayment, SubjectSubscription, StudyPlan, StudyPlanFile,
    StudyPlanGeneration, GeneratedFile, MaterialDownloadLog, BulkAssignmentAuditLog
)


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
            SubjectPayment.Status.WAITING_FOR_PAYMENT: 'blue',
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


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    """
    Админка для планов занятий
    """
    list_display = ['title', 'teacher', 'student', 'subject', 'week_start_date', 'status_badge', 'created_at']
    list_filter = ['status', 'week_start_date', 'subject', 'created_at']
    search_fields = ['title', 'content', 'teacher__username', 'student__username', 'subject__name']
    readonly_fields = ['created_at', 'updated_at', 'sent_at', 'week_end_date']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('teacher', 'student', 'subject', 'enrollment', 'title', 'content')
        }),
        ('Период', {
            'fields': ('week_start_date', 'week_end_date')
        }),
        ('Статус', {
            'fields': ('status', 'sent_at')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            StudyPlan.Status.DRAFT: 'gray',
            StudyPlan.Status.SENT: 'green',
            StudyPlan.Status.ARCHIVED: 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'


@admin.register(StudyPlanFile)
class StudyPlanFileAdmin(admin.ModelAdmin):
    """
    Админка для файлов планов занятий
    """
    list_display = ['name', 'study_plan', 'uploaded_by', 'file_size_display', 'created_at']
    list_filter = ['created_at', 'study_plan__subject']
    search_fields = ['name', 'study_plan__title', 'uploaded_by__username']
    readonly_fields = ['created_at', 'file_size']

    fieldsets = (
        ('Основная информация', {
            'fields': ('study_plan', 'file', 'name', 'uploaded_by')
        }),
        ('Метаданные', {
            'fields': ('file_size', 'created_at')
        }),
    )

    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.2f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
    file_size_display.short_description = 'Размер файла'


class GeneratedFileInline(admin.TabularInline):
    """
    Инлайн для отображения сгенерированных файлов
    """
    model = GeneratedFile
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['file_type', 'status', 'file', 'error_message', 'created_at']


@admin.register(StudyPlanGeneration)
class StudyPlanGenerationAdmin(admin.ModelAdmin):
    """
    Админка для генерации учебных планов
    """
    list_display = [
        'id', 'teacher', 'student', 'subject', 'status_badge',
        'files_progress', 'created_at', 'completed_at'
    ]
    list_filter = ['status', 'created_at', 'subject', 'teacher']
    search_fields = ['teacher__username', 'student__username', 'subject__name']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    inlines = [GeneratedFileInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('teacher', 'student', 'subject', 'enrollment')
        }),
        ('Параметры генерации', {
            'fields': ('parameters',)
        }),
        ('Статус', {
            'fields': ('status', 'error_message')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """
        Цветной бейдж статуса генерации
        """
        colors = {
            StudyPlanGeneration.Status.PENDING: 'gray',
            StudyPlanGeneration.Status.PROCESSING: 'blue',
            StudyPlanGeneration.Status.COMPLETED: 'green',
            StudyPlanGeneration.Status.FAILED: 'red'
        }

        emojis = {
            StudyPlanGeneration.Status.PENDING: '⏳',
            StudyPlanGeneration.Status.PROCESSING: '⚙️',
            StudyPlanGeneration.Status.COMPLETED: '✅',
            StudyPlanGeneration.Status.FAILED: '❌'
        }

        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '⏳')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{} {}</span>',
            color,
            emoji,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    def files_progress(self, obj):
        """
        Прогресс генерации файлов
        """
        total = obj.generated_files.count()
        compiled = obj.generated_files.filter(status=GeneratedFile.Status.COMPILED).count()

        if total == 0:
            return format_html(
                '<span style="color: gray;">Файлы не созданы</span>'
            )

        color = 'green' if compiled == total else 'orange'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span>',
            color,
            compiled,
            total
        )
    files_progress.short_description = 'Файлы'


@admin.register(GeneratedFile)
class GeneratedFileAdmin(admin.ModelAdmin):
    """
    Админка для сгенерированных файлов
    """
    list_display = [
        'id', 'generation', 'file_type_badge', 'status_badge',
        'file_link', 'created_at'
    ]
    list_filter = ['file_type', 'status', 'created_at']
    search_fields = [
        'generation__teacher__username',
        'generation__student__username',
        'generation__subject__name'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('generation', 'file_type')
        }),
        ('Файл', {
            'fields': ('file', 'status', 'error_message')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def file_type_badge(self, obj):
        """
        Цветной бейдж типа файла
        """
        colors = {
            GeneratedFile.FileType.PROBLEM_SET: 'blue',
            GeneratedFile.FileType.REFERENCE_GUIDE: 'green',
            GeneratedFile.FileType.VIDEO_LIST: 'red',
            GeneratedFile.FileType.WEEKLY_PLAN: 'purple'
        }

        emojis = {
            GeneratedFile.FileType.PROBLEM_SET: '📝',
            GeneratedFile.FileType.REFERENCE_GUIDE: '📚',
            GeneratedFile.FileType.VIDEO_LIST: '🎥',
            GeneratedFile.FileType.WEEKLY_PLAN: '📅'
        }

        color = colors.get(obj.file_type, 'gray')
        emoji = emojis.get(obj.file_type, '📄')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{} {}</span>',
            color,
            emoji,
            obj.get_file_type_display()
        )
    file_type_badge.short_description = 'Тип файла'

    def status_badge(self, obj):
        """
        Цветной бейдж статуса файла
        """
        colors = {
            GeneratedFile.Status.PENDING: 'gray',
            GeneratedFile.Status.GENERATING: 'blue',
            GeneratedFile.Status.COMPILED: 'green',
            GeneratedFile.Status.FAILED: 'red'
        }

        emojis = {
            GeneratedFile.Status.PENDING: '⏳',
            GeneratedFile.Status.GENERATING: '⚙️',
            GeneratedFile.Status.COMPILED: '✅',
            GeneratedFile.Status.FAILED: '❌'
        }

        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '⏳')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{} {}</span>',
            color,
            emoji,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    def file_link(self, obj):
        """
        Ссылка на файл если он существует
        """
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">📥 Скачать</a>',
                obj.file.url
            )
        return format_html('<span style="color: gray;">Нет файла</span>')
    file_link.short_description = 'Файл'


@admin.register(MaterialDownloadLog)
class MaterialDownloadLogAdmin(admin.ModelAdmin):
    """
    Админка для логов загрузок материалов
    """
    list_display = [
        'material_link',
        'user_email',
        'ip_address',
        'file_size_display',
        'timestamp',
        'user_agent_short'
    ]

    search_fields = [
        'material__title',
        'user__email',
        'user__first_name',
        'user__last_name',
        'ip_address'
    ]

    list_filter = [
        'timestamp',
        'material',
        'user'
    ]

    readonly_fields = [
        'material',
        'user',
        'ip_address',
        'user_agent',
        'file_size',
        'timestamp'
    ]

    fieldsets = (
        ('Информация о загрузке', {
            'fields': ('material', 'user', 'timestamp')
        }),
        ('Сетевые данные', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Размер файла', {
            'fields': ('file_size',)
        }),
    )

    def material_link(self, obj):
        """
        Ссылка на материал
        """
        url = reverse('admin:materials_material_change', args=[obj.material.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.material.title[:50] + '...' if len(obj.material.title) > 50 else obj.material.title
        )
    material_link.short_description = 'Материал'

    def user_email(self, obj):
        """
        Email пользователя
        """
        return obj.user.email
    user_email.short_description = 'Пользователь'

    def file_size_display(self, obj):
        """
        Форматированный размер файла
        """
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    file_size_display.short_description = 'Размер файла'

    def user_agent_short(self, obj):
        """
        Сокращенный User-Agent
        """
        ua = obj.user_agent[:50]
        if len(obj.user_agent) > 50:
            ua += '...'
        return ua
    user_agent_short.short_description = 'User-Agent'

    def has_add_permission(self, request):
        """
        Логи только для просмотра, не может быть добавлены вручную
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Логи не могут быть удалены из админки (используйте management command)
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Логи только для просмотра
        """
        return False


@admin.register(BulkAssignmentAuditLog)
class BulkAssignmentAuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for bulk assignment audit logs.
    Tracks all bulk material assignment operations.
    """
    list_display = [
        "id",
        "get_operation_display",
        "performed_by",
        "get_status_display",
        "total_items",
        "created_count",
        "failed_count",
        "created_at",
        "duration_display",
    ]
    list_filter = ["operation_type", "status", "created_at"]
    search_fields = ["performed_by__email", "performed_by__first_name", "performed_by__last_name"]
    readonly_fields = [
        "id",
        "operation_type",
        "status",
        "total_items",
        "created_count",
        "skipped_count",
        "failed_count",
        "failed_items",
        "error_message",
        "metadata",
        "created_at",
        "completed_at",
        "duration_seconds",
    ]
    fieldsets = (
        ("Operation Details", {
            "fields": (
                "id",
                "performed_by",
                "operation_type",
                "status",
            )
        }),
        ("Statistics", {
            "fields": (
                "total_items",
                "created_count",
                "skipped_count",
                "failed_count",
            )
        }),
        ("Additional Info", {
            "fields": (
                "metadata",
                "failed_items",
                "error_message",
            ),
            "classes": ("collapse",)
        }),
        ("Timing", {
            "fields": (
                "created_at",
                "completed_at",
                "duration_seconds",
            )
        }),
    )

    def has_add_permission(self, request):
        """Logs can only be created by the system"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Logs cannot be deleted from admin"""
        return False

    def has_change_permission(self, request, obj=None):
        """Logs are read-only"""
        return False

    def get_operation_display(self, obj):
        """Display operation type with color coding"""
        return obj.get_operation_type_display()
    get_operation_display.short_description = "Operation"

    def duration_display(self, obj):
        """Display duration in a readable format"""
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.2f}s"
        return "-"
    duration_display.short_description = "Duration"

