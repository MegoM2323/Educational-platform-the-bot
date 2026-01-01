from django.contrib import admin
from .models import (
    Element,
    ElementFile,
    Lesson,
    LessonElement,
    KnowledgeGraph,
    GraphLesson,
    LessonDependency,
    ElementProgress,
    LessonProgress,
)


# ============================================
# Element and Lesson Admin
# ============================================


class ElementFileInline(admin.TabularInline):
    """Inline для редактирования файлов элемента"""

    model = ElementFile
    extra = 0
    readonly_fields = ("uploaded_at", "uploaded_by", "file_size")
    fields = ("file", "original_filename", "file_size", "uploaded_at", "uploaded_by")


class LessonElementInline(admin.TabularInline):
    model = LessonElement
    extra = 1
    ordering = ["order"]
    fields = ["element", "order", "is_optional", "custom_instructions"]


@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "element_type",
        "difficulty",
        "estimated_time_minutes",
        "max_score",
        "is_public",
        "created_by",
    ]
    list_filter = ["element_type", "difficulty", "is_public", "created_at"]
    search_fields = ["title", "description", "tags"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ElementFileInline]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("title", "description", "element_type", "content")},
        ),
        (
            "Параметры",
            {"fields": ("difficulty", "estimated_time_minutes", "max_score")},
        ),
        (
            "Метаданные",
            {"fields": ("tags", "created_by", "is_public", "created_at", "updated_at")},
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "subject",
        "element_count",
        "total_duration_minutes",
        "total_max_score",
        "is_public",
        "created_by",
    ]
    list_filter = ["subject", "is_public", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "total_duration_minutes",
        "total_max_score",
    ]
    inlines = [LessonElementInline]

    fieldsets = (
        ("Основная информация", {"fields": ("title", "description", "subject")}),
        (
            "Статистика",
            {
                "fields": ("total_duration_minutes", "total_max_score"),
                "description": "Автоматически вычисляется на основе элементов урока",
            },
        ),
        (
            "Метаданные",
            {"fields": ("created_by", "is_public", "created_at", "updated_at")},
        ),
    )

    def element_count(self, obj):
        return obj.elements.count()

    element_count.short_description = "Элементов"

    def save_model(self, request, obj, form, change):
        if not change:  # Новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        # Пересчитать статистику после сохранения
        obj.recalculate_totals()


# Register other models with basic admin
admin.site.register(LessonElement)
admin.site.register(KnowledgeGraph)
admin.site.register(GraphLesson)
admin.site.register(LessonDependency)
admin.site.register(ElementProgress)
admin.site.register(LessonProgress)
