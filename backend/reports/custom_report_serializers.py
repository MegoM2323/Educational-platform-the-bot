"""
Custom Report Serializers

Serializers for CustomReport model and related operations.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomReport, CustomReportExecution, CustomReportBuilderTemplate

User = get_user_model()

# Alias for backwards compatibility
ReportTemplate = CustomReportBuilderTemplate


class CustomReportListSerializer(serializers.ModelSerializer):
    """Serializer for listing custom reports."""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    shared_count = serializers.SerializerMethodField()
    last_execution = serializers.SerializerMethodField()

    class Meta:
        model = CustomReport
        fields = [
            'id', 'name', 'description', 'created_by', 'created_by_name',
            'is_shared', 'shared_count', 'status', 'created_at', 'updated_at',
            'last_execution'
        ]

    def get_shared_count(self, obj):
        return obj.shared_with.count()

    def get_last_execution(self, obj):
        execution = obj.executions.first()
        if execution:
            return {
                'executed_at': execution.executed_at,
                'rows_returned': execution.rows_returned,
                'execution_time_ms': execution.execution_time_ms
            }
        return None


class CustomReportDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed custom report view."""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    shared_with_list = serializers.SerializerMethodField()
    execution_history = serializers.SerializerMethodField()
    available_fields = serializers.SerializerMethodField()
    available_filters = serializers.SerializerMethodField()

    class Meta:
        model = CustomReport
        fields = [
            'id', 'name', 'description', 'created_by', 'created_by_name',
            'is_shared', 'shared_with_list', 'config', 'status', 'created_at',
            'updated_at', 'execution_history', 'available_fields', 'available_filters'
        ]

    def get_shared_with_list(self, obj):
        return [
            {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email
            }
            for user in obj.shared_with.all()
        ]

    def get_execution_history(self, obj):
        executions = obj.executions.all()[:10]  # Last 10 executions
        return CustomReportExecutionSerializer(executions, many=True).data

    def get_available_fields(self, obj):
        return {
            'description': 'Available fields for this report type',
            'options': obj.get_field_options()
        }

    def get_available_filters(self, obj):
        return {
            'description': 'Available filter options',
            'options': obj.get_filter_options()
        }


class CustomReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating custom reports."""

    class Meta:
        model = CustomReport
        fields = [
            'name', 'description', 'config', 'status'
        ]

    def validate_config(self, value):
        """Validate config structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a dictionary")

        if 'fields' not in value or not isinstance(value['fields'], list):
            raise serializers.ValidationError("Config must contain 'fields' list")

        if not value['fields']:
            raise serializers.ValidationError("Fields list cannot be empty")

        # Validate chart type if provided
        if 'chart_type' in value:
            valid_charts = ['bar', 'line', 'pie', 'histogram', 'scatter']
            if value['chart_type'] not in valid_charts:
                raise serializers.ValidationError(
                    f"chart_type must be one of: {', '.join(valid_charts)}"
                )

        return value

    def create(self, validated_data):
        """Create custom report with current user as creator."""
        validated_data['created_by'] = self.context['request'].user
        return CustomReport.objects.create(**validated_data)


class CustomReportUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating custom reports."""

    class Meta:
        model = CustomReport
        fields = [
            'name', 'description', 'config', 'status', 'is_shared'
        ]

    def validate_config(self, value):
        """Validate config structure."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Config must be a dictionary")

        if value and 'fields' in value:
            if not isinstance(value['fields'], list) or not value['fields']:
                raise serializers.ValidationError("Fields list cannot be empty")

        return value


class CustomReportGenerateSerializer(serializers.Serializer):
    """Serializer for generate endpoint."""

    # No input fields required - uses report config
    pass


class CustomReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer for report execution records."""

    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True)

    class Meta:
        model = CustomReportExecution
        fields = [
            'id', 'executed_by', 'executed_by_name', 'rows_returned',
            'execution_time_ms', 'result_summary', 'executed_at'
        ]
        read_only_fields = fields


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for report templates."""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'base_config',
            'is_system', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]

    def to_representation(self, instance):
        """Add clone information to response."""
        data = super().to_representation(instance)
        data['can_clone'] = True
        data['clone_url'] = f'/api/templates/{instance.id}/clone/'
        return data


class ReportTemplateCloneSerializer(serializers.Serializer):
    """Serializer for cloning a template."""

    name = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    config_overrides = serializers.JSONField(required=False, default=dict)

    def validate_name(self, value):
        """Ensure name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()


class ShareReportSerializer(serializers.Serializer):
    """Serializer for sharing reports with colleagues."""

    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )

    def validate_user_ids(self, value):
        """Validate user IDs exist and are teachers."""
        if not value:
            raise serializers.ValidationError("At least one user must be specified")

        users = User.objects.filter(id__in=value, role='teacher')
        if users.count() != len(value):
            raise serializers.ValidationError("Some user IDs are invalid or not teachers")

        return value
