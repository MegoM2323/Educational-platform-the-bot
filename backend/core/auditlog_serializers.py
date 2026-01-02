"""
Serializers for AuditLog model
"""
from rest_framework import serializers
from accounts.serializers import UserMinimalSerializer
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog"""

    user = UserMinimalSerializer(read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "action",
            "action_display",
            "target_type",
            "target_id",
            "ip_address",
            "user_agent",
            "metadata",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]
