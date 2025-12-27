"""
T_ASSIGN_010: Serializers for assignment history and submission versioning.

Serializers:
- AssignmentHistorySerializer: List and detail view of assignment changes
- SubmissionVersionSerializer: List and detail view of submission versions
- SubmissionVersionDiffSerializer: Diff comparison between versions
- SubmissionVersionRestoreSerializer: Restore action data
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import format_lazy

from assignments.models import (
    AssignmentHistory, SubmissionVersion, SubmissionVersionDiff,
    SubmissionVersionRestore
)

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user data for history records."""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name')


class AssignmentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for AssignmentHistory records.

    Shows what changed, who changed it, when, and the old/new values.
    """
    changed_by_name = serializers.CharField(
        source='changed_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    changed_by_detail = UserMinimalSerializer(
        source='changed_by',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = AssignmentHistory
        fields = (
            'id', 'assignment', 'changed_by', 'changed_by_name', 'changed_by_detail',
            'change_time', 'changes_dict', 'change_summary', 'fields_changed'
        )
        read_only_fields = (
            'id', 'assignment', 'changed_by', 'change_time',
            'changes_dict', 'change_summary', 'fields_changed'
        )


class SubmissionVersionSerializer(serializers.ModelSerializer):
    """
    Serializer for SubmissionVersion records.

    Shows submission versions with content, metadata, and versioning info.
    """
    submitted_by_name = serializers.CharField(
        source='submitted_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    submitted_by_detail = UserMinimalSerializer(
        source='submitted_by',
        read_only=True,
        allow_null=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionVersion
        fields = (
            'id', 'submission', 'version_number', 'file', 'file_url', 'content',
            'submitted_at', 'is_final', 'submitted_by', 'submitted_by_name',
            'submitted_by_detail', 'previous_version'
        )
        read_only_fields = (
            'id', 'submission', 'version_number', 'file', 'content',
            'submitted_at', 'is_final', 'submitted_by', 'previous_version'
        )

    def get_file_url(self, obj):
        """Return file URL if it exists."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class SubmissionVersionListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing submission versions.

    Used in list views to reduce payload size.
    """
    submitted_by_name = serializers.CharField(
        source='submitted_by.get_full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SubmissionVersion
        fields = (
            'id', 'version_number', 'submitted_at', 'is_final',
            'submitted_by_name', 'submitted_by'
        )
        read_only_fields = fields


class SubmissionVersionDetailSerializer(SubmissionVersionSerializer):
    """Extended version for detailed view with additional context."""
    previous_version_detail = SubmissionVersionListSerializer(
        source='previous_version',
        read_only=True,
        allow_null=True
    )

    class Meta(SubmissionVersionSerializer.Meta):
        fields = SubmissionVersionSerializer.Meta.fields + ('previous_version_detail',)


class SubmissionVersionDiffSerializer(serializers.ModelSerializer):
    """
    Serializer for showing diff between two submission versions.

    Compares content and shows added/removed/changed lines.
    """
    version_a_detail = SubmissionVersionListSerializer(
        source='version_a',
        read_only=True
    )
    version_b_detail = SubmissionVersionListSerializer(
        source='version_b',
        read_only=True
    )

    class Meta:
        model = SubmissionVersionDiff
        fields = (
            'id', 'version_a', 'version_b', 'version_a_detail', 'version_b_detail',
            'diff_content', 'created_at'
        )
        read_only_fields = fields


class SubmissionVersionRestoreSerializer(serializers.ModelSerializer):
    """
    Serializer for SubmissionVersionRestore audit trail.

    Shows which versions were restored and by whom.
    """
    restored_by_name = serializers.CharField(
        source='restored_by.get_full_name',
        read_only=True,
        allow_null=True
    )
    restored_by_detail = UserMinimalSerializer(
        source='restored_by',
        read_only=True,
        allow_null=True
    )
    restored_from_version_detail = SubmissionVersionListSerializer(
        source='restored_from_version',
        read_only=True,
        allow_null=True
    )
    restored_to_version_detail = SubmissionVersionListSerializer(
        source='restored_to_version',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = SubmissionVersionRestore
        fields = (
            'id', 'submission', 'restored_from_version', 'restored_to_version',
            'restored_by', 'restored_by_name', 'restored_by_detail',
            'restored_at', 'reason', 'restored_from_version_detail',
            'restored_to_version_detail'
        )
        read_only_fields = (
            'id', 'submission', 'restored_from_version', 'restored_to_version',
            'restored_by', 'restored_at', 'restored_from_version_detail',
            'restored_to_version_detail'
        )


class SubmissionRestoreRequestSerializer(serializers.Serializer):
    """
    Serializer for POST request to restore a previous submission version.

    Input validation for restoration requests.
    """
    version_number = serializers.IntegerField(
        min_value=1,
        help_text='Version number to restore'
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text='Reason for restoring this version'
    )

    def validate_version_number(self, value):
        """Validate that the version exists."""
        submission = self.context.get('submission')
        if submission:
            if not SubmissionVersion.objects.filter(
                submission=submission,
                version_number=value
            ).exists():
                raise serializers.ValidationError(
                    f"Version {value} does not exist for this submission."
                )
        return value
