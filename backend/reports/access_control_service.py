"""
Report Access Control Service

Provides high-level operations for managing report access:
- Creating and managing access tokens
- Managing report sharing
- Validating access permissions
- Logging access for audit trails
"""

import secrets
from datetime import timedelta
from typing import Optional, List, Tuple

from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import (
    Report, ReportAccessToken, ReportSharing, ReportAccessAuditLog
)

User = get_user_model()


class ReportAccessControlService:
    """
    Service for managing report access control operations.
    """

    # Token length and expiration defaults
    TOKEN_LENGTH = 32
    DEFAULT_TOKEN_EXPIRATION_HOURS = 24
    DEFAULT_TOKEN_MAX_ACCESSES = None  # Unlimited

    @staticmethod
    def create_access_token(
        report: Report,
        created_by: User,
        expires_in_hours: int = DEFAULT_TOKEN_EXPIRATION_HOURS,
        max_accesses: Optional[int] = DEFAULT_TOKEN_MAX_ACCESSES
    ) -> ReportAccessToken:
        """
        Create a temporary access token for a report.

        Args:
            report: Report to create token for
            created_by: User creating the token
            expires_in_hours: Token expiration time in hours
            max_accesses: Maximum number of accesses (None = unlimited)

        Returns:
            ReportAccessToken instance

        Raises:
            ValueError: If created_by is not authorized
        """
        if not ReportAccessControlService._can_manage_access(created_by, report):
            raise ValueError("User not authorized to create access tokens for this report")

        # Generate unique token
        token = secrets.token_urlsafe(ReportAccessControlService.TOKEN_LENGTH)

        # Calculate expiration
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)

        # Create token
        access_token = ReportAccessToken.objects.create(
            token=token,
            report=report,
            created_by=created_by,
            expires_at=expires_at,
            max_accesses=max_accesses
        )

        return access_token

    @staticmethod
    def revoke_access_token(token: ReportAccessToken, revoked_by: User = None) -> bool:
        """
        Revoke an access token.

        Args:
            token: Token to revoke
            revoked_by: User revoking the token (for logging)

        Returns:
            bool: Success status
        """
        token.revoke()
        return True

    @staticmethod
    def share_report(
        report: Report,
        shared_by: User,
        shared_with_user: Optional[User] = None,
        shared_role: str = '',
        permission: str = 'view',
        expires_in_days: Optional[int] = None,
        share_message: str = ''
    ) -> ReportSharing:
        """
        Share a report with a user or role.

        Args:
            report: Report to share
            shared_by: User sharing the report
            shared_with_user: User to share with (None for role-based sharing)
            shared_role: Role to share with (if user-specific, leave empty)
            permission: Permission level (view, view_download, view_download_export)
            expires_in_days: Expiration in days (None = never expires)
            share_message: Optional message to recipient

        Returns:
            ReportSharing instance

        Raises:
            ValueError: If invalid parameters or unauthorized
        """
        if not ReportAccessControlService._can_manage_access(shared_by, report):
            raise ValueError("User not authorized to share this report")

        if not shared_with_user and not shared_role:
            raise ValueError("Either shared_with_user or shared_role must be provided")

        if permission not in ['view', 'view_download', 'view_download_export']:
            raise ValueError("Invalid permission level")

        # Determine share type
        if shared_with_user:
            share_type = ReportSharing.ShareType.USER
        else:
            share_type = ReportSharing.ShareType.ROLE

        # Calculate expiration if provided
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)

        # Create sharing entry
        sharing = ReportSharing.objects.create(
            report=report,
            shared_by=shared_by,
            shared_with_user=shared_with_user,
            share_type=share_type,
            shared_role=shared_role,
            permission=permission,
            expires_at=expires_at,
            share_message=share_message
        )

        return sharing

    @staticmethod
    def unshare_report(sharing: ReportSharing, requested_by: User = None) -> bool:
        """
        Remove report sharing.

        Args:
            sharing: ReportSharing to remove
            requested_by: User requesting the unshare

        Returns:
            bool: Success status
        """
        sharing.is_active = False
        sharing.save(update_fields=['is_active'])
        return True

    @staticmethod
    def get_access_tokens_for_report(report: Report) -> List[ReportAccessToken]:
        """
        Get all active access tokens for a report.

        Args:
            report: Report to get tokens for

        Returns:
            List of active ReportAccessToken instances
        """
        return ReportAccessToken.objects.filter(
            report=report,
            status=ReportAccessToken.Status.ACTIVE
        ).order_by('-created_at')

    @staticmethod
    def get_report_sharings(report: Report) -> List[ReportSharing]:
        """
        Get all active sharings for a report.

        Args:
            report: Report to get sharings for

        Returns:
            List of active ReportSharing instances
        """
        return ReportSharing.objects.filter(
            report=report,
            is_active=True
        ).select_related('shared_with_user').order_by('-created_at')

    @staticmethod
    def get_access_audit_logs(
        report: Report = None,
        user: User = None,
        access_type: str = None,
        days_back: int = 30
    ) -> List[ReportAccessAuditLog]:
        """
        Get access audit logs with optional filtering.

        Args:
            report: Filter by report
            user: Filter by user
            access_type: Filter by access type
            days_back: Get logs from last N days

        Returns:
            List of ReportAccessAuditLog instances
        """
        query = ReportAccessAuditLog.objects.all()

        if report:
            query = query.filter(report=report)

        if user:
            query = query.filter(accessed_by=user)

        if access_type:
            query = query.filter(access_type=access_type)

        # Filter by date range
        cutoff_date = timezone.now() - timedelta(days=days_back)
        query = query.filter(accessed_at__gte=cutoff_date)

        return query.order_by('-accessed_at')

    @staticmethod
    def validate_token_access(token_str: str, report: Report) -> Tuple[bool, Optional[ReportAccessToken]]:
        """
        Validate an access token for a report.

        Args:
            token_str: Token string
            report: Report to validate against

        Returns:
            Tuple of (is_valid, token_object)
        """
        try:
            token = ReportAccessToken.objects.get(
                token=token_str,
                report=report
            )

            if token.is_valid():
                return True, token
            return False, token

        except ReportAccessToken.DoesNotExist:
            return False, None

    @staticmethod
    def log_report_access(
        report: Report,
        user: User,
        request=None,
        access_type: str = 'view',
        access_method: str = 'direct',
        duration_seconds: int = 0,
        metadata: dict = None
    ) -> ReportAccessAuditLog:
        """
        Log a report access event.

        Args:
            report: Report being accessed
            user: User accessing the report
            request: HTTP request (optional, for IP/user-agent)
            access_type: Type of access (view, download, etc.)
            access_method: Method of access (direct, token_link, etc.)
            duration_seconds: How long the user accessed the report
            metadata: Additional metadata

        Returns:
            ReportAccessAuditLog instance
        """
        ip_address = '127.0.0.1'
        user_agent = ''
        session_id = ''

        if request:
            ip_address = ReportAccessControlService._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            if hasattr(request, 'session') and request.session:
                session_id = request.session.session_key or ''

        log_entry = ReportAccessAuditLog.objects.create(
            report=report,
            accessed_by=user,
            access_type=access_type,
            access_method=access_method,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            access_duration_seconds=duration_seconds,
            metadata=metadata or {}
        )

        return log_entry

    @staticmethod
    def get_access_statistics(report: Report, days_back: int = 30) -> dict:
        """
        Get access statistics for a report.

        Args:
            report: Report to get statistics for
            days_back: Number of days to include

        Returns:
            Dictionary with access statistics
        """
        cutoff_date = timezone.now() - timedelta(days=days_back)

        logs = ReportAccessAuditLog.objects.filter(
            report=report,
            accessed_at__gte=cutoff_date
        )

        access_by_type = {}
        access_by_method = {}
        access_by_user = {}

        for log in logs:
            # By access type
            access_by_type[log.access_type] = access_by_type.get(log.access_type, 0) + 1

            # By access method
            access_by_method[log.access_method] = access_by_method.get(log.access_method, 0) + 1

            # By user
            user_key = log.accessed_by.email
            if user_key not in access_by_user:
                access_by_user[user_key] = 0
            access_by_user[user_key] += 1

        return {
            'total_accesses': logs.count(),
            'unique_users': logs.values('accessed_by').distinct().count(),
            'access_by_type': access_by_type,
            'access_by_method': access_by_method,
            'access_by_user': access_by_user,
            'date_range_days': days_back,
        }

    @staticmethod
    def export_audit_log(
        report: Report = None,
        user: User = None,
        format: str = 'json',
        days_back: int = 30
    ) -> str:
        """
        Export audit logs in specified format.

        Args:
            report: Filter by report
            user: Filter by user
            format: Export format (json, csv)
            days_back: Number of days to include

        Returns:
            Exported data as string
        """
        logs = ReportAccessControlService.get_access_audit_logs(
            report=report,
            user=user,
            days_back=days_back
        )

        if format == 'json':
            import json
            data = [
                {
                    'report': log.report.title,
                    'user': log.accessed_by.email,
                    'access_type': log.access_type,
                    'access_method': log.access_method,
                    'ip_address': str(log.ip_address),
                    'accessed_at': log.accessed_at.isoformat(),
                    'duration_seconds': log.access_duration_seconds,
                }
                for log in logs
            ]
            return json.dumps(data, indent=2)

        elif format == 'csv':
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Report', 'User', 'Access Type', 'Access Method',
                'IP Address', 'Accessed At', 'Duration (seconds)'
            ])

            # Write rows
            for log in logs:
                writer.writerow([
                    log.report.title,
                    log.accessed_by.email,
                    log.access_type,
                    log.access_method,
                    str(log.ip_address),
                    log.accessed_at.isoformat(),
                    log.access_duration_seconds,
                ])

            return output.getvalue()

        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    def _can_manage_access(user: User, report: Report) -> bool:
        """
        Check if user can manage access for a report.

        Only the report owner or admin can manage access.
        """
        return user.is_staff or user.is_superuser or report.author_id == user.id

    @staticmethod
    def _get_client_ip(request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
