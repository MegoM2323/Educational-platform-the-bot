"""
Serializers for ElementProgress and LessonProgress (T401, T402)
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ElementProgress, LessonProgress, Element
from .element_serializers import ElementListSerializer

User = get_user_model()


class ElementProgressSerializer(serializers.ModelSerializer):
    """
    Сериализатор для прогресса по элементу
    """

    element = ElementListSerializer(read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    score_percent = serializers.SerializerMethodField()

    class Meta:
        model = ElementProgress
        fields = [
            "id",
            "student",
            "student_name",
            "element",
            "graph_lesson",
            "answer",
            "score",
            "max_score",
            "score_percent",
            "status",
            "started_at",
            "completed_at",
            "time_spent_seconds",
            "attempts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "score",
            "status",
            "started_at",
            "completed_at",
            "time_spent_seconds",
            "attempts",
            "created_at",
            "updated_at",
        ]

    def get_score_percent(self, obj):
        """Получить процент баллов (вычисляется на основе score и max_score)"""
        return obj.score_percent


class SaveElementProgressSerializer(serializers.Serializer):
    """
    Сериализатор для сохранения ответа на элемент
    """

    answer = serializers.JSONField(required=True)

    def validate_answer(self, value):
        """Валидация ответа в зависимости от типа элемента"""
        element = self.context.get("element")
        if not element:
            return value

        element_type = element.element_type

        # Валидация для текстовой задачи
        if element_type == "text_problem":
            if not isinstance(value, dict) or "text" not in value:
                raise serializers.ValidationError(
                    "Ответ на текстовую задачу должен содержать поле 'text'"
                )

        # Валидация для быстрого вопроса
        elif element_type == "quick_question":
            if not isinstance(value, dict) or "choice" not in value:
                raise serializers.ValidationError(
                    "Ответ на быстрый вопрос должен содержать поле 'choice'"
                )

            choice = value.get("choice")
            choices = element.content.get("choices", [])

            if not isinstance(choice, int) or choice < 0 or choice >= len(choices):
                raise serializers.ValidationError(
                    f"Индекс выбранного ответа должен быть от 0 до {len(choices) - 1}"
                )

        # Валидация для теории
        elif element_type == "theory":
            if not isinstance(value, dict) or "viewed" not in value:
                raise serializers.ValidationError(
                    "Ответ на теорию должен содержать поле 'viewed'"
                )

        # Валидация для видео
        elif element_type == "video":
            if not isinstance(value, dict) or "watched_until" not in value:
                raise serializers.ValidationError(
                    "Ответ на видео должен содержать поле 'watched_until' (секунды)"
                )

            watched_until = value.get("watched_until")
            if not isinstance(watched_until, (int, float)) or watched_until < 0:
                raise serializers.ValidationError(
                    "watched_until должен быть положительным числом"
                )

        return value


class LessonProgressSerializer(serializers.ModelSerializer):
    """
    Сериализатор для прогресса по уроку
    """

    lesson_title = serializers.CharField(
        source="graph_lesson.lesson.title", read_only=True
    )
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    elements_progress = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = LessonProgress
        fields = [
            "id",
            "student",
            "student_name",
            "graph_lesson",
            "lesson_title",
            "status",
            "completed_elements",
            "total_elements",
            "completion_percent",
            "percentage",
            "total_score",
            "max_possible_score",
            "started_at",
            "completed_at",
            "last_activity",
            "total_time_spent_seconds",
            "created_at",
            "updated_at",
            "elements_progress",
        ]
        read_only_fields = [
            "id",
            "student",
            "completed_elements",
            "total_elements",
            "completion_percent",
            "total_score",
            "max_possible_score",
            "started_at",
            "completed_at",
            "last_activity",
            "total_time_spent_seconds",
            "created_at",
            "updated_at",
        ]

    def get_percentage(self, obj):
        """Получить percentage (синоним completion_percent для frontend)"""
        return obj.completion_percent

    def get_elements_progress(self, obj):
        """Получить прогресс по всем элементам урока"""
        elements_progress = (
            ElementProgress.objects.filter(
                student=obj.student, graph_lesson=obj.graph_lesson
            )
            .select_related("element", "element__created_by")
            .order_by("element__lessonelement__order")
        )

        return ElementProgressSerializer(elements_progress, many=True).data


class UpdateLessonStatusSerializer(serializers.Serializer):
    """
    Сериализатор для обновления статуса урока
    """

    status = serializers.ChoiceField(
        choices=LessonProgress.STATUS_CHOICES, required=True
    )
