"""
Permissions for reports module.

Implements comprehensive role-based access control for reports with:
- Student: Can view own reports
- Parent: Can view children's reports
- Teacher: Can view class reports, manage own reports
- Tutor: Can view assigned student reports
- Admin: Can view all reports

Supports shared reports via tokens and explicit sharing.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import StudentProfile
from .models import ReportAccessToken, ReportSharing

User = get_user_model()


class ReportAccessService:
    """
    Service for checking report access permissions.
    Centralized logic for role-based and sharing-based access.
    """

    @staticmethod
    def can_user_view_report(user, report, access_method="direct", **kwargs):
        """
        Check if user can view the given report.

        Args:
            user: User requesting access
            report: Report instance
            access_method: How user is trying to access ('direct', 'token', 'sharing')
            **kwargs: Additional context (token, sharing object, etc.)

        Returns:
            bool: True if user can view
        """
        if not user or not user.is_authenticated:
            return False

        # Admin/superuser can view any report
        if user.is_staff or user.is_superuser:
            return True

        # Check access via shared link (token)
        if access_method == "token" and "token" in kwargs:
            token = kwargs.get("token")
            return ReportAccessService._check_token_access(user, report, token)

        # Check explicit sharing
        if ReportAccessService._check_sharing_access(user, report):
            return True

        # Check role-based access
        return ReportAccessService._check_role_based_access(user, report)

    @staticmethod
    def _check_token_access(user, report, token_obj):
        """Check if token grants access to report."""
        if not token_obj.is_valid():
            return False

        if token_obj.report_id != report.id:
            return False

        # Update token access count
        token_obj.increment_access()
        return True

    @staticmethod
    def _check_sharing_access(user, report):
        """Check if report is explicitly shared with user or user's role."""
        from django.db.models import Q

        sharings = ReportSharing.objects.filter(
            report_id=report.id, is_active=True
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))

        # User-specific sharing
        if sharings.filter(shared_with_user_id=user.id).exists():
            return True

        # Role-based sharing
        if sharings.filter(shared_role=user.role).exists():
            return True

        return False

    @staticmethod
    def _check_role_based_access(user, report):
        """Check role-based access without sharing."""
        # Student: can view reports about themselves
        if user.role == User.Role.STUDENT:
            return report.target_students.filter(id=user.id).exists()

        # Parent: can view reports about their children
        if user.role == User.Role.PARENT:
            try:
                children = user.parent_profile.children.all()
                return report.target_students.filter(id__in=children).exists()
            except AttributeError:
                return False

        # Teacher: can view their own created reports and shared ones
        if user.role == User.Role.TEACHER:
            return report.author_id == user.id

        # Tutor: can view their own created reports
        if user.role == User.Role.TUTOR:
            return report.author_id == user.id

        return False

    @staticmethod
    def get_user_accessible_reports(user):
        """
        Get all reports accessible to the given user.

        Returns a QuerySet of reports the user can access.
        """
        from django.db.models import Q
        from .models import Report

        if not user or not user.is_authenticated:
            return Report.objects.none()

        if user.is_staff or user.is_superuser:
            return Report.objects.all()

        # Student: reports about them + shared with them
        if user.role == User.Role.STUDENT:
            return Report.objects.filter(
                Q(target_students=user)
                | Q(sharings__shared_with_user=user, sharings__is_active=True)
                | Q(sharings__shared_role=User.Role.STUDENT, sharings__is_active=True)
            ).distinct()

        # Parent: reports about their children + shared with them
        if user.role == User.Role.PARENT:
            try:
                children = user.parent_profile.children.all()
                return Report.objects.filter(
                    Q(target_students__in=children)
                    | Q(sharings__shared_with_user=user, sharings__is_active=True)
                    | Q(
                        sharings__shared_role=User.Role.PARENT, sharings__is_active=True
                    )
                ).distinct()
            except AttributeError:
                return Report.objects.none()

        # Teacher: own reports + shared with them
        if user.role == User.Role.TEACHER:
            return Report.objects.filter(
                Q(author=user)
                | Q(sharings__shared_with_user=user, sharings__is_active=True)
                | Q(sharings__shared_role=User.Role.TEACHER, sharings__is_active=True)
            ).distinct()

        # Tutor: own reports + shared with them
        if user.role == User.Role.TUTOR:
            return Report.objects.filter(
                Q(author=user)
                | Q(sharings__shared_with_user=user, sharings__is_active=True)
                | Q(sharings__shared_role=User.Role.TUTOR, sharings__is_active=True)
            ).distinct()

        return Report.objects.none()

    @staticmethod
    def can_user_share_report(user, report):
        """Check if user can share the report."""
        # Only owner or admin can share
        return user.is_staff or user.is_superuser or report.author_id == user.id

    @staticmethod
    def can_user_edit_report(user, report):
        """Check if user can edit the report."""
        # Only owner or admin can edit
        return user.is_staff or user.is_superuser or report.author_id == user.id

    @staticmethod
    def log_access(
        report, user, access_type="view", access_method="direct", request=None, **kwargs
    ):
        """
        Log report access for audit trail.

        Args:
            report: Report being accessed
            user: User accessing the report
            access_type: Type of access (view, download, share, print, export)
            access_method: Method of access (direct, token_link, shared_access, role_based)
            request: HTTP request object
            **kwargs: Additional metadata
        """
        from .models import ReportAccessAuditLog

        ip_address = "0.0.0.0"
        user_agent = ""
        session_id = ""

        if request:
            ip_address = ReportAccessService._get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            session_id = request.session.session_key if request.session else ""

        ReportAccessAuditLog.objects.create(
            report=report,
            accessed_by=user,
            access_type=access_type,
            access_method=access_method,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            access_duration_seconds=kwargs.get("duration", 0),
            metadata=kwargs.get("metadata", {}),
        )

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class ParentReportPermission(BasePermission):
    """
    Parent access control for student reports.

    Rules:
    - Parent can view StudentReport for linked children
    - Parent has read-only access (no edit/delete)
    - Respects show_to_parent flag
    - Admin can see all reports
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if parent can access this report"""
        user = request.user

        # Admin can access all reports
        if user.is_staff or user.is_superuser:
            return True

        # Teachers can manage their own reports (write access)
        if user.role == User.Role.TEACHER:
            return obj.teacher == user

        # Students can view reports about themselves (read-only)
        if user.role == User.Role.STUDENT:
            if request.method in SAFE_METHODS:
                return obj.student == user
            return False

        # Parents can view reports about their children (read-only)
        if user.role == User.Role.PARENT:
            # Check if report is visible to parent
            if not obj.show_to_parent:
                return False

            # Check if user is the parent of the student
            try:
                student_profile = StudentProfile.objects.select_related("parent").get(
                    user_id=obj.student_id
                )
                if student_profile.parent_id == user.id:
                    # Read-only access only
                    return request.method in SAFE_METHODS
            except StudentProfile.DoesNotExist:
                pass

            # Check direct parent assignment
            if obj.parent_id == user.id and request.method in SAFE_METHODS:
                return True

            return False

        return False


class IsTeacherOrAdmin(BasePermission):
    """
    Only teachers or admin can create/edit reports.
    """

    def has_permission(self, request, view):
        """Check if user is teacher or admin"""
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.role == User.Role.TEACHER
                or request.user.is_staff
                or request.user.is_superuser
            )
        )


class CanAcknowledgeReport(BasePermission):
    """
    Only parent can acknowledge a report.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if parent can acknowledge this report"""
        user = request.user

        # Admin can acknowledge any report
        if user.is_staff or user.is_superuser:
            return True

        # Only parents can acknowledge
        if user.role != User.Role.PARENT:
            return False

        # Check if user is the parent
        try:
            student_profile = StudentProfile.objects.select_related("parent").get(
                user_id=obj.student_id
            )
            return student_profile.parent_id == user.id
        except StudentProfile.DoesNotExist:
            return obj.parent_id == user.id


class CanAccessReport(BasePermission):
    """
    Permission check for report access based on roles and sharing.

    Supports:
    - Direct access via roles (student own reports, parent children reports)
    - Shared reports (via ReportSharing model)
    - Temporary access tokens (via ReportAccessToken)
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user can access this report"""
        return ReportAccessService.can_user_view_report(request.user, obj)


class CanShareReport(BasePermission):
    """
    Permission check for sharing reports.

    Only the report owner or admin can share reports.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user can share this report"""
        return ReportAccessService.can_user_share_report(request.user, obj)


class CanEditReport(BasePermission):
    """
    Permission check for editing reports.

    Only the report owner or admin can edit reports.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user can edit this report"""
        return ReportAccessService.can_user_edit_report(request.user, obj)
