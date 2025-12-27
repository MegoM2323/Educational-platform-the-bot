"""
Serializers for Teacher Progress Viewer (T403)
"""
from rest_framework import serializers


class StudentProgressOverviewSerializer(serializers.Serializer):
    """
    Сериализатор для обзора прогресса студента
    """
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    student_email = serializers.EmailField()
    completion_percentage = serializers.FloatField()
    lessons_completed = serializers.IntegerField()
    lessons_total = serializers.IntegerField()
    total_score = serializers.IntegerField()
    max_possible_score = serializers.IntegerField()
    last_activity = serializers.DateTimeField(allow_null=True)


class ElementProgressDetailSerializer(serializers.Serializer):
    """
    Детальная информация о прогрессе по элементу
    """
    element_id = serializers.IntegerField()
    element_type = serializers.CharField()
    element_title = serializers.CharField()
    student_answer = serializers.JSONField(allow_null=True)
    score = serializers.IntegerField(allow_null=True)
    max_score = serializers.IntegerField()
    status = serializers.CharField()
    completed_at = serializers.DateTimeField(allow_null=True)
    attempts = serializers.IntegerField()
    # For quick_question type
    correct_answer = serializers.JSONField(required=False, allow_null=True)
    choices = serializers.JSONField(required=False, allow_null=True)


class LessonProgressDetailSerializer(serializers.Serializer):
    """
    Детальная информация о прогрессе по уроку
    """
    lesson_id = serializers.IntegerField()
    lesson_title = serializers.CharField()
    status = serializers.CharField()
    completion_percent = serializers.IntegerField()
    completed_elements = serializers.IntegerField()
    total_elements = serializers.IntegerField()
    total_score = serializers.IntegerField()
    max_possible_score = serializers.IntegerField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    total_time_spent_seconds = serializers.IntegerField()
