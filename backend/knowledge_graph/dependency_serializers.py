"""
Serializers for LessonDependency model (T303)
"""
from rest_framework import serializers
from .models import LessonDependency, GraphLesson


class DependencySerializer(serializers.ModelSerializer):
    """
    Сериализатор для зависимости между уроками
    """
    from_lesson_title = serializers.CharField(source='from_lesson.lesson.title', read_only=True)
    to_lesson_title = serializers.CharField(source='to_lesson.lesson.title', read_only=True)
    dependency_type_display = serializers.CharField(source='get_dependency_type_display', read_only=True)

    class Meta:
        model = LessonDependency
        fields = [
            'id',
            'graph',
            'from_lesson',
            'from_lesson_title',
            'to_lesson',
            'to_lesson_title',
            'dependency_type',
            'dependency_type_display',
            'min_score_percent',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """Общая валидация зависимости"""
        from_lesson = data.get('from_lesson')
        to_lesson = data.get('to_lesson')
        graph = data.get('graph')

        # Проверка что уроки не совпадают
        if from_lesson and to_lesson and from_lesson == to_lesson:
            raise serializers.ValidationError("Урок не может зависеть от самого себя")

        # Проверка что оба урока принадлежат одному графу
        if from_lesson and graph and from_lesson.graph != graph:
            raise serializers.ValidationError("Prerequisite урок не принадлежит этому графу")

        if to_lesson and graph and to_lesson.graph != graph:
            raise serializers.ValidationError("Зависимый урок не принадлежит этому графу")

        return data

    def validate_min_score_percent(self, value):
        """Валидация минимального процента баллов"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Процент должен быть от 0 до 100")
        return value


class AddDependencySerializer(serializers.Serializer):
    """
    Сериализатор для добавления зависимости
    """
    prerequisite_lesson_id = serializers.IntegerField(required=True)
    dependency_type = serializers.ChoiceField(
        choices=LessonDependency.DEPENDENCY_TYPES,
        default='required'
    )
    min_score_percent = serializers.IntegerField(default=0, min_value=0, max_value=100)

    def validate_prerequisite_lesson_id(self, value):
        """Проверка существования prerequisite урока"""
        if not GraphLesson.objects.filter(id=value).exists():
            raise serializers.ValidationError("Prerequisite урок не найден в графе")
        return value
