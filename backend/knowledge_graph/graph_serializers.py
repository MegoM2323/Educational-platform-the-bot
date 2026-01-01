"""
Serializers for KnowledgeGraph and GraphLesson models (T301, T302)
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import KnowledgeGraph, GraphLesson, Lesson, LessonDependency
from .lesson_serializers import LessonListSerializer

User = get_user_model()


class GraphLessonSerializer(serializers.ModelSerializer):
    """
    Сериализатор для урока в графе с позицией
    """

    lesson = LessonListSerializer(read_only=True)
    lesson_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = GraphLesson
        fields = [
            "id",
            "lesson",
            "lesson_id",
            "position_x",
            "position_y",
            "is_unlocked",
            "unlocked_at",
            "node_color",
            "node_size",
            "added_at",
        ]
        read_only_fields = ["id", "added_at", "unlocked_at"]


class DependencyBriefSerializer(serializers.ModelSerializer):
    """
    Краткий сериализатор зависимости для включения в KnowledgeGraphSerializer
    """

    class Meta:
        model = LessonDependency
        fields = [
            "id",
            "from_lesson",
            "to_lesson",
            "dependency_type",
            "min_score_percent",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class KnowledgeGraphSerializer(serializers.ModelSerializer):
    """
    Полный сериализатор для графа знаний

    Возвращает граф с lessons и dependencies в формате ожидаемом frontend:
    - lessons: массив GraphLesson объектов
    - dependencies: массив LessonDependency объектов
    """

    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    student_email = serializers.CharField(source="student.email", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    # FIX T008: переименовано lessons_in_graph -> lessons для соответствия frontend
    lessons = serializers.SerializerMethodField()
    # FIX T008: добавлено поле dependencies
    dependencies = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeGraph
        fields = [
            "id",
            "student",
            "student_name",
            "student_email",
            "subject",
            "subject_name",
            "created_by",
            "created_by_name",
            "is_active",
            "allow_skip",
            "created_at",
            "updated_at",
            "lessons",
            "dependencies",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_lessons(self, obj):
        """Получить все уроки в графе с позициями (с оптимизацией N+1)"""
        from django.db.models import Count, Prefetch

        graph_lessons_qs = GraphLesson.objects.filter(graph=obj).order_by("added_at")

        lessons_qs = (
            Lesson.objects.filter(
                id__in=graph_lessons_qs.values_list("lesson_id", flat=True)
            )
            .select_related("created_by", "subject")
            .prefetch_related("elements")
            .annotate(elements_count_annotated=Count("elements"))
        )

        prefetch = Prefetch("lesson", queryset=lessons_qs)
        graph_lessons = graph_lessons_qs.select_related(
            "lesson", "lesson__created_by", "lesson__subject"
        ).prefetch_related(prefetch)

        return GraphLessonSerializer(graph_lessons, many=True).data

    def get_dependencies(self, obj):
        """Получить все зависимости графа"""
        dependencies = (
            LessonDependency.objects.filter(graph=obj)
            .select_related("from_lesson", "to_lesson")
            .order_by("created_at")
        )

        # Возвращаем в формате ожидаемом frontend
        return [
            {
                "id": dep.id,
                "from_lesson": dep.from_lesson_id,
                "to_lesson": dep.to_lesson_id,
                "dependency_type": dep.dependency_type,
                "min_score_percent": dep.min_score_percent,
                "created_at": dep.created_at.isoformat() if dep.created_at else None,
            }
            for dep in dependencies
        ]

    def validate_student(self, value):
        """Валидация студента"""
        if value.role != "student":
            raise serializers.ValidationError(
                "Указанный пользователь не является студентом"
            )
        return value


class AddLessonToGraphSerializer(serializers.Serializer):
    """
    Сериализатор для добавления урока в граф
    """

    lesson_id = serializers.IntegerField(required=True)
    position_x = serializers.FloatField(default=0)
    position_y = serializers.FloatField(default=0)
    node_color = serializers.CharField(max_length=7, default="#4F46E5")
    node_size = serializers.IntegerField(default=50, min_value=10, max_value=200)

    def validate_lesson_id(self, value):
        """Проверка существования урока"""
        if not Lesson.objects.filter(id=value).exists():
            raise serializers.ValidationError("Урок с указанным ID не найден")
        return value

    def validate_node_color(self, value):
        """Валидация цвета узла"""
        import re

        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError(
                "Некорректный формат цвета (ожидается #RRGGBB)"
            )
        return value


class UpdateLessonPositionSerializer(serializers.Serializer):
    """
    Сериализатор для обновления позиции урока в графе
    """

    position_x = serializers.FloatField(required=False)
    position_y = serializers.FloatField(required=False)
    node_color = serializers.CharField(max_length=7, required=False)
    node_size = serializers.IntegerField(min_value=10, max_value=200, required=False)

    def validate_node_color(self, value):
        """Валидация цвета узла"""
        import re

        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise serializers.ValidationError(
                "Некорректный формат цвета (ожидается #RRGGBB)"
            )
        return value


class BatchUpdateLessonsSerializer(serializers.Serializer):
    """
    Сериализатор для batch обновления позиций уроков
    """

    lessons = serializers.ListField(
        child=serializers.DictField(), required=True, allow_empty=False
    )

    def validate_lessons(self, value):
        """Валидация списка уроков"""
        for lesson_data in value:
            if "lesson_id" not in lesson_data:
                raise serializers.ValidationError(
                    "Каждый урок должен содержать lesson_id"
                )

            if "position_x" not in lesson_data or "position_y" not in lesson_data:
                raise serializers.ValidationError(
                    "Каждый урок должен содержать position_x и position_y"
                )

            # Проверка типов
            try:
                float(lesson_data["position_x"])
                float(lesson_data["position_y"])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "position_x и position_y должны быть числами"
                )

        return value
