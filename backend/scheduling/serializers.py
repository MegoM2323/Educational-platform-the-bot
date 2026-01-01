"""
Serializers for scheduling system.

Includes serializers for lesson models with validation.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, time

from scheduling.models import Lesson, LessonHistory

try:
    from materials.models import Subject
except ImportError:
    Subject = None

User = get_user_model()


def normalize_time_format(value):
    """
    Нормализация формата времени: HH:MM -> HH:MM:SS.

    Принимает время в формате HH:MM или HH:MM:SS и возвращает
    объект time или строку в формате HH:MM:SS.

    Args:
        value: Время в виде строки (HH:MM или HH:MM:SS) или объекта time

    Returns:
        Оригинальное значение (если уже time объект или HH:MM:SS строка)
        или строка с добавленными секундами (если HH:MM)
    """
    # Если уже time объект - возвращаем как есть
    if isinstance(value, time):
        return value

    # Если строка в формате HH:MM - добавляем секунды
    if isinstance(value, str) and value.count(":") == 1:
        return value + ":00"

    return value


class TimeFormatValidationMixin:
    """
    Миксин для валидации и нормализации формата времени.

    Обеспечивает обратную совместимость, принимая как HH:MM, так и HH:MM:SS.
    """

    def validate_start_time(self, value):
        """Нормализация формата start_time: HH:MM -> HH:MM:SS."""
        return normalize_time_format(value)

    def validate_end_time(self, value):
        """Нормализация формата end_time: HH:MM -> HH:MM:SS."""
        return normalize_time_format(value)


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for subjects."""

    class Meta:
        model = Subject
        fields = ["id", "name", "description", "color"]


class LessonSerializer(serializers.ModelSerializer):
    """Serializer for lessons with computed fields."""

    teacher_name = serializers.CharField(source="teacher.get_full_name", read_only=True)
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    # Explicit ID fields for frontend compatibility
    teacher_id = serializers.IntegerField(source="teacher.id", read_only=True)
    subject_id = serializers.IntegerField(source="subject.id", read_only=True)
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    datetime_start = serializers.DateTimeField(read_only=True)
    datetime_end = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "teacher",
            "student",
            "subject",
            "teacher_id",
            "student_id",
            "subject_id",
            "teacher_name",
            "student_name",
            "subject_name",
            "date",
            "start_time",
            "end_time",
            "description",
            "telemost_link",
            "status",
            "is_upcoming",
            "can_cancel",
            "datetime_start",
            "datetime_end",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "teacher_name",
            "student_name",
            "subject_name",
            "teacher_id",
            "student_id",
            "subject_id",
        ]

    def validate(self, data):
        """Validate lesson data."""
        # Validate time range
        if "start_time" in data and "end_time" in data:
            if data["start_time"] >= data["end_time"]:
                raise serializers.ValidationError({"end_time": "End time must be after start time"})

        # Validate date not in past
        if "date" in data:
            if data["date"] < timezone.now().date():
                raise serializers.ValidationError({"date": "Cannot create lesson in the past"})

        return data


class LessonCreateSerializer(TimeFormatValidationMixin, serializers.Serializer):
    """Serializer for creating lessons."""

    student = serializers.IntegerField()  # ID студента
    subject = serializers.IntegerField()  # ID предмета
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField(required=False, allow_blank=True)
    telemost_link = serializers.URLField(required=False, allow_blank=True)

    def validate_student(self, value):
        """Validate student exists and has role=student."""
        try:
            user = User.objects.get(id=value, role="student")
        except User.DoesNotExist:
            raise serializers.ValidationError("Student not found")
        return value

    def validate_subject(self, value):
        """Validate subject exists."""
        try:
            Subject.objects.get(id=value)
        except Subject.DoesNotExist:
            raise serializers.ValidationError("Subject not found")
        return value

    def validate(self, data):
        """Validate lesson creation."""
        # Проверяем наличие request в контексте
        if "request" not in self.context:
            raise serializers.ValidationError(
                {"non_field_errors": "Request context is required for validation"}
            )

        # Validate time range
        if data["start_time"] >= data["end_time"]:
            raise serializers.ValidationError({"end_time": "End time must be after start time"})

        # Validate date not in past
        if data["date"] < timezone.now().date():
            raise serializers.ValidationError({"date": "Cannot create lesson in the past"})

        # Validate that start_time today is not in the past
        now = timezone.now()
        if data["date"] == now.date() and data["start_time"] <= now.time():
            raise serializers.ValidationError({"start_time": "Start time cannot be in the past"})

        # Check for time conflicts
        try:
            from scheduling.services.lesson_service import LessonService
            from django.core.exceptions import ValidationError as DjangoValidationError

            teacher = self.context["request"].user
            student_id = data["student"]

            student = User.objects.get(id=student_id)
            LessonService._check_time_conflicts(
                date=data["date"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                teacher=teacher,
                student=student,
            )
        except DjangoValidationError as e:
            raise serializers.ValidationError({"non_field_errors": str(e)})

        return data


class LessonUpdateSerializer(TimeFormatValidationMixin, serializers.Serializer):
    """Serializer for updating lessons."""

    date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    telemost_link = serializers.URLField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=["pending", "confirmed", "completed", "cancelled"], required=False
    )

    def validate(self, data):
        """Validate update data."""
        # Validate time range if both provided
        if "start_time" in data and "end_time" in data:
            if data["start_time"] >= data["end_time"]:
                raise serializers.ValidationError({"end_time": "End time must be after start time"})

        # Validate date not in past
        if "date" in data:
            if data["date"] < timezone.now().date():
                raise serializers.ValidationError({"date": "Cannot set lesson to the past"})

        # Check for time conflicts if date/time changed
        if any(field in data for field in ["date", "start_time", "end_time"]):
            from scheduling.services.lesson_service import LessonService
            from django.core.exceptions import ValidationError as DjangoValidationError

            # Get lesson from context (set in view) - обязательно для проверки конфликтов
            lesson = self.context.get("lesson")
            if not lesson:
                raise serializers.ValidationError(
                    {"non_field_errors": "Lesson context is required for time conflict validation"}
                )

            # Use updated or existing values
            check_date = data.get("date", lesson.date)
            check_start = data.get("start_time", lesson.start_time)
            check_end = data.get("end_time", lesson.end_time)

            try:
                LessonService._check_time_conflicts(
                    date=check_date,
                    start_time=check_start,
                    end_time=check_end,
                    teacher=lesson.teacher,
                    student=lesson.student,
                    exclude_lesson_id=lesson.id,
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError({"non_field_errors": str(e)})

        return data


class LessonHistorySerializer(serializers.ModelSerializer):
    """Serializer for lesson history entries."""

    performed_by_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    def get_performed_by_name(self, obj):
        return obj.performed_by.get_full_name() if obj.performed_by else "System"

    class Meta:
        model = LessonHistory
        fields = [
            "id",
            "lesson",
            "action",
            "action_display",
            "performed_by",
            "performed_by_name",
            "old_values",
            "new_values",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]


class AdminLessonSerializer(serializers.ModelSerializer):
    """Serializer for admin lesson view with full details."""

    teacher_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "date",
            "start_time",
            "end_time",
            "teacher",
            "teacher_name",
            "student",
            "student_name",
            "subject",
            "subject_name",
            "description",
            "telemost_link",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_teacher_name(self, obj):
        """Get full teacher name."""
        if not obj.teacher:
            return "(Удаленный преподаватель)"
        if obj.teacher.first_name or obj.teacher.last_name:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return obj.teacher.email

    def get_student_name(self, obj):
        """Get full student name."""
        if not obj.student:
            return "(Удаленный студент)"
        if obj.student.first_name or obj.student.last_name:
            return f"{obj.student.first_name} {obj.student.last_name}".strip()
        return obj.student.email

    def get_subject_name(self, obj):
        """Get subject name with fallback for deleted subjects."""
        if not obj.subject:
            return "(Удаленный предмет)"
        return obj.subject.name
