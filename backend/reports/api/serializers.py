"""
Serializers for Analytics API endpoints.

Handles validation and serialization of analytics request/response data.
"""

from rest_framework import serializers


class StudentAnalyticsRecordSerializer(serializers.Serializer):
    """Single student analytics record."""
    student_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    avg_grade = serializers.FloatField()
    submission_count = serializers.IntegerField()
    progress_pct = serializers.IntegerField(min_value=0, max_value=100)


class AssignmentAnalyticsRecordSerializer(serializers.Serializer):
    """Single assignment analytics record."""
    assignment_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    avg_score = serializers.FloatField()
    submission_rate = serializers.FloatField(min_value=0, max_value=100)
    late_count = serializers.IntegerField(min_value=0)
    total_submissions = serializers.IntegerField(min_value=0, required=False)


class AttendanceAnalyticsRecordSerializer(serializers.Serializer):
    """Single attendance analytics record."""
    date = serializers.DateField()
    present_count = serializers.IntegerField(min_value=0)
    absent_count = serializers.IntegerField(min_value=0)
    late_count = serializers.IntegerField(min_value=0)


class EngagementAnalyticsRecordSerializer(serializers.Serializer):
    """Single engagement analytics record."""
    student_id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    submission_rate = serializers.FloatField(min_value=0, max_value=100)
    avg_time_to_submit = serializers.FloatField()
    responsiveness = serializers.ChoiceField(
        choices=['very_high', 'high', 'medium', 'low']
    )
    late_submissions = serializers.IntegerField(min_value=0, required=False)


class AnalyticsMetadataSerializer(serializers.Serializer):
    """Pagination and filter metadata."""
    total = serializers.IntegerField(min_value=0)
    page = serializers.IntegerField(min_value=1)
    per_page = serializers.IntegerField(min_value=1, max_value=1000)
    filters_applied = serializers.DictField()


class AnalyticsSummarySerializer(serializers.Serializer):
    """Summary statistics for analytics data."""
    mean = serializers.FloatField()
    median = serializers.FloatField()
    std_dev = serializers.FloatField()


class StudentAnalyticsResponseSerializer(serializers.Serializer):
    """Complete response for student analytics endpoint."""
    data = StudentAnalyticsRecordSerializer(many=True)
    metadata = AnalyticsMetadataSerializer()
    summary = AnalyticsSummarySerializer(required=False)


class StudentAnalyticsFilterSerializer(serializers.Serializer):
    """Query parameter filters for student analytics."""
    subject_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    grade_min = serializers.FloatField(required=False, min_value=0, max_value=100)
    grade_max = serializers.FloatField(required=False, min_value=0, max_value=100)
    sort_by = serializers.ChoiceField(
        choices=['score', 'name', 'date'],
        default='score'
    )
    page = serializers.IntegerField(default=1, min_value=1)
    per_page = serializers.IntegerField(default=20, min_value=1, max_value=1000)


class AssignmentAnalyticsFilterSerializer(serializers.Serializer):
    """Query parameter filters for assignment analytics."""
    teacher_id = serializers.IntegerField(required=False)
    subject_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    status = serializers.ChoiceField(
        choices=['active', 'closed', 'archived'],
        required=False
    )
    sort_by = serializers.ChoiceField(
        choices=['score', 'name', 'date'],
        default='score'
    )
    page = serializers.IntegerField(default=1, min_value=1)
    per_page = serializers.IntegerField(default=20, min_value=1, max_value=1000)


class ProgressAnalyticsFilterSerializer(serializers.Serializer):
    """Query parameter filters for progress analytics."""
    student_id = serializers.IntegerField(required=False)
    subject_id = serializers.IntegerField(required=False)
    granularity = serializers.ChoiceField(
        choices=['day', 'week', 'month'],
        default='week'
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
