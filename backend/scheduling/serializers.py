"""
Serializers for scheduling system.

Includes serializers for lesson models with validation.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from scheduling.models import Lesson, LessonHistory
from materials.models import Subject

User = get_user_model()


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for subjects."""

    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'color']


class LessonSerializer(serializers.ModelSerializer):
    """Serializer for lessons with computed fields."""

    teacher_name = serializers.CharField(
        source='teacher.get_full_name',
        read_only=True
    )
    student_name = serializers.CharField(
        source='student.get_full_name',
        read_only=True
    )
    subject_name = serializers.CharField(
        source='subject.name',
        read_only=True
    )
    is_upcoming = serializers.BooleanField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    datetime_start = serializers.DateTimeField(read_only=True)
    datetime_end = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'teacher', 'student', 'subject',
            'teacher_name', 'student_name', 'subject_name',
            'date', 'start_time', 'end_time',
            'description', 'telemost_link',
            'status', 'is_upcoming', 'can_cancel',
            'datetime_start', 'datetime_end',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'teacher_name', 'student_name', 'subject_name']

    def validate(self, data):
        """Validate lesson data."""
        # Validate time range
        if 'start_time' in data and 'end_time' in data:
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError(
                    {'end_time': 'End time must be after start time'}
                )

        # Validate date not in past
        if 'date' in data:
            if data['date'] < timezone.now().date():
                raise serializers.ValidationError(
                    {'date': 'Cannot create lesson in the past'}
                )

        return data


class LessonCreateSerializer(serializers.Serializer):
    """Serializer for creating lessons."""

    student = serializers.CharField()  # UUID string
    subject = serializers.CharField()  # UUID string
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    description = serializers.CharField(required=False, allow_blank=True)
    telemost_link = serializers.URLField(required=False, allow_blank=True)

    def validate_student(self, value):
        """Validate student exists and has role=student."""
        try:
            user = User.objects.get(id=value, role='student')
        except User.DoesNotExist:
            raise serializers.ValidationError('Student not found')
        return value

    def validate_subject(self, value):
        """Validate subject exists."""
        try:
            Subject.objects.get(id=value)
        except Subject.DoesNotExist:
            raise serializers.ValidationError('Subject not found')
        return value

    def validate_start_time(self, value):
        """Convert HH:MM format to HH:MM:SS if needed."""
        if isinstance(value, str) and value.count(':') == 1:
            value = value + ':00'
        return value

    def validate_end_time(self, value):
        """Convert HH:MM format to HH:MM:SS if needed."""
        if isinstance(value, str) and value.count(':') == 1:
            value = value + ':00'
        return value

    def validate(self, data):
        """Validate lesson creation."""
        # Validate time range
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError(
                {'end_time': 'End time must be after start time'}
            )

        # Validate date not in past
        if data['date'] < timezone.now().date():
            raise serializers.ValidationError(
                {'date': 'Cannot create lesson in the past'}
            )

        # Validate teacher teaches subject to student
        from materials.models import SubjectEnrollment

        teacher = self.context['request'].user
        student_id = data['student']
        subject_id = data['subject']

        try:
            SubjectEnrollment.objects.get(
                student_id=student_id,
                teacher=teacher,
                subject_id=subject_id,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            raise serializers.ValidationError(
                'You do not teach this subject to this student'
            )

        return data


class LessonUpdateSerializer(serializers.Serializer):
    """Serializer for updating lessons."""

    date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    telemost_link = serializers.URLField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=['pending', 'confirmed', 'completed', 'cancelled'],
        required=False
    )

    def validate_start_time(self, value):
        """Convert HH:MM format to HH:MM:SS if needed."""
        if isinstance(value, str) and value.count(':') == 1:
            value = value + ':00'
        return value

    def validate_end_time(self, value):
        """Convert HH:MM format to HH:MM:SS if needed."""
        if isinstance(value, str) and value.count(':') == 1:
            value = value + ':00'
        return value

    def validate(self, data):
        """Validate update data."""
        # Validate time range if both provided
        if 'start_time' in data and 'end_time' in data:
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError(
                    {'end_time': 'End time must be after start time'}
                )

        # Validate date not in past
        if 'date' in data:
            if data['date'] < timezone.now().date():
                raise serializers.ValidationError(
                    {'date': 'Cannot set lesson to the past'}
                )

        return data


class LessonHistorySerializer(serializers.ModelSerializer):
    """Serializer for lesson history entries."""

    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name',
        read_only=True
    )
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )

    class Meta:
        model = LessonHistory
        fields = [
            'id', 'lesson', 'action', 'action_display',
            'performed_by', 'performed_by_name',
            'old_values', 'new_values', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class AdminLessonSerializer(serializers.ModelSerializer):
    """Serializer for admin lesson view with full details."""

    teacher_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'date', 'start_time', 'end_time',
            'teacher', 'teacher_name',
            'student', 'student_name',
            'subject', 'subject_name',
            'description', 'telemost_link', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_teacher_name(self, obj):
        """Get full teacher name."""
        if obj.teacher.first_name or obj.teacher.last_name:
            return f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
        return obj.teacher.email

    def get_student_name(self, obj):
        """Get full student name."""
        if obj.student.first_name or obj.student.last_name:
            return f"{obj.student.first_name} {obj.student.last_name}".strip()
        return obj.student.email
