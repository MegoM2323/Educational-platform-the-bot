from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Report, ReportTemplate, ReportRecipient, AnalyticsData, ReportSchedule

User = get_user_model()


class ReportListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка отчетов
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    target_students_count = serializers.SerializerMethodField()
    target_parents_count = serializers.SerializerMethodField()
    recipients_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = (
            'id', 'title', 'description', 'type', 'status', 'author', 'author_name',
            'target_students_count', 'target_parents_count', 'recipients_count',
            'start_date', 'end_date', 'is_auto_generated', 'generation_frequency',
            'created_at', 'generated_at', 'sent_at'
        )
    
    def get_target_students_count(self, obj):
        return obj.target_students.count()
    
    def get_target_parents_count(self, obj):
        return obj.target_parents.count()
    
    def get_recipients_count(self, obj):
        return obj.recipients.count()


class ReportDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального просмотра отчета
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    target_students = serializers.SerializerMethodField()
    target_parents = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = (
            'id', 'title', 'description', 'type', 'status', 'author', 'author_name',
            'target_students', 'target_parents', 'start_date', 'end_date',
            'content', 'file', 'is_auto_generated', 'generation_frequency',
            'created_at', 'updated_at', 'generated_at', 'sent_at', 'recipients'
        )
    
    def get_target_students(self, obj):
        return [{
            'id': student.id,
            'name': student.get_full_name(),
            'role': student.role
        } for student in obj.target_students.all()]
    
    def get_target_parents(self, obj):
        return [{
            'id': parent.id,
            'name': parent.get_full_name(),
            'role': parent.role
        } for parent in obj.target_parents.all()]
    
    def get_recipients(self, obj):
        return ReportRecipientSerializer(obj.recipients.all(), many=True).data


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания отчета
    """
    class Meta:
        model = Report
        fields = (
            'title', 'description', 'type', 'target_students', 'target_parents',
            'start_date', 'end_date', 'content', 'is_auto_generated', 'generation_frequency'
        )
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class ReportTemplateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для шаблонов отчетов
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = (
            'id', 'name', 'description', 'type', 'template_content',
            'is_default', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ReportRecipientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получателей отчетов
    """
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    recipient_role = serializers.CharField(source='recipient.role', read_only=True)
    
    class Meta:
        model = ReportRecipient
        fields = (
            'id', 'report', 'recipient', 'recipient_name', 'recipient_role',
            'is_sent', 'sent_at', 'read_at'
        )
        read_only_fields = ('id', 'sent_at', 'read_at')


class AnalyticsDataSerializer(serializers.ModelSerializer):
    """
    Сериализатор для аналитических данных
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = AnalyticsData
        fields = (
            'id', 'student', 'student_name', 'metric_type', 'value', 'unit',
            'date', 'period_start', 'period_end', 'metadata', 'created_at'
        )
        read_only_fields = ('id', 'created_at')


class ReportScheduleSerializer(serializers.ModelSerializer):
    """
    Сериализатор для расписания отчетов
    """
    report_template_name = serializers.CharField(source='report_template.name', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = (
            'id', 'report_template', 'report_template_name', 'frequency',
            'day_of_week', 'day_of_month', 'time', 'is_active',
            'last_generated', 'next_generation', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'last_generated', 'next_generation', 'created_at', 'updated_at')


class ReportStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики отчетов
    """
    total_reports = serializers.IntegerField()
    draft_reports = serializers.IntegerField()
    generated_reports = serializers.IntegerField()
    sent_reports = serializers.IntegerField()
    auto_generated_reports = serializers.IntegerField()
    templates_count = serializers.IntegerField()
    active_schedules = serializers.IntegerField()


class StudentProgressSerializer(serializers.Serializer):
    """
    Сериализатор для прогресса студента
    """
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    progress_percentage = serializers.FloatField()
    completed_assignments = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    average_score = serializers.FloatField()
    materials_studied = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    last_activity = serializers.DateTimeField()


class ClassPerformanceSerializer(serializers.Serializer):
    """
    Сериализатор для успеваемости класса
    """
    class_name = serializers.CharField()
    total_students = serializers.IntegerField()
    average_progress = serializers.FloatField()
    average_score = serializers.FloatField()
    completion_rate = serializers.FloatField()
    top_performers = StudentProgressSerializer(many=True)
    struggling_students = StudentProgressSerializer(many=True)
