"""
Serializers for scheduling system.

Includes serializers for lesson models with validation.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.apps import apps
from django.utils import timezone
from django.utils.html import escape
from datetime import timedelta, time

from scheduling.models import Lesson, LessonHistory

User = get_user_model()


def get_subject_model():
    """Lazy load Subject model to avoid import issues during migrations."""
    return apps.get_model("materials", "Subject")


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


class SubjectSerializer(serializers.Serializer):
    """Serializer for subjects."""

    id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(max_length=7, default="#3B82F6")


class LessonSerializer(serializers.ModelSerializer):
    """Serializer for lessons with computed fields."""

    teacher_name = serializers.CharField(source="teacher.get_full_name", read_only=True)
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    # Explicit ID fields for frontend compatibility
    teacher_id = serializers.ReadOnlyField(source="teacher.id")
    subject_id = serializers.ReadOnlyField(source="subject.id")
    student_id = serializers.SerializerMethodField()
    is_upcoming = serializers.BooleanField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    datetime_start = serializers.DateTimeField(read_only=True)
    datetime_end = serializers.DateTimeField(read_only=True)

    def get_student_name(self, obj):
        """Get student full name or placeholder if not assigned."""
        if obj.student is None:
            return "(No student assigned)"
        return obj.student.get_full_name()

    def get_student_id(self, obj):
        """Get student ID or None if not assigned."""
        if obj.student is None:
            return None
        return obj.student.id

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
            "notes",
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
        # Validate time range - allow midnight crossing (23:00 -> 01:00)
        if "start_time" in data and "end_time" in data:
            if data["start_time"] == data["end_time"]:
                raise serializers.ValidationError(
                    {"end_time": "Start time and end time cannot be the same"}
                )

        # Validate date not in past
        if "date" in data:
            if data["date"] < timezone.now().date():
                raise serializers.ValidationError({"date": "Cannot create lesson in the past"})

        return data


class LessonCreateSerializer(TimeFormatValidationMixin, serializers.Serializer):
    """Serializer for creating lessons."""

    student = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    subject = serializers.CharField()  # ID предмета
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField(required=False, allow_blank=True)
    telemost_link = serializers.URLField(required=False, allow_blank=True)

    def validate_student(self, value):
        """Validate student exists and has role=student."""
        if value is None or value == "":
            return None
        try:
            user = User.objects.get(id=value, role="student")
        except (User.DoesNotExist, ValueError):
            raise serializers.ValidationError("Student not found")
        return value

    def validate_subject(self, value):
        """Validate subject exists."""
        if value is None:
            return value
        try:
            get_subject_model().objects.get(id=value)
        except (get_subject_model().DoesNotExist, ValueError):
            raise serializers.ValidationError("Subject not found or invalid ID")
        return value

    def validate_description(self, value):
        """Sanitize description to prevent XSS."""
        if value:
            return escape(value)
        return value

    def validate_telemost_link(self, value):
        """Validate URL and sanitize."""
        if value:
            # Check allowed domains
            allowed_domains = [
                "https://telemost.yandex.ru/",
                "https://meet.google.com/",
            ]
            if not any(value.startswith(domain) for domain in allowed_domains):
                raise serializers.ValidationError(
                    "Only Yandex Telemost or Google Meet links are allowed"
                )
        return value

    def validate(self, data):
        """Validate lesson creation."""
        # Проверяем наличие request в контексте
        if "request" not in self.context:
            raise serializers.ValidationError(
                {"non_field_errors": "Request context is required for validation"}
            )

        # Validate time range - allow midnight crossing (23:00 -> 01:00)
        if data["start_time"] == data["end_time"]:
            raise serializers.ValidationError(
                {"end_time": "Start time and end time cannot be the same"}
            )

        # Validate duration (minimum 30 minutes, maximum 4 hours)
        start_time = data["start_time"]
        end_time = data["end_time"]

        # Compute duration
        from datetime import datetime, date as date_obj

        duration = datetime.combine(date_obj.today(), end_time) - datetime.combine(
            date_obj.today(), start_time
        )

        # If duration is negative (midnight crossing), add 1 day
        if duration.total_seconds() < 0:
            duration += timedelta(days=1)

        # Check minimum duration
        if duration < timedelta(minutes=30):
            raise serializers.ValidationError(
                {"end_time": "Lesson duration must be at least 30 minutes"}
            )

        # Check maximum duration
        if duration > timedelta(hours=4):
            raise serializers.ValidationError(
                {"end_time": "Lesson duration must not exceed 4 hours"}
            )

        # Validate date not in past
        if data["date"] < timezone.now().date():
            raise serializers.ValidationError({"date": "Cannot create lesson in the past"})

        # Validate that start_time today is not in the past
        now = timezone.now()
        if data["date"] == now.date() and data["start_time"] <= now.time():
            raise serializers.ValidationError({"start_time": "Start time cannot be in the past"})

        # Check for time conflicts (only if student is assigned)
        if data.get("student"):
            try:
                from scheduling.services.lesson_service import LessonService
                from django.core.exceptions import (
                    ValidationError as DjangoValidationError,
                )

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
    status = serializers.ChoiceField(choices=Lesson.Status.choices, required=False)
    teacher_id = serializers.IntegerField(required=False, allow_null=True)
    student_id = serializers.IntegerField(required=False, allow_null=True)
    subject_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_teacher_id(self, value):
        """Validate teacher exists and has role=teacher."""
        if value is None:
            return value
        try:
            user = User.objects.get(id=value, role="teacher")
        except User.DoesNotExist:
            raise serializers.ValidationError("Teacher not found or does not have teacher role")
        return value

    def validate_student_id(self, value):
        """Validate student exists and has role=student."""
        if value is None:
            return value
        try:
            user = User.objects.get(id=value, role="student")
        except User.DoesNotExist:
            raise serializers.ValidationError("Student not found or does not have student role")
        return value

    def validate_subject_id(self, value):
        """Validate subject exists."""
        if value is None:
            return value
        try:
            get_subject_model().objects.get(id=value)
        except get_subject_model().DoesNotExist:
            raise serializers.ValidationError("Subject not found")
        return value

    def to_internal_value(self, data):
        """Convert IDs to objects for service layer."""
        ret = super().to_internal_value(data)

        # Convert student_id to student object
        if "student_id" in ret:
            student_id = ret.pop("student_id")
            if student_id is not None:
                try:
                    ret["student"] = User.objects.get(id=student_id, role="student")
                except User.DoesNotExist:
                    raise serializers.ValidationError({"student_id": "Student not found"})
            else:
                ret["student"] = None

        # Convert teacher_id to teacher object
        if "teacher_id" in ret:
            teacher_id = ret.pop("teacher_id")
            if teacher_id is not None:
                try:
                    ret["teacher"] = User.objects.get(id=teacher_id, role="teacher")
                except User.DoesNotExist:
                    raise serializers.ValidationError({"teacher_id": "Teacher not found"})
            else:
                ret["teacher"] = None

        # Convert subject_id to subject object
        if "subject_id" in ret:
            subject_id = ret.pop("subject_id")
            if subject_id is not None:
                try:
                    ret["subject"] = get_subject_model().objects.get(id=subject_id)
                except get_subject_model().DoesNotExist:
                    raise serializers.ValidationError({"subject_id": "Subject not found"})
            else:
                ret["subject"] = None

        return ret

    def validate(self, data):
        """Validate update data."""
        # Validate time range if both provided - allow midnight crossing (23:00 -> 01:00)
        if "start_time" in data and "end_time" in data:
            if data["start_time"] == data["end_time"]:
                raise serializers.ValidationError(
                    {"end_time": "Start time and end time cannot be the same"}
                )

        # Validate date not in past
        if "date" in data:
            if data["date"] < timezone.now().date():
                raise serializers.ValidationError({"date": "Cannot set lesson to the past"})

        # Get lesson from context for conflict checking
        lesson = self.context.get("lesson")
        if not lesson:
            # Only needed if checking conflicts
            if any(field in data for field in ["date", "start_time", "end_time", "student"]):
                raise serializers.ValidationError(
                    {"non_field_errors": "Lesson context is required for conflict validation"}
                )
        else:
            from scheduling.services.lesson_service import LessonService
            from django.core.exceptions import ValidationError as DjangoValidationError

            # Check for conflicts if date/time changed OR student changed
            should_check_conflicts = any(
                field in data for field in ["date", "start_time", "end_time", "student"]
            )

            if should_check_conflicts:
                # Use updated or existing values
                check_date = data.get("date", lesson.date)
                check_start = data.get("start_time", lesson.start_time)
                check_end = data.get("end_time", lesson.end_time)
                # Use the new student if being changed, otherwise use existing
                check_student = data.get("student", lesson.student)

                try:
                    LessonService._check_time_conflicts(
                        date=check_date,
                        start_time=check_start,
                        end_time=check_end,
                        teacher=lesson.teacher,
                        student=check_student,
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
        """Get name of user who performed the action."""
        if obj.performed_by:
            return obj.performed_by.get_full_name()
        return "System"

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

    def to_representation(self, instance):
        """Ensure performed_by can be null in output."""
        ret = super().to_representation(instance)
        ret["performed_by"] = instance.performed_by_id if instance.performed_by else None
        return ret


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
            return "(No student assigned)"
        if obj.student.first_name or obj.student.last_name:
            return f"{obj.student.first_name} {obj.student.last_name}".strip()
        return obj.student.email

    def get_subject_name(self, obj):
        """Get subject name with fallback for deleted subjects."""
        if not obj.subject:
            return "(Удаленный предмет)"
        return obj.subject.name
