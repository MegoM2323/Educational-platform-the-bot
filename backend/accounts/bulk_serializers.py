"""
Serializers for bulk user operations API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class BulkUserIDsSerializer(serializers.Serializer):
    """Base serializer for bulk operations that take a list of user IDs"""

    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=1000,
        help_text="List of user IDs (max 1000)"
    )

    def validate_user_ids(self, value):
        """Ensure no duplicates"""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate user IDs not allowed")
        return value


class BulkActivateSerializer(BulkUserIDsSerializer):
    """Serializer for bulk activate operation"""
    pass


class BulkDeactivateSerializer(BulkUserIDsSerializer):
    """Serializer for bulk deactivate operation"""
    pass


class BulkAssignRoleSerializer(BulkUserIDsSerializer):
    """Serializer for bulk assign role operation"""

    role = serializers.ChoiceField(
        choices=User.Role.choices,
        help_text="Role to assign to all users"
    )


class BulkResetPasswordSerializer(BulkUserIDsSerializer):
    """Serializer for bulk reset password operation"""

    send_email = serializers.BooleanField(
        default=True,
        help_text="Whether to send reset email to users"
    )


class BulkSuspendSerializer(BulkUserIDsSerializer):
    """Serializer for bulk suspend operation"""

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional reason for suspension"
    )


class BulkUnsuspendSerializer(BulkUserIDsSerializer):
    """Serializer for bulk unsuspend operation"""
    pass


class BulkDeleteSerializer(BulkUserIDsSerializer):
    """Serializer for bulk delete (archive) operation"""

    permanent = serializers.BooleanField(
        default=False,
        help_text="If True, permanently delete. If False, archive only"
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional reason for deletion"
    )


class BulkOperationResponseSerializer(serializers.Serializer):
    """Serializer for bulk operation responses"""

    class SuccessItemSerializer(serializers.Serializer):
        user_id = serializers.IntegerField()
        email = serializers.EmailField()
        full_name = serializers.CharField()

    class FailureItemSerializer(serializers.Serializer):
        user_id = serializers.IntegerField()
        reason = serializers.CharField()

    class SummarySerializer(serializers.Serializer):
        total_requested = serializers.IntegerField()
        success_count = serializers.IntegerField()
        failure_count = serializers.IntegerField()

    operation_id = serializers.UUIDField()
    success = serializers.BooleanField()
    error = serializers.CharField(required=False, allow_blank=True)
    successes = SuccessItemSerializer(many=True)
    failures = FailureItemSerializer(many=True)
    summary = SummarySerializer()
