"""
Serializers for Lesson model (T202)
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Lesson, LessonElement, Element
from .element_serializers import ElementCreatedBySerializer, ElementListSerializer

User = get_user_model()


class LessonElementSerializer(serializers.ModelSerializer):
    """
    Сериализатор для связи элемента с уроком
    """

    element = ElementListSerializer(read_only=True)
    element_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = LessonElement
        fields = [
            "id",
            "element",
            "element_id",
            "order",
            "is_optional",
            "custom_instructions",
        ]


class LessonSerializer(serializers.ModelSerializer):
    """
    Полный сериализатор для урока с элементами
    """

    created_by = ElementCreatedBySerializer(read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    elements_list = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "subject_name",
            "is_public",
            "total_duration_minutes",
            "total_max_score",
            "created_by",
            "created_at",
            "updated_at",
            "elements_list",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
            "total_duration_minutes",
            "total_max_score",
        ]

    def get_elements_list(self, obj):
        """Получить упорядоченный список элементов урока"""
        lesson_elements = (
            LessonElement.objects.filter(lesson=obj)
            .select_related("element", "element__created_by")
            .order_by("order")
        )

        return LessonElementSerializer(lesson_elements, many=True).data

    def validate_subject(self, value):
        """Валидация предмета"""
        request = self.context.get("request")
        if not request:
            return value

        # Проверяем что учитель имеет доступ к этому предмету
        if request.user.role == "teacher":
            from materials.models import TeacherSubject

            if not TeacherSubject.objects.filter(
                teacher=request.user, subject=value
            ).exists():
                raise serializers.ValidationError("У вас нет доступа к этому предмету")

        return value

    def create(self, validated_data):
        """Создание урока с автоматическим заполнением created_by"""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class LessonListSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для списка уроков (без элементов)
    """

    created_by = ElementCreatedBySerializer(read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    elements_count = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "subject_name",
            "is_public",
            "total_duration_minutes",
            "total_max_score",
            "elements_count",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_elements_count(self, obj):
        """Подсчет количества элементов в уроке (использует аннотацию если доступна)"""
        if hasattr(obj, "elements_count_annotated"):
            return obj.elements_count_annotated
        return obj.elements.count()


class AddElementToLessonSerializer(serializers.Serializer):
    """
    Сериализатор для добавления элемента в урок
    """

    element_id = serializers.IntegerField(required=True)
    order = serializers.IntegerField(required=False, allow_null=True)
    is_optional = serializers.BooleanField(default=False)
    custom_instructions = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_element_id(self, value):
        """Проверка существования элемента"""
        if not Element.objects.filter(id=value).exists():
            raise serializers.ValidationError("Элемент с указанным ID не найден")
        return value

    def validate_order(self, value):
        """Валидация порядка"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Порядок не может быть отрицательным")
        return value
