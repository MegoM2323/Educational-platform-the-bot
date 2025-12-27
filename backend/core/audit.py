"""
Centralized audit logging for user activities.

Provides comprehensive audit trail for all user actions including:
- Login/logout events
- API endpoint access
- Material views
- Assignment submissions
- User data modifications
"""
import logging
from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import QuerySet

from .models import AuditLog

logger = logging.getLogger(__name__)
User = get_user_model()


class AuditService:
    """
    Service for logging user activities to the audit log.

    Handles extraction of request metadata (IP address, user-agent)
    and persistence of audit events.
    """

    @staticmethod
    def extract_client_ip(request) -> str:
        """
        Extract client IP address from request.

        Checks X-Forwarded-For header first (for proxied requests),
        then falls back to REMOTE_ADDR.

        Args:
            request: Django HTTP request object

        Returns:
            str: Client IP address or 'unknown' if unable to determine
        """
        if not request:
            return 'unknown'

        # Check for X-Forwarded-For header (proxy, load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs; take the first one
            ip = x_forwarded_for.split(',')[0].strip()
            if ip:
                return ip

        # Fall back to REMOTE_ADDR
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip

    @staticmethod
    def extract_user_agent(request) -> str:
        """
        Extract user-agent from request headers.

        Args:
            request: Django HTTP request object

        Returns:
            str: User-Agent header or 'unknown' if not present
        """
        if not request:
            return 'unknown'

        return request.META.get('HTTP_USER_AGENT', 'unknown')[:500]  # Limit length

    @staticmethod
    def log_action(
        action: str,
        user: Optional[User] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request=None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        Log a user activity to the audit log.

        Args:
            action: Type of action (login, logout, view_material, etc.)
            user: User performing the action
            target_type: Type of object being acted upon (material, assignment, etc.)
            target_id: ID of the target object
            metadata: Additional context (JSON-serializable dict)
            request: Django HTTP request object (for IP/user-agent extraction)
            ip_address: Optional explicit IP address (if request not available)
            user_agent: Optional explicit user-agent (if request not available)

        Returns:
            AuditLog: Created audit log entry or None if logging failed
        """
        try:
            # Extract IP and user-agent from request if not provided
            if ip_address is None:
                ip_address = AuditService.extract_client_ip(request)

            if user_agent is None:
                user_agent = AuditService.extract_user_agent(request)

            # Create audit log entry
            audit_log = AuditLog.objects.create(
                action=action,
                user=user,
                target_type=target_type,
                target_id=target_id,
                metadata=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent
            )

            logger.debug(
                f"Audit log created: {action} by {user} on {target_type}:{target_id}"
            )

            return audit_log

        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_user_activities(
        user: User,
        action: Optional[str] = None,
        limit: int = 100,
        days: int = 90
    ) -> QuerySet:
        """
        Get audit log entries for a specific user.

        Args:
            user: User to get activities for
            action: Optional filter by action type
            limit: Maximum number of results
            days: Only include entries from last N days

        Returns:
            QuerySet: Filtered audit log entries
        """
        from datetime import timedelta

        start_date = timezone.now() - timedelta(days=days)

        queryset = AuditLog.objects.filter(
            user=user,
            timestamp__gte=start_date
        ).order_by('-timestamp')

        if action:
            queryset = queryset.filter(action=action)

        return queryset[:limit]

    @staticmethod
    def get_action_summary(
        action: str,
        days: int = 1
    ) -> Dict[str, Any]:
        """
        Get summary statistics for a specific action type.

        Args:
            action: Action type to summarize
            days: Time period in days

        Returns:
            Dict: Summary including count, unique users, top targets
        """
        from datetime import timedelta

        start_date = timezone.now() - timedelta(days=days)

        queryset = AuditLog.objects.filter(
            action=action,
            timestamp__gte=start_date
        )

        return {
            'action': action,
            'total_count': queryset.count(),
            'unique_users': queryset.values('user').distinct().count(),
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat()
        }


class AuditLogViewSetHelper:
    """
    Helper class for AuditLog ViewSet operations.

    Provides filtering and queryset optimization for audit log queries.
    """

    @staticmethod
    def apply_filters(
        queryset: QuerySet,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> QuerySet:
        """
        Apply filters to audit log queryset.

        Args:
            queryset: Initial queryset
            user_id: Filter by user ID
            action: Filter by action type
            target_type: Filter by target type
            ip_address: Filter by IP address
            date_from: Filter by start date (ISO format)
            date_to: Filter by end date (ISO format)

        Returns:
            QuerySet: Filtered queryset
        """
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        if action:
            queryset = queryset.filter(action=action)

        if target_type:
            queryset = queryset.filter(target_type=target_type)

        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)

        if date_from:
            from datetime import datetime
            try:
                start_date = datetime.fromisoformat(date_from)
                queryset = queryset.filter(timestamp__gte=start_date)
            except ValueError:
                pass

        if date_to:
            from datetime import datetime
            try:
                end_date = datetime.fromisoformat(date_to)
                queryset = queryset.filter(timestamp__lte=end_date)
            except ValueError:
                pass

        return queryset


# Функция-обёртка для удобного доступа к AuditService.log
def audit_log(
    request,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True
):
    """
    Convenience function for logging audit events.

    Wrapper around AuditService.log for simpler imports.

    Args:
        request: Django HTTP request object
        action: Action being performed
        target_type: Type of object being acted upon
        target_id: ID of the target object
        details: Additional details dictionary
        success: Whether the action succeeded
    """
    return AuditService.log(
        request=request,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        success=success
    )
