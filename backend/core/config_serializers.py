"""
Serializers for Configuration API
"""

from rest_framework import serializers
from .config import ConfigurationService


class ConfigurationSerializer(serializers.Serializer):
    """
    Serializer for Configuration data.

    Includes current value and default value from schema.
    """

    key = serializers.CharField()
    value = serializers.JSONField()
    default_value = serializers.JSONField(read_only=True)
    current_value = serializers.JSONField(read_only=True)
    value_type = serializers.CharField()
    description = serializers.CharField()
    group = serializers.CharField()
    updated_by = serializers.CharField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class ConfigurationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating configuration values.

    Validates the value before updating.
    """

    value = serializers.JSONField(help_text='Configuration value')

    def validate(self, data):
        """Validate configuration value."""
        request = self.context.get('request')
        view = self.context.get('view')

        if not view or not hasattr(view, 'kwargs'):
            raise serializers.ValidationError('Missing context for validation')

        key = view.kwargs.get('key')
        value = data.get('value')

        if not key:
            raise serializers.ValidationError('Configuration key is required')

        # Validate using ConfigurationService
        try:
            ConfigurationService.validate(key, value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        data['key'] = key
        return data


class ConfigurationBulkUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk configuration updates.

    Accepts a dictionary of key-value pairs.
    """

    configurations = serializers.JSONField(
        help_text='Dictionary of configuration key-value pairs'
    )

    def validate_configurations(self, value):
        """Validate all configurations."""
        if not isinstance(value, dict):
            raise serializers.ValidationError('configurations must be a dictionary')

        errors = {}
        for key, val in value.items():
            try:
                ConfigurationService.validate(key, val)
            except ValueError as e:
                errors[key] = str(e)

        if errors:
            raise serializers.ValidationError(errors)

        return value


class ConfigurationSchemaSerializer(serializers.Serializer):
    """
    Serializer for configuration schema.

    Describes all available configuration options.
    """

    key = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField()
    group = serializers.CharField()
    default = serializers.JSONField()
    current = serializers.JSONField()


class ConfigurationGroupSerializer(serializers.Serializer):
    """
    Serializer for a group of configurations.
    """

    group = serializers.CharField(help_text='Configuration group name')
    items = ConfigurationSerializer(many=True, read_only=True)


class ConfigurationResetSerializer(serializers.Serializer):
    """
    Serializer for reset configuration request.
    """

    RESET_CHOICES = [
        ('all', 'Reset all configurations to defaults'),
        ('group', 'Reset specific group to defaults'),
    ]

    reset_type = serializers.ChoiceField(
        choices=RESET_CHOICES,
        help_text='Type of reset to perform'
    )
    group = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Group name (required if reset_type is "group")'
    )

    def validate(self, data):
        """Validate reset parameters."""
        reset_type = data.get('reset_type')
        group = data.get('group')

        if reset_type == 'group' and not group:
            raise serializers.ValidationError(
                'group is required when reset_type is "group"'
            )

        return data
