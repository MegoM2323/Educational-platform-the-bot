"""
Serializers for Element model (T201)
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Element, ElementFile
from .validators import validate_element_content
import re

User = get_user_model()


class ElementCreatedBySerializer(serializers.Serializer):
    """Сериализатор для информации об авторе элемента"""
    id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)

    def get_name(self, obj):
        return obj.get_full_name()


class ElementFileSerializer(serializers.ModelSerializer):
    """Сериализатор для файлов элемента (T006)"""
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ElementFile
        fields = ['id', 'original_filename', 'file_size', 'uploaded_at', 'file_url']
        read_only_fields = ['id', 'original_filename', 'file_size', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        """Возвращает полный URL файла"""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class ElementSerializer(serializers.ModelSerializer):
    """
    Сериализатор для Element с валидацией по типу

    FIX T019: Документация структуры поля content

    Поле content имеет разную структуру в зависимости от element_type:

    1. text_problem (Текстовая задача):
       {
         "problem_text": "Текст задачи",
         "answer_format": "short_text|number|formula|essay",
         "hints": ["Подсказка 1", "Подсказка 2"],  // опционально
         "solution": "Пример решения"  // опционально
       }

    2. quick_question (Быстрый вопрос):
       {
         "question": "Текст вопроса",
         "choices": ["Вариант A", "Вариант B", "Вариант C"],
         "correct_answer": 0,  // индекс правильного ответа (начиная с 0)
         "explanation": "Объяснение правильного ответа"  // опционально
       }

    3. theory (Теория):
       {
         "text": "HTML-контент или Markdown",
         "examples": ["Пример 1", "Пример 2"],  // опционально
         "formulas": ["formula1", "formula2"]  // опционально (LaTeX)
       }

    4. video (Видео):
       {
         "url": "https://youtube.com/watch?v=...",
         "platform": "youtube|vimeo|custom",
         "description": "Описание видео",
         "duration_seconds": 300,  // опционально
         "thumbnail": "https://..."  // опционально
       }

    Валидация гарантирует корректность структуры для каждого типа.
    """
    created_by = ElementCreatedBySerializer(read_only=True)
    element_type_display = serializers.CharField(source='get_element_type_display', read_only=True)
    files = ElementFileSerializer(many=True, read_only=True)
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = Element
        fields = [
            'id',
            'title',
            'description',
            'element_type',
            'element_type_display',
            'content',
            'difficulty',
            'estimated_time_minutes',
            'max_score',
            'tags',
            'is_public',
            'created_by',
            'created_at',
            'updated_at',
            'files',
            'files_count',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_files_count(self, obj):
        """Возвращает количество файлов элемента"""
        return obj.files.count()

    def validate_element_type(self, value):
        """Валидация типа элемента"""
        valid_types = [choice[0] for choice in Element.ELEMENT_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Некорректный тип элемента. Допустимые значения: {', '.join(valid_types)}"
            )
        return value

    def validate_content(self, value):
        """
        Валидация содержимого элемента в зависимости от типа
        Использует централизованный валидатор из validators.py (T018)
        """
        element_type = self.initial_data.get('element_type')

        if not element_type:
            # Если это обновление, берем тип из instance
            if self.instance:
                element_type = self.instance.element_type
            else:
                raise serializers.ValidationError("Тип элемента обязателен")

        # Используем централизованный валидатор
        try:
            validate_element_content(element_type, value)
        except DjangoValidationError as e:
            # Конвертируем Django ValidationError в DRF ValidationError
            raise serializers.ValidationError(str(e))

        return value

    def validate_difficulty(self, value):
        """Валидация сложности"""
        if value < 1 or value > 10:
            raise serializers.ValidationError("Сложность должна быть от 1 до 10")
        return value

    def validate_estimated_time_minutes(self, value):
        """Валидация времени выполнения"""
        if value < 1:
            raise serializers.ValidationError("Время выполнения должно быть положительным числом")
        return value

    def validate_max_score(self, value):
        """Валидация максимального балла"""
        if value < 0:
            raise serializers.ValidationError("Максимальный балл не может быть отрицательным")
        return value

    def create(self, validated_data):
        """Создание элемента с автоматическим заполнением created_by"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ElementListSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для списка элементов (без полного content)
    """
    created_by = ElementCreatedBySerializer(read_only=True)
    element_type_display = serializers.CharField(source='get_element_type_display', read_only=True)
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = Element
        fields = [
            'id',
            'title',
            'description',
            'element_type',
            'element_type_display',
            'difficulty',
            'estimated_time_minutes',
            'max_score',
            'tags',
            'is_public',
            'created_by',
            'created_at',
            'updated_at',
            'files_count',
        ]

    def get_files_count(self, obj):
        """Возвращает количество файлов элемента"""
        return obj.files.count()
